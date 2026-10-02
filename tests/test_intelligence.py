"""Offline transport failures, source semantics, scoped retrieval and bounded delivery."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fusion_intel_http import fetch
from fusion_intel import lookup
from fusion_knowledge import knowledge_query, method_search, source_preview
from fusion_store import Case, FusionError, encode, manifest
from fusion_workspace import Workspace
from test_runtime import CONFIG


class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fusion-intel-")
        self.root = Path(self.tmp.name)
        self.workspace = Workspace.create(self.root / "workspace")
        self.case = Case.create(self.root / "case", dict(CONFIG, mission_id="src"))
        self.workspace.bind(self.case, "session-a", "project-a", self.case.meta("case_id"), ["local-fixture"])

    def tearDown(self):
        self.case.close()
        self.workspace.close()
        self.tmp.cleanup()

    def test_cache_refresh_offline_and_failure_do_not_lie_about_freshness(self):
        cache = self.root / "cache"
        with patch("fusion_intel_http.time.time", return_value=10000), patch("fusion_intel_http.download", return_value={"x": 1}) as net:
            first = fetch(cache, "fixture", "https://example.invalid")
            second = fetch(cache, "fixture", "https://example.invalid")
            offline = fetch(cache, "fixture", "https://example.invalid", offline=True)
            self.assertEqual(net.call_count, 1)
            self.assertEqual([first["status"], second["status"], offline["status"]], ["live", "cache", "offline_cache"])
        with patch("fusion_intel_http.time.time", return_value=20000), patch("fusion_intel_http.download", side_effect=OSError("do not echo me")):
            failed = fetch(cache, "fixture", "https://example.invalid", refresh=True)
            self.assertEqual(failed["status"], "stale_on_error")
            self.assertEqual(failed["fetched_at"], 10000)
            self.assertNotIn("do not echo", encode(failed))
            missing = fetch(cache, "fixture", "https://missing.invalid", offline=True)
            self.assertIsNone(missing["data"])
            self.assertEqual(missing["status"], "unavailable")

    def test_corrupt_and_future_cache_are_not_trusted(self):
        cache = self.root / "cache"
        with patch("fusion_intel_http.download", return_value={"x": 1}):
            fetch(cache, "fixture", "https://example.invalid")
        file = next(cache.glob("*.json"))
        value = json.loads(file.read_text())
        value["data"]["x"] = 2
        file.write_text(encode(value))
        self.assertIsNone(fetch(cache, "fixture", "https://example.invalid", offline=True)["data"])
        value["sha256"] = hashlib.sha256(encode(value["data"]).encode()).hexdigest()
        value["fetched_at"] = 99999999999
        file.write_text(encode(value))
        self.assertIsNone(fetch(cache, "fixture", "https://example.invalid", offline=True)["data"])

    def test_cve_rejected_and_wrong_source_identity_remain_explicit(self):
        identity = "CVE-2021-44228"
        payloads = [
            {"cveMetadata": {"cveId": identity, "state": "REJECTED"}, "containers": {"cna": {}}},
            {"dateReleased": "2026-10-01", "count": 1, "vulnerabilities": [{"cveID": identity}]},
            {"status": "OK", "data": [{"cve": "CVE-2020-0001", "epss": "0.9", "percentile": "0.9", "date": "2026-10-01"}]},
        ]
        with patch("fusion_intel_http.download", side_effect=payloads):
            sources = lookup(self.root / "cache", {"mode": "cve", "cve": identity})
        self.assertEqual(source_preview(sources[0])["record"]["state"], "REJECTED")
        self.assertTrue(source_preview(sources[1])["listed"])
        self.assertEqual(sources[2]["status"], "unavailable")
        self.assertIn("unknown", source_preview(sources[0])["applicability"])
        with self.assertRaises(FusionError):
            lookup(self.root, {"mode": "cve", "cve": "../CVE-2021-44228"})

    def test_package_pagination_withdrawal_and_no_secret_target_upload(self):
        request = {"mode": "package", "ecosystem": "PyPI", "package": "jinja2", "version": "3.1.4", "cursor": "next"}
        with patch("fusion_intel_http.download", return_value={"vulns": [{"id": "GHSA-fixture", "withdrawn": "2026-01-01"}], "next_page_token": "more"}) as net:
            result = lookup(self.root / "cache", request)[0]
        self.assertEqual(net.call_args.args[1], {"package": {"name": "jinja2", "ecosystem": "PyPI"}, "version": "3.1.4", "page_token": "next"})
        self.assertEqual(source_preview(result)["next_cursor"], "more")
        self.assertEqual(source_preview(result)["candidates"][0]["withdrawn"], "2026-01-01")
        with self.assertRaises(FusionError):
            lookup(self.root, dict(request, package="https://private.example?token=abc"))

    def test_recent_preserves_window_counts_and_does_not_imply_full_database(self):
        request = {"mode": "recent", "until": "2026-01-01T00:00:00Z", "days": 2}
        with patch("fusion_intel_http.download", return_value={"startIndex": 0, "totalResults": 40, "vulnerabilities": [{"cve": {"id": "CVE-2021-44228"}}]}) as net:
            result = lookup(self.root / "cache", request)[0]
        self.assertIn("lastModStartDate", net.call_args.args[0])
        summary = source_preview(result)
        self.assertEqual(summary["total"], 40)
        self.assertEqual(summary["next_offset"], 1)
        self.assertEqual(result["window"]["until"], "2026-01-01T00:00:00+00:00")
        with self.assertRaises(FusionError):
            lookup(self.root, dict(request, days=8))

    def test_methods_are_mission_specific_and_all_cards_have_conditions(self):
        src = method_search("src", "fusion-api", "对象 租户 越权 IDOR")
        self.assertEqual(src[0]["id"], "src-object-boundary")
        red = method_search("redteam", "fusion-recon", "红队 打点 入口")
        self.assertEqual(red[0]["id"], "redteam-entry-triage")
        self.assertFalse(method_search("reverse", "fusion-binary", "租户 越权"))
        for card in manifest("knowledge-cards.json", "cards"):
            for key in ("requires", "steps", "disprove", "next", "sources"):
                self.assertTrue(card[key])

    def test_local_search_is_offline_bounded_case_scoped_and_has_readable_snapshot(self):
        with patch("fusion_intel_http.download", side_effect=AssertionError("local must not use network")):
            result = knowledge_query(self.case, self.workspace, "project-a", {"mode": "local", "skill": "fusion-api", "query": "对象 租户 越权"})
        self.assertFalse(result["target_validated"])
        self.assertEqual(result["mission"], "src")
        self.assertLessEqual(len(encode(result)), 6000)
        saved = self.case.root / result["snapshot"]["path"]
        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), result["snapshot"]["sha256"])
        self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["case_id"], self.case.meta("case_id"))
        self.assertTrue(saved.with_suffix(".md").is_file())
        self.assertIn("## 当前方法", saved.with_suffix(".md").read_text(encoding="utf-8"))
        self.assertEqual(result["experiences"]["namespace"]["project"], "project-a")

    def test_wrong_session_cannot_query_or_write_another_case(self):
        file = self.root / "query.json"
        file.write_text(encode({"mode": "local", "skill": "fusion-api", "query": "objects"}))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/fusion.py"), "knowledge", "--workspace", str(self.workspace.root),
                                 "--case", str(self.case.root), "--session", "wrong-session", "--input", str(file)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"session_case_mismatch", result.stdout + result.stderr)
        self.assertFalse((self.case.root / "knowledge").exists())
        valid = subprocess.run([sys.executable, str(ROOT / "scripts/fusion.py"), "knowledge", "--workspace", str(self.workspace.root),
                                "--case", str(self.case.root), "--session", "session-a", "--input", str(file)], capture_output=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["status"], "research_context")

    def test_bad_source_payload_is_unavailable_instead_of_clean(self):
        with patch("fusion_intel_http.download", return_value={"error": "backend down"}):
            result = lookup(self.root / "cache", {"mode": "package", "ecosystem": "npm", "package": "lodash", "version": "4.17.21"})
        self.assertEqual(result[0]["status"], "unavailable")
        self.assertIsNone(result[0]["data"])

    def test_stalled_pagination_is_not_an_endless_repeat_instruction(self):
        with patch("fusion_intel_http.download", return_value={"startIndex": 0, "totalResults": 40, "vulnerabilities": []}):
            result = lookup(self.root / "cache", {"mode": "recent", "until": "2026-01-01T00:00:00Z"})
        self.assertEqual(result[0]["status"], "unavailable")
        with patch("fusion_intel_http.download", return_value={"next_page_token": "repeated"}):
            result = lookup(self.root / "cache", {"mode": "package", "ecosystem": "PyPI", "package": "jinja2", "version": "3.1.4", "cursor": "repeated"})
        self.assertEqual(result[0]["status"], "unavailable")

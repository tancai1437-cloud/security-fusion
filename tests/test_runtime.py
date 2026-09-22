"""Offline reliability tests. No scanners, credentials, external targets or MCP servers."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from fusion_store import Case, FusionError, encode
from fusion_views import bounded, catalog, query, report, resume
from fusion_workspace import Workspace

CONFIG = {"mission_id": "pentest", "objective": "Offline runtime validation",
          "scope": "Temporary files only; no network", "constraints": ["No external targets"]}


def spec(key="one", **changes):
    result = {"key": key, "target": "local-fixture", "target_version": "sha256:fixture-v1",
              "identity_ref": "test-user-a", "check_type": "offline-fixture",
              "inputs": {"sample_ref": "fixture-v1"}, "method_version": "fixture-method-v1",
              "capability_id": "evidence.persist", "skill_id": "fusion-web",
              "purpose": "Validate the local fixture", "depends_on": []}
    result.update(changes)
    return result


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fusion-test-")
        self.root = Path(self.temporary.name)
        self.case = Case.create(self.root / "case", CONFIG)
        self.workspace = Workspace.create(self.root / "workspace")
        self.workspace.bind(self.case, "test-session", "test-project", self.case.meta("case_id"),
                            ["local-fixture", "other-fixture"])
        self.raw = self.root / "raw.txt"
        self.raw.write_text("observed fixture, no vulnerability claim", encoding="utf-8")

    def tearDown(self):
        self.case.close()
        self.workspace.close()
        self.temporary.cleanup()

    def plan(self, *specs):
        return self.case.plan(list(specs or (spec(),)))

    def complete(self, key="one", **kwargs):
        call = self.case.begin(key, "host", "fixture", **kwargs)
        self.case.record(call["attempt_id"], "review", "Captured fixture", [self.raw])
        self.case.review(call["attempt_id"], "done", "Expected fixture observed")
        return call["attempt_id"]

    def cli(self, *argv, expected=0):
        argv = (argv[0], "--workspace", self.workspace.root, "--session", "test-session", *argv[1:])
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "fusion.py"),
                                 *map(str, argv)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout if expected == 0 else result.stderr)

    def test_restart_reuses_completed_check(self):
        self.plan()
        attempt = self.complete()
        self.case.close()
        self.case = Case(self.root / "case")
        result = self.case.begin("one", "host", "fixture")
        self.assertEqual(result["decision"], "reuse")
        self.assertEqual(result["attempt_id"], attempt)

    def test_active_attempt_never_replays_after_restart(self):
        self.plan()
        call = self.case.begin("one", "host", "fixture")
        self.case.close()
        self.case = Case(self.root / "case")
        self.assertEqual(self.case.begin("one", "host", "fixture", "retry")["decision"], "hold")
        self.case.reconcile(call["attempt_id"], "observed", "Recovered fixture result", [self.raw])
        self.assertEqual(self.case.begin("one", "host", "fixture")["status"], "review")
        self.case.review(call["attempt_id"], "done", "Recovered result reviewed")
        self.assertEqual(self.case.begin("one", "host", "fixture")["decision"], "reuse")

    def test_changed_conditions_are_distinct(self):
        checks = [spec(), spec("b", identity_ref="test-user-b"), spec("c", target_version="v2"),
                  spec("d", inputs={"sample_ref": "other"}), spec("e", method_version="v2")]
        result = self.case.plan(checks)
        self.assertEqual(len({r["check_id"] for r in result["checks"]}), 5)

    def test_same_check_across_skills_deduplicates(self):
        result = self.plan(spec(), spec("same", skill_id="fusion-api"))
        self.assertEqual(result["checks"][0]["check_id"], result["checks"][1]["check_id"])
        self.assertTrue(result["checks"][1]["existing"])

    def test_changed_alias_does_not_replace_original(self):
        self.plan()
        with self.assertRaisesRegex(FusionError, "already refers"):
            self.plan(spec(identity_ref="changed"))
        self.assertEqual(query(self.case, "checks")["total"], 1)

    def test_target_search_finds_prior_refutations_without_full_history(self):
        self.plan(spec(), spec("other", target="other-fixture"))
        self.case.note("refuted", "Same target already disproved under user A", "one")
        self.case.note("negative", "Unrelated observation", "other")
        notes = query(self.case, "notes", target="local-fixture")
        self.assertEqual(notes["total"], 1)
        self.assertEqual(notes["items"][0]["kind"], "refuted")
        checks = query(self.case, "checks", target="local-fixture")
        self.assertEqual(checks["total"], 1)
        self.assertEqual(checks["items"][0]["identity_ref"], "test-user-a")

    def test_missing_and_tampered_evidence_block_reuse(self):
        self.plan()
        attempt = self.complete()
        path = self.case.root / self.case.artifacts(attempt)[0]["path"]
        path.write_text("tampered", encoding="utf-8")
        self.assertEqual(self.case.begin("one", "host", "fixture")["status"], "evidence_invalid")
        path.unlink()
        self.assertEqual(self.case.begin("one", "host", "fixture")["decision"], "hold")

    def test_review_requires_evidence(self):
        self.plan()
        attempt = self.case.begin("one", "host", "fixture")["attempt_id"]
        with self.assertRaisesRegex(FusionError, "evidence"):
            self.case.record(attempt, "review", "Nothing captured")
        with self.assertRaisesRegex(FusionError, "Only captured"):
            self.case.review(attempt, "done", "Not enough")

    def test_retry_requires_nonempty_reason(self):
        self.plan()
        attempt = self.case.begin("one", "host", "fixture")["attempt_id"]
        self.case.record(attempt, "failed", "Fixture unavailable")
        self.assertEqual(self.case.begin("one", "host", "fixture")["decision"], "hold")
        with self.assertRaises(FusionError):
            self.case.begin("one", "host", "fixture", " ")
        self.assertEqual(self.case.begin("one", "host", "fixture", "Fixture restored")["decision"], "execute")

    def test_dependencies_and_cycle_rollback(self):
        self.plan(spec(), spec("two", inputs={"sample_ref": "second"}, depends_on=["one"]))
        self.assertEqual(self.case.begin("two", "host", "fixture")["status"], "dependency_blocked")
        self.complete()
        self.assertEqual(self.case.begin("two", "host", "fixture")["decision"], "execute")
        with self.assertRaisesRegex(FusionError, "cycle"):
            self.plan(spec("cycle-a", inputs={"n": 3}, depends_on=["cycle-b"]),
                      spec("cycle-b", inputs={"n": 4}, depends_on=["cycle-a"]))
        self.assertEqual(query(self.case, "checks")["total"], 2)

    def test_dependency_retest_invalidates_downstream_reuse(self):
        self.plan(spec(), spec("two", inputs={"sample_ref": "second"}, depends_on=["one"]))
        self.complete()
        self.complete("two")
        self.complete(retest_reason="Refresh fixture")
        self.assertEqual(self.case.begin("two", "host", "fixture")["status"], "dependency_changed")

    def test_dependency_change_during_execution_blocks_acceptance(self):
        self.plan(spec(), spec("two", inputs={"n": 2}, depends_on=["one"]))
        self.complete()
        attempt = self.case.begin("two", "host", "fixture")["attempt_id"]
        self.case.record(attempt, "review", "Captured", [self.raw])
        self.complete(retest_reason="Refresh fixture")
        with self.assertRaisesRegex(FusionError, "Dependency changed"):
            self.case.review(attempt, "done", "Outdated prerequisite")

    def test_unversioned_results_require_expiry(self):
        self.plan(spec(target_version="unversioned"))
        attempt = self.case.begin("one", "host", "fixture")["attempt_id"]
        self.case.record(attempt, "review", "Captured", [self.raw])
        with self.assertRaisesRegex(FusionError, "validity"):
            self.case.review(attempt, "done", "Valid result")
        with self.assertRaisesRegex(FusionError, "finite"):
            self.case.review(attempt, "done", "Invalid expiry", valid_for=float("inf"))
        self.case.review(attempt, "done", "Valid for a minute", valid_for=60)
        import time
        with patch("fusion_store.time.time", return_value=time.time() + 120):
            self.assertEqual(self.case.begin("one", "host", "fixture")["status"], "stale")

    def test_refutations_survive_and_supersession_is_auditable(self):
        self.plan()
        first = self.case.note("hypothesis", "Possible fixture issue", "one")["note_id"]
        second = self.case.note("refuted", "Control response disproves fixture issue", "one", supersedes=first)
        packet = resume(self.case)
        self.assertEqual([n["id"] for n in packet["required_notes"]], [second["note_id"]])
        history = query(self.case, "notes", identity="one")["items"]
        self.assertTrue(history[0]["superseded"])
        self.assertFalse(history[1]["superseded"])

    def test_large_history_has_bounded_packet_and_pagination(self):
        self.plan()
        for number in range(1000):
            self.case.note("decision", f"Historical decision {number}: " + "x" * 60)
        packet = resume(self.case, maximum=6000)
        self.assertLessEqual(len(encode(packet)), 6000)
        self.assertGreater(packet["omitted_notes"], 900)
        self.assertEqual(query(self.case, "notes", limit=7)["next_offset"], 7)
        self.assertEqual(query(self.case, "notes", offset=999)["next_offset"], None)

    def test_mandatory_constraints_are_never_silently_cut(self):
        self.plan()
        for number in range(4):
            self.case.note("constraint", f"Constraint {number}: " + "x" * 1700)
        with self.assertRaisesRegex(FusionError, "context_budget_exceeded"):
            resume(self.case, maximum=6000)

    def test_catalog_requires_observed_schema_and_does_not_claim_health(self):
        self.assertLess(len(encode(catalog())), 2000)
        self.assertEqual(catalog(capability="http.request")["status"], "unverified_candidates")
        inventory = {"providers": [{"id": "burp", "tools": [
            {"name": "mcp__burp__send_http1_request", "inputSchema": {"type": "object"}},
            {"name": "unrelated_tool", "inputSchema": {"type": "object"}}]}]}
        result = catalog(capability="http.request", inventory=inventory)
        self.assertEqual(len(result["bindings"]), 1)
        self.assertEqual(result["health"], "not_probed")
        inventory["providers"][0]["tools"][0]["inputSchema"] = {"description": "x" * 9000}
        with self.assertRaisesRegex(FusionError, "context_budget_exceeded"):
            bounded(catalog(capability="http.request", inventory=inventory), 6000)

    def test_two_connections_reserve_once(self):
        self.plan()
        def reserve(_):
            connection = Case(self.case.root)
            try:
                return connection.begin("one", "host", "fixture")["decision"]
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, range(2)))
        self.assertCountEqual(results, ["execute", "hold"])

    def test_report_partial_empty_and_evidence_validation(self):
        self.assertEqual(report(self.case)["status"], "partial")
        self.plan()
        self.assertEqual(report(self.case)["counts"], {"pending": 1})
        attempt = self.complete()
        self.assertEqual(report(self.case)["ledger_status"], "completed")
        self.assertEqual(report(self.case)["status"], "partial")
        (self.case.root / self.case.artifacts(attempt)[0]["path"]).unlink()
        self.assertEqual(report(self.case)["counts"], {"evidence_invalid": 1})
        self.assertFalse((self.case.root / "report/findings.json").exists())

    def test_case_cannot_overwrite_or_use_secret_fields(self):
        with self.assertRaisesRegex(FusionError, "already exists"):
            Case.create(self.case.root, CONFIG)
        with self.assertRaisesRegex(FusionError, "secure"):
            self.plan(spec(inputs={"token": "test-value"}))
        self.assertEqual(query(self.case, "checks")["total"], 0)

    def test_cli_runner_captures_large_output_and_skips_duplicate(self):
        self.plan()
        program = ("from pathlib import Path; p=Path('counter'); "
                   "p.write_text(str(int(p.read_text())+1) if p.exists() else '1'); print('X'*100000)")
        args = ("run", "--case", self.case.root, "--check", "one", "--", sys.executable, "-c", program)
        first = self.cli(*args)
        self.assertEqual(first["status"], "review")
        self.assertLess(len(encode(first)), 1000)
        self.cli("review", "--case", self.case.root, "--attempt", first["attempt_id"],
                 "--verdict", "done", "--summary", "Counter and output inspected")
        second = self.cli(*args)
        self.assertEqual(second["decision"], "reuse")
        self.assertEqual((self.case.root / "counter").read_text(), "1")
        changed = self.cli("run", "--case", self.case.root, "--check", "one", "--",
                           sys.executable, "-c", "print('changed')", expected=2)
        self.assertIn("Command changed", changed["error"])

    def test_cli_nonzero_and_timeout_are_not_success(self):
        self.plan(spec(), spec("timeout", inputs={"fixture": "timeout"}))
        failed = self.cli("run", "--case", self.case.root, "--check", "one", "--",
                          sys.executable, "-c", "raise SystemExit(7)")
        self.assertEqual((failed["status"], failed["returncode"]), ("failed", 7))
        timed = self.cli("run", "--case", self.case.root, "--check", "timeout", "--timeout", "0.1",
                         "--", sys.executable, "-c", "import time; time.sleep(5)")
        self.assertEqual(timed["status"], "unknown")
        self.assertEqual(self.case.begin("timeout", "host", "fixture", "retry")["decision"], "hold")

    def test_cli_mcp_error_overrides_requested_review(self):
        self.plan()
        attempt = self.case.begin("one", "host", "fixture")["attempt_id"]
        result = self.root / "mcp.json"
        result.write_text(json.dumps({"isError": True, "content": [{"type": "text", "text": "fixture error"}]}))
        receipt = self.cli("record", "--case", self.case.root, "--attempt", attempt, "--status", "review",
                           "--summary", "MCP fixture error", "--mcp-result", result)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(len(receipt["evidence_ids"]), 1)


if __name__ == "__main__":
    unittest.main()

"""Observable stage handoff, advisory state, and host failures; no target calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fusion_knowledge import source_preview
from evaluate_dsh_trace import evaluate
from fusion_store import Case
from fusion_views import report
from test_runtime import CONFIG, spec


class ComponentUpgradeTests(unittest.TestCase):
    def test_stage_report_links_real_evidence_and_keeps_unreviewed_work_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.txt"
            raw.write_text("controlled observation", encoding="utf-8")
            case = Case.create(root / "case", CONFIG)
            try:
                case.plan([spec()])
                call = case.begin("one", "host", "fixture")["attempt_id"]
                case.record(call, "review", "Awaiting interpretation", [raw])
                result = report(case)
                self.assertEqual(result["status"], "partial")
                stage = case.root / "report/stage.md"
                text = stage.read_text(encoding="utf-8")
                self.assertIn(call, text)
                self.assertIn(case.artifacts(call)[0]["id"], text)
                self.assertIn("review", text)
                before = stage.read_bytes()
                report(case)
                self.assertEqual(before, stage.read_bytes())
                self.assertEqual(case.check("one")["status"], "review")
            finally:
                case.close()

    def test_advisory_state_is_separate_from_target_applicability(self):
        value = {"source": "CVE List V5", "data": {"cveMetadata": {"state": "PUBLISHED"},
                 "containers": {"cna": {"affected": [{"product": "fixture", "versions": [
                     {"version": str(i), "status": "affected"} for i in range(5)]}]}}}}
        preview = source_preview(value)
        self.assertTrue(preview["candidate"])
        self.assertEqual(preview["affected"][0]["omitted_versions"], 2)
        self.assertIn("unknown", preview["applicability"])
        value["data"]["cveMetadata"]["state"] = "REJECTED"
        self.assertFalse(source_preview(value)["candidate"])
        osv = source_preview({"source": "OSV", "data": {"vulns": [{"id": "fixture", "withdrawn": "2026-01-01"}]}})
        self.assertFalse(osv["candidates"][0]["candidate"])

    def test_evaluation_separates_loading_execution_delivery_and_provider_errors(self):
        route = {"type": "tool/call", "data": {"name": "fusion", "arguments": {"action": "route"}}}
        self.assertEqual(evaluate([route])["status"], "not_executed")
        failure = {"type": "turn/end", "data": {"reason": {"kind": "error", "error": {
            "code": "QUOTA", "message": "private-secret-do-not-export"}}}}
        packet = evaluate([route, failure])
        self.assertEqual(packet["status"], "infrastructure_blocked")
        self.assertNotIn("private-secret", json.dumps(packet))
        child = {"type": "observed-tool-result", "child": True, "tool": "fixture", "isError": False}
        self.assertEqual(evaluate([route, child])["status"], "executed_without_delivery")
        partial = {"type": "tool/result", "data": {"message": {"content": [{"type": "text", "text": json.dumps({
            "status": "partial", "report": {"path": "stage.md"}, "verification": "ledger_only"})}]}}}
        self.assertEqual(evaluate([route, child, partial])["status"], "delivery_reported")
        self.assertEqual(evaluate([partial])["status"], "not_executed", "A textual report claim cannot replace observed execution")

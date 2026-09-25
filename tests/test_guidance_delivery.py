"""Regression checks for methodology visibility and honest delivery accounting."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from fusion_store import Case, encode, manifest
from fusion_methods import specialist_card
from fusion_views import catalog, report, resume
from fusion_delivery import inspect_output
from test_runtime import CONFIG, spec


class GuidanceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fusion-delivery-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = Case.create(self.root / "case", CONFIG)
        self.addCleanup(self.case.close)

    def complete_recon(self):
        self.case.plan([spec(skill_id="fusion-recon", capability_id="web.crawl")])
        attempt = self.case.begin("one", "host", "fixture-reader")["attempt_id"]
        raw = self.root / "observation.json"
        raw.write_text('{"fixture":"test-only"}', encoding="utf-8")
        self.case.record(attempt, "review", "Local fixture captured", [raw])
        self.case.review(attempt, "done", "Fixture content checked; limited sample")
        return attempt

    def test_all_specialists_supply_current_method_without_loading_other_specialists(self):
        for module in manifest("specialists.json", "modules"):
            with self.subTest(skill=module["id"]):
                result = catalog(skill=module["id"])
                self.assertEqual(result["path"], module["path"])
                self.assertLessEqual(len(encode(result)), 3500)
                card = result["action_card"]
                source = Path(card["source"]).read_text(encoding="utf-8")
                self.assertIn(card["method"], source)
                self.assertIn(card["completion"], source)
                self.assertEqual(len(card["source_sha256"]), 64)
                self.case.plan([spec(key=module["id"], method_version=module["id"],
                                     skill_id=module["id"], capability_id=module["execution_routes"][0])])
                recovered = resume(self.case, identity=module["id"])
                self.assertEqual(recovered["guidance"]["specialist"]["skill_id"], module["id"])
                self.assertLessEqual(len(encode(recovered)), 6000)

    def test_two_registered_checks_cannot_hide_missing_outputs_or_untracked_work(self):
        self.complete_recon()
        self.case.plan([spec("second", method_version="second", skill_id="fusion-recon", capability_id="web.crawl")])
        attempt = self.case.begin("second", "host", "fixture-reader")["attempt_id"]
        self.case.record(attempt, "review", "Captured second observation", [self.root / "observation.json"])
        self.case.review(attempt, "done", "Second observation reviewed")
        # An unrelated file or an agent's prose claim cannot reveal how many external calls occurred.
        (self.case.root / "untracked-results.txt").write_text("12 other actions claimed", encoding="utf-8")
        result = report(self.case)
        self.assertEqual(result["ledger_status"], "completed")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["registered_attempts"], 2)
        self.assertEqual(result["untracked_actions"], "unknown_without_host_trace")
        self.assertEqual({p["path"] for p in result["delivery_gaps"]},
                         set(specialist_card("fusion-recon")["stage_outputs"]))
        audit = json.loads((self.case.root / "report/delivery.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["routes"], [{"skill_id": "fusion-recon", "capability_id": "web.crawl",
                                           "provider": "host", "tool": "fixture-reader", "attempts": 2}])
        self.assertEqual(audit["methodology_adherence"], "not_measured")

    def test_empty_or_invalid_outputs_are_gaps_and_valid_json_is_not_proof_of_completion(self):
        self.complete_recon()
        paths = [self.case.root / p for p in specialist_card("fusion-recon")["stage_outputs"]]
        for path, content in zip(paths, ("", "not-json", "[]")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        result = report(self.case)
        self.assertEqual({gap["status"] for gap in result["delivery_gaps"]}, {"empty", "invalid_json"})
        for path in paths:
            path.write_text("[]", encoding="utf-8")
        result = report(self.case)
        self.assertEqual(result["delivery_gaps"], [])
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["completion_scope"], "no_overall_completion_claim")

    def test_stage_output_symlink_cannot_satisfy_case_delivery_with_foreign_file(self):
        self.complete_recon()
        external = self.root / "foreign.json"
        external.write_text("[]", encoding="utf-8")
        output = self.case.root / specialist_card("fusion-recon")["stage_outputs"][0]
        output.parent.mkdir(parents=True)
        try:
            output.symlink_to(external)
        except OSError:
            self.skipTest("Symlinks unavailable on this host")
        result = report(self.case)
        self.assertIn({"path": output.relative_to(self.case.root).as_posix(), "status": "outside_case"},
                      result["delivery_gaps"])

    def test_export_directory_requires_nonempty_in_case_file(self):
        relative = "specialists/fusion-js/exported-artifacts/"
        directory = self.case.root / relative
        self.assertEqual(inspect_output(self.case, relative)["status"], "missing")
        directory.mkdir(parents=True)
        self.assertEqual(inspect_output(self.case, relative)["status"], "empty")
        (directory / "empty.txt").write_text("")
        self.assertEqual(inspect_output(self.case, relative)["status"], "empty")
        (directory / "replica.py").write_text("print('fixture')")
        result = inspect_output(self.case, relative)
        self.assertEqual(result["status"], "present_unreviewed")
        self.assertEqual(result["nonempty_files"], 1)

    def test_export_directory_rejects_foreign_symlink(self):
        relative = "specialists/fusion-js/exported-artifacts/"
        directory = self.case.root / relative
        directory.mkdir(parents=True)
        external = self.root / "outside.py"
        external.write_text("print('foreign')")
        try:
            (directory / "foreign.py").symlink_to(external)
        except OSError:
            self.skipTest("Symlinks unavailable on this host")
        self.assertEqual(inspect_output(self.case, relative)["status"], "outside_case")


if __name__ == "__main__":
    unittest.main()

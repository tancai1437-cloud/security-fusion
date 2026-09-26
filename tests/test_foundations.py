"""Acceptance, immutable retrieval and bounded recovery use real local ledgers."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fusion_store import Case, FusionError, encode
from fusion_evidence import read_evidence
from fusion_acceptance import assess, acceptance
from fusion_methods import check_guidance
from fusion_views import resume, query
from test_runtime import CONFIG, spec


class FoundationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fusion-foundations-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = Case.create(self.root / "case", dict(CONFIG, criteria=[
            {"id": "baseline", "question": "What did the initial observation show?"},
            {"id": "comparison", "question": "Does the distinct control reproduce the result?"}]))
        self.addCleanup(self.case.close)
        self.raw = self.root / "raw.md"
        self.raw.write_text("Actual local fixture\n" * 4000, encoding="utf-8")

    def done(self, key, reason=""):
        attempt = self.case.begin(key, "host", "fixture", reason)["attempt_id"]
        self.case.record(attempt, "review", "Saved local observation", [self.raw])
        self.case.review(attempt, "done", "Reviewed fixed sample")
        return attempt

    def test_goal_criteria_require_reviewed_support_and_follow_dependency_versions(self):
        self.case.plan([spec("first"), spec("second", inputs={"control": 2}, depends_on=["first"]),
                        spec("independent", inputs={"other": 3})])
        first, independent = self.done("first"), self.done("independent")
        self.assertEqual(len(acceptance(self.case)["gaps"]), 2)
        second = self.done("second")
        assess(self.case, [{"criterion": "baseline", "attempts": [independent], "summary": "Independent reviewed fact"},
                           {"criterion": "comparison", "attempts": [second], "summary": "Comparison with initial result"}])
        self.assertEqual(acceptance(self.case)["gaps"], [])
        self.raw.write_text("Fixture revision two", encoding="utf-8")
        self.done("first", "Changed input fixture")
        audit = acceptance(self.case)
        self.assertEqual(audit["gaps"], [{"id": "comparison", "status": "support_changed", "attempts": [second]}])
        self.assertEqual(audit["items"][0]["status"], "supported")
        with self.assertRaises(FusionError):
            assess(self.case, [{"criterion": "comparison", "attempts": [first], "summary": "Obsolete attempt"}])

    def test_unsettled_and_foreign_support_cannot_accept_a_goal(self):
        self.case.plan([spec()])
        pending = self.case.begin("one", "host", "fixture")["attempt_id"]
        for identity in (pending, "CALL-foreign"):
            with self.assertRaises(FusionError):
                assess(self.case, [{"criterion": "baseline", "attempts": [identity], "summary": "Not verified"}])
        self.assertEqual(len(acceptance(self.case)["gaps"]), 2)

    def test_artifact_read_uses_permanent_copy_with_bounded_paging(self):
        self.case.plan([spec()])
        attempt = self.done("one")
        artifact = query(self.case, "artifacts", identity="one")["items"][0]
        self.raw.unlink()  # Host scratch cleanup cannot remove formal evidence.
        first = read_evidence(self.case, artifact["id"], length=16384, maximum=1800)
        self.assertLessEqual(len(encode(first)), 1800)
        self.assertEqual(first["attempt_id"], attempt)
        self.assertTrue(first["next_offset"])
        other = Case.create(self.root / "other", CONFIG)
        try:
            with self.assertRaisesRegex(FusionError, "Unknown artifact"):
                read_evidence(other, artifact["id"])
        finally:
            other.close()
        (self.case.root / artifact["path"]).write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(FusionError, "changed"):
            read_evidence(self.case, artifact["id"])

    def test_dependency_result_precedes_full_method_under_budget_pressure(self):
        self.case.plan([spec("first"), spec("next", inputs={"control": 2}, depends_on=["first"])])
        first = self.done("first")
        guidance = check_guidance(spec())
        guidance["specialist"]["method"] *= 20  # Simulate a large specialist without modifying the pack.
        with patch("fusion_views.check_guidance", return_value=guidance):
            packet = resume(self.case, maximum=6000)
        self.assertEqual(packet["results"][0]["attempt_id"], first)
        self.assertTrue(packet["guidance"]["specialist"]["method_deferred"])
        self.assertIn("source_sha256", packet["guidance"]["specialist"])
        self.assertLessEqual(len(encode(packet)), 6000)
        self.assertEqual(packet["config"]["criteria"][1]["id"], "comparison")

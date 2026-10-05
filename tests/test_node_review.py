"""Node decisions survive restart, stay case-local and cannot launder evidence."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fusion_node_review import review_node, latest_node
from fusion_store import Case, FusionError, encode
from fusion_views import resume
from fusion_progress import continuation_query
from test_runtime import CONFIG, spec


class NodeReviewTests(unittest.TestCase):
    def test_linked_pending_node_survives_restart_and_never_replays_or_crosses_cases(self):
        self.case.review(self.attempt, "done", "Controlled evidence")
        self.case.plan([spec("side", inputs={"sample": 2}), spec("deep", inputs={"sample": 3}, depends_on=["one"])])
        follow = self.case.check("deep")["id"]
        review_node(self.case, dict(self.data, next_check="deep"))
        self.case.close()
        self.case = Case(self.root / "case")
        self.assertEqual(resume(self.case, focus=True)["current"]["id"], follow)
        self.assertIn(self.data["next_test"], continuation_query(self.case, "generic goal"))
        with self.assertRaises(FusionError):
            review_node(self.case, dict(self.data, next_check="one"))
        with self.assertRaises(FusionError):
            review_node(self.case, dict(self.data, next_check="foreign-case-key"))
        with self.assertRaises(FusionError):
            review_node(self.case, dict(self.data, next_check="deep", decision="blocked"))
        unsettled = self.case.begin("side", "host", "fixture")["check_id"]
        self.assertEqual(resume(self.case, focus=True)["current"]["id"], unsettled)
        self.assertEqual(self.case.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fusion-node-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = Case.create(self.root / "case", CONFIG)
        self.addCleanup(lambda: self.case.close())
        self.case.plan([spec()])
        self.attempt = self.case.begin("one", "host", "local-fixture")["attempt_id"]
        raw = self.root / "observed.txt"
        raw.write_text("controlled fixture denied; no target network", encoding="utf-8")
        self.case.record(self.attempt, "review", "Observed fixture", [raw])
        self.data = {"question": "Which control produced the observed refusal?", "attempts": [self.attempt],
                     "conclusion": "The controlled fixture refused; cause not yet established.",
                     "unresolved": ["Is the tested identity valid?"], "decision": "continue",
                     "next_test": "Check the existing normal control for the same test identity."}

    def test_unreviewed_fake_and_foreign_attempts_cannot_be_promoted(self):
        with self.assertRaises(FusionError):
            review_node(self.case, self.data)
        self.case.review(self.attempt, "done", "The fixture refusal was observed")
        with self.assertRaises(FusionError):
            review_node(self.case, dict(self.data, attempts=["CALL-invented"]))
        other = Case.create(self.root / "other", CONFIG)
        try:
            with self.assertRaises(FusionError):
                review_node(other, self.data)
            self.assertIsNone(latest_node(other))
        finally:
            other.close()

    def test_real_result_restart_compaction_and_corruption(self):
        self.case.review(self.attempt, "done", "Observed refusal, not a vulnerability")
        record = review_node(self.case, self.data)
        self.assertFalse(record["task_completed"])
        self.case.close()
        self.case = Case(self.root / "case")
        packet = resume(self.case)
        self.assertEqual(packet["node_review"]["next_test"], self.data["next_test"])
        self.assertLessEqual(len(encode(packet)), 6000)
        self.assertEqual(packet["node_review"]["status"], "historical_supported")
        artifact = self.case.artifacts(self.attempt)[0]
        (self.case.root / artifact["path"]).write_text("changed", encoding="utf-8")
        self.assertEqual(latest_node(self.case)["status"], "evidence_changed")
        self.assertFalse(latest_node(self.case)["support_current"])

    def test_ready_to_deliver_does_not_complete_case_and_rejects_known_gaps(self):
        self.case.review(self.attempt, "done", "Controlled result")
        with self.assertRaises(FusionError):
            review_node(self.case, dict(self.data, decision="ready_to_deliver"))
        ready = review_node(self.case, dict(self.data, decision="ready_to_deliver", unresolved=[]))
        self.assertFalse(ready["task_completed"])
        self.assertEqual(self.case.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 1)

    def test_larger_review_uses_pointer_without_expanding_recovery_budget(self):
        self.case.review(self.attempt, "done", "Controlled result")
        review_node(self.case, dict(self.data, question="问" * 240, conclusion="证" * 500,
                                   unresolved=["未" * 180] * 4, next_test="测" * 300))
        packet = resume(self.case, maximum=3600)
        self.assertLessEqual(len(encode(packet)), 3600)
        self.assertTrue(packet.get("node_review") or packet.get("node_review_deferred"))

"""Long-history recovery uses ledger evidence, not the conversational summary."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fusion_store import Case, encode
from fusion_views import resume
from test_runtime import CONFIG, spec


class RecoveryProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fusion-progress-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = Case.create(self.root / "case", CONFIG)
        self.addCleanup(lambda: self.case.close())
        self.raw = self.root / "response.txt"
        self.raw.write_text("Local fixture: control denied", encoding="utf-8")

    def complete(self, key, summary="Control denied; no access observed"):
        call = self.case.begin(key, "host", "local-reader")
        self.case.record(call["attempt_id"], "review", "Captured", [self.raw])
        self.case.review(call["attempt_id"], "done", summary)
        return call["attempt_id"]

    def test_dependency_conclusions_survive_restart_and_unrelated_history(self):
        self.case.plan([spec("baseline"), spec("next", inputs={"n": 2}, depends_on=["baseline"])])
        baseline = self.complete("baseline")
        evidence = self.case.artifacts(baseline)[0]["id"]
        note = self.case.note("negative", "The control rules out the first hypothesis", "baseline", [evidence])
        for n in range(30):
            key = f"noise-{n}"
            self.case.plan([spec(key, inputs={"noise": n})])
            self.complete(key, "Unrelated local observation")
        for n in range(150):
            self.case.note("decision", f"Historical planning text {n}: " + "x" * 70)
        self.case.close()
        self.case = Case(self.root / "case")
        recovered = resume(self.case, maximum=6000)
        self.assertLessEqual(len(encode(recovered)), 6000)
        result = recovered["results"][0]
        self.assertEqual(result["attempt_id"], baseline)
        self.assertTrue(result["reusable"])
        self.assertEqual(result["notes"][0]["id"], note["note_id"])
        self.assertEqual(result["evidence"][0]["id"], evidence)
        self.assertEqual(recovered["next_action"]["action"], "execute")
        self.assertEqual(recovered["next_action"]["check_id"], self.case.check("next")["id"])
        self.assertGreater(recovered["omitted_results"], 0)

    def test_expired_and_tampered_results_never_return_as_reusable(self):
        self.case.plan([spec("old")])
        attempt = self.complete("old")
        self.case.db.execute("UPDATE checks SET expires=1")
        expired = resume(self.case)["results"][0]
        self.assertFalse(expired["reusable"])
        self.assertEqual(expired["status"], "stale")
        self.assertTrue(expired["historical_evidence_valid"])
        artifact = self.case.artifacts(attempt)[0]
        (self.case.root / artifact["path"]).write_text("tampered", encoding="utf-8")
        altered = resume(self.case)["results"][0]
        self.assertFalse(altered["historical_evidence_valid"])
        self.assertFalse(altered["reusable"])

    def test_many_unsettled_calls_are_paged_without_losing_attention(self):
        self.case.plan([spec(f"step-{n}", inputs={"n": n}) for n in range(80)])
        for n in range(80):
            self.case.begin(f"step-{n}", "host", "fixture")
        recovered = resume(self.case, maximum=6000)
        self.assertLessEqual(len(encode(recovered)), 6000)
        self.assertEqual(recovered["next_action"]["action"], "reconcile")
        self.assertEqual(len(recovered["in_flight"]) + recovered["omitted_in_flight"], 80)
        self.assertIn(recovered["current"]["attempt_id"], [a["id"] for a in recovered["in_flight"]])

    def test_blocked_dependencies_and_independent_work_have_distinct_statuses(self):
        self.case.plan([spec("first"), spec("blocked", inputs={"n": 2}, depends_on=["first"]),
                        spec("independent", inputs={"n": 3})])
        attempt = self.case.begin("first", "host", "fixture")["attempt_id"]
        self.case.record(attempt, "blocked", "Missing local fixture", [self.raw])
        recovered = resume(self.case)
        self.assertEqual(recovered["next_action"]["check_id"], self.case.check("independent")["id"])
        waiting = next(c for c in recovered["queue"] if c["id"] == self.case.check("blocked")["id"])
        self.assertFalse(waiting["ready"])
        self.assertEqual(waiting["blocked_by"], [self.case.check("first")["id"]])

    def test_case_results_do_not_leak_to_another_case(self):
        self.case.plan([spec("a")])
        self.complete("a", "Only case A knows this marker")
        other = Case.create(self.root / "other-case", CONFIG)
        try:
            other.plan([spec("b", target="other-fixture")])
            self.assertEqual(resume(other)["results"], [])
            self.assertNotIn("Only case A", encode(resume(other)))
        finally:
            other.close()

    def test_target_outcome_precedes_incidental_file_writes_when_no_check_is_pending(self):
        self.case.plan([spec("baseline", capability_id="http.request")])
        observed = self.complete("baseline")
        for n in range(12):
            self.case.plan([spec(f"write-{n}", inputs={"file": n})])
            self.complete(f"write-{n}", "Wrote a report fragment")
        recovered = resume(self.case, fallback_skill="fusion-web")
        self.assertIsNone(recovered["current"])
        self.assertEqual(recovered["results"][0]["attempt_id"], observed)
        self.assertEqual(recovered["guidance"]["specialist"]["skill_id"], "fusion-web")

    def test_large_historical_routing_is_optional_but_current_adapter_is_preserved(self):
        self.case.plan([spec("active")])
        key = self.case.check("active")["id"]
        adapter = {"status": "mcp_preflight_required", "profile": "long/private/profile/" * 12}
        with self.case.transaction():
            self.case.event("observation_routed", key, {
                "observation": {"target": "local-fixture", "resource": "/fixture"},
                "selected": key, "adapter_hint": adapter,
                "decisions": [{"id": f"historical-{n}", "reason": "x" * 900} for n in range(6)]})
        recovered = resume(self.case, maximum=6000)
        self.assertLessEqual(len(encode(recovered)), 6000)
        self.assertEqual(recovered["routing"]["adapter_hint"], adapter)
        self.assertGreater(recovered["routing"]["omitted_decisions"], 0)
        self.assertEqual(recovered["routing"]["omitted_decisions"] + len(recovered["routing"]["decisions"]), 6)
        self.assertEqual(recovered["routing"]["details"]["kind"], "events")
        self.assertEqual(recovered["config"]["constraints"], CONFIG["constraints"])
        self.assertIn("guidance", recovered)

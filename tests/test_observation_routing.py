"""Deterministic routing tests; HTTP is loopback-only, MCP receipts are synthetic."""
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import test_start
import test_environment
from fusion_store import Case
from fusion_views import resume


class ObservationRoutingTests(unittest.TestCase):
    setUp = test_start.StartTests.setUp
    cli = test_start.StartTests.cli
    task = test_start.StartTests.task
    write_task = test_start.StartTests.write_task
    start = test_start.StartTests.start

    def seed(self):
        self.write_task(self.task())
        started = self.start("--", sys.executable, "-c", "print('SYNTHETIC ROUTER FIXTURE; not a real assessment')")
        execution = started["execution"]
        self.cli("review", "--attempt", execution["attempt_id"], "--verdict", "done",
                 "--summary", "Reviewed synthetic fixture for router mechanics only", "--valid-for", "600")
        self.source = started["check_id"]
        self.evidence = execution["evidence_ids"]

    def observation(self, *features, **changes):
        value = {"target": "local-fixture", "resource": "/api/controlled-objects",
                 "target_version": "unversioned", "identity_ref": "controlled-role-pair",
                 "source_check": self.source, "evidence_ids": self.evidence,
                 "features": list(features), "inputs": {}}
        value.update(changes)
        return value

    def route(self, data, *args, expected=0):
        path = self.root / "observations.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return self.cli("route", "--input", path, *args, expected=expected)

    def test_http_entry_selects_specialist_capability_and_real_program_without_manual_check(self):
        if not shutil.which("curl"):
            self.skipTest("curl unavailable")
        with test_start.local_service() as (url, requests):
            task = self.task(url)
            del task["check"]
            task["entry"] = url
            self.write_task(task)
            started = self.start("--execute-local")
            self.assertEqual(started["guidance"]["specialist"]["skill_id"], "fusion-recon")
            self.assertEqual(started["execution"]["route"]["capability_id"], "web.crawl")
            self.assertEqual(started["execution"]["status"], "review")
            self.assertEqual(requests, ["/baseline"])
            self.assertIn("fusion-local-baseline", (self.case / started["execution"]["capture_dir"] / "stdout").read_text())
            self.cli("review", "--attempt", started["execution"]["attempt_id"], "--verdict", "done",
                     "--summary", "Real loopback response read; baseline only", "--valid-for", "600")
            self.source, self.evidence = started["check_id"], started["execution"]["evidence_ids"]
            data = self.observation("http.entry", target=url, resource=url, identity_ref="anonymous")
            routed = self.route(data, "--execute-local")
            self.assertEqual(routed["decisions"][0]["status"], "done")
            self.assertNotIn("call", routed)
            self.assertEqual(requests, ["/baseline"])
            data["features"] = ["api.object", "identity.available"]
            data["inputs"] = {"request_ref": "observed-request"}
            routed = self.route(data)
            self.assertEqual(routed["selected"]["id"], "identity-baseline")
            self.assertEqual(routed["check"]["skill_id"], "fusion-api")
            self.assertEqual(routed["check"]["capability_id"], "http.request")
            data["features"] = ["js.bundle"]
            routed = self.route(data)
            self.assertEqual(routed["selected"]["id"], "js-request-map")
            self.assertEqual(routed["execution"]["status"], "tool_selection_required")

    def test_missing_identity_blocks_only_dependent_procedures_and_survives_resume(self):
        self.seed()
        routed = self.route(self.observation("http.auth-required", "api.object"))
        self.assertNotIn("check_id", routed)
        self.assertTrue(all(d["status"] == "blocked" for d in routed["decisions"]))
        self.assertEqual(self.cli("query", "--kind", "checks")["total"], 1)
        restored = self.cli("resume")
        self.assertEqual(restored["routing"]["decisions"], routed["decisions"])
        self.assertIsNone(restored["current"])
        # An independent JS evidence path remains selectable.
        routed = self.route(self.observation("http.auth-required", "api.object", "js.bundle"))
        self.assertEqual(routed["selected"]["id"], "js-request-map")

    def test_login_shell_suppresses_downstream_input_variants(self):
        self.seed()
        routed = self.route(self.observation("http.login-shell", "input.text", "response.business",
                                            inputs={"request_ref": "request", "parameter": "q"}))
        self.assertEqual(routed["selected"]["id"], "login-shell-map")
        self.assertEqual(next(d for d in routed["decisions"] if d["procedure_id"] == "input-context")["status"], "suppressed")

    def test_same_facts_reuse_check_but_changed_objects_get_a_distinct_check(self):
        self.seed()
        data = self.observation("api.object", "identity.verified", "objects.controlled",
                                inputs={"identity_refs": ["role-a", "role-b"],
                                        "object_refs": ["owned-a", "owned-b"], "operation": "read"})
        first = self.route(data)
        data["evidence_ids"] = list(reversed(self.evidence))
        repeated = self.route(data)
        self.assertEqual(first["check_id"], repeated["check_id"])
        self.assertEqual(self.cli("query", "--kind", "checks")["total"], 2)
        restored = self.cli("resume")
        self.assertEqual(restored["guidance"]["procedure"]["id"], "object-boundary")
        self.assertLessEqual(len(json.dumps(restored, ensure_ascii=False, separators=(",", ":"))), 6000)
        data["inputs"]["object_refs"] = ["owned-c", "owned-d"]
        changed = self.route(data)
        self.assertNotEqual(first["check_id"], changed["check_id"])
        self.assertEqual(self.cli("query", "--kind", "checks")["total"], 3)

    def test_unreviewed_cross_target_unknown_or_unbacked_facts_never_create_work(self):
        self.seed()
        for changes in ({"target": "foreign-target"}, {"evidence_ids": ["E-invented"]},
                        {"target_version": "different-version"}, {"features": ["invented-feature"]},
                        {"inputs": {"identity_refs": ["same", "same"]}}):
            with self.subTest(changes=changes):
                self.route(self.observation("js.bundle", **changes), expected=2)
                self.assertEqual(self.cli("query", "--kind", "checks")["total"], 1)
        self.cli("run", "--check", self.source, "--retest-reason", "Synthetic state transition for test",
                 "--", sys.executable, "-c", "print('SYNTHETIC ROUTER FIXTURE; not a real assessment')")
        self.route(self.observation("js.bundle"), expected=2)

    def test_budget_failure_does_not_mutate_plan(self):
        self.seed()
        self.route(self.observation("js.bundle"), "--max-chars", "512", expected=2)
        self.assertEqual(self.cli("query", "--kind", "checks")["total"], 1)

    def test_mcp_selection_uses_current_verified_name_and_never_calls_fixture(self):
        self.seed()
        fixture = test_environment.EnvironmentTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.ready()
        flags = ("--environment", fixture.root, "--agent", "dsh", "--instance", fixture.instance)
        data = self.observation("browser.cache")
        chosen = self.route(data, *flags, "--execute-local")
        self.assertEqual(chosen["execution"]["status"], "mcp_host_call_required")
        self.assertEqual(chosen["execution"]["name"], fixture.tool)
        self.assertNotIn("call", chosen)
        expired_host = self.route(data, "--environment", fixture.root, "--agent", "dsh", "--instance", "new-host")
        self.assertEqual(expired_host["execution"]["status"], "tool_selection_required")
        self.assertEqual(self.cli("query", "--kind", "attempts")["total"], 1)

    def test_candidate_review_stays_on_existing_evidence_instead_of_expanding_collection(self):
        self.seed()
        chosen = self.route(self.observation("candidate.observed", "api.operation", "js.bundle"))
        self.assertEqual(chosen["selected"]["id"], "candidate-review")
        self.assertEqual(chosen["execution"]["status"], "evidence_review_required")

    def test_installed_method_changes_do_not_replace_saved_inflight_method(self):
        self.seed()
        chosen = self.route(self.observation("js.bundle"))
        case = Case(self.case)
        try:
            with patch("fusion_routing.procedure_card", side_effect=AssertionError("Must use the persisted method")):
                packet = resume(case)
            self.assertEqual(packet["guidance"]["procedure"], chosen["selected"])
            self.assertNotIn("procedure_snapshot", packet["current"]["spec"])
        finally:
            case.close()


if __name__ == "__main__":
    unittest.main()

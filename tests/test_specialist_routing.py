"""Exercise specialist selection, real helper processes, capture and recovery."""
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import test_start
import test_observation_routing
import test_specialist_tools
from fusion_routing import local_binding, procedures, tool_binding
from fusion_store import Case


class SpecialistRoutingTests(unittest.TestCase):
    setUp = test_start.StartTests.setUp
    cli = test_start.StartTests.cli
    task = test_start.StartTests.task
    write_task = test_start.StartTests.write_task
    start = test_start.StartTests.start
    route = test_observation_routing.ObservationRoutingTests.route

    def test_binary_entry_reaches_real_profile_and_managed_route_survives_restart(self):
        sample = (self.root / "sample.dll").resolve()
        sample.write_bytes(test_specialist_tools.pe_fixture(True))
        task = self.task(str(sample))
        del task["check"]
        task["entry"] = str(sample)
        task["config"]["mission_id"] = "reverse"
        self.write_task(task)
        started = self.start("--execute-local")
        execution = started["execution"]
        profile = json.loads((self.case / execution["capture_dir"] / "stdout").read_text(encoding="utf-8"))
        self.assertEqual(profile["kind"], "managed")
        self.assertEqual(execution["route"]["capability_id"], "binary.profile")
        held = self.start("--execute-local", "--expect-case", started["case_id"])
        self.assertEqual(held["execution"]["decision"], "hold")
        self.cli("review", "--attempt", execution["attempt_id"], "--verdict", "done",
                 "--summary", "Synthetic PE metadata verified; not a runnable managed assembly", "--valid-for", "600")
        data = {"target": str(sample), "resource": str(sample), "target_version": "sha256:" + profile["sha256"],
                "identity_ref": "local-read-only", "source_check": started["check_id"],
                "evidence_ids": execution["evidence_ids"], "features": profile["feature_hints"],
                "inputs": {"question": "Locate the fixture's relevant type"}}
        routed = self.route(data)
        self.assertEqual(routed["selected"]["id"], "managed-context")
        restored = self.cli("resume")
        self.assertEqual(restored["guidance"]["procedure"]["id"], "managed-context")
        self.assertLessEqual(len(json.dumps(restored, ensure_ascii=False, separators=(",", ":"))), 6000)
        repeated = self.start("--execute-local", "--expect-case", started["case_id"])
        self.assertEqual(repeated["execution"]["decision"], "reuse")
        self.assertEqual(self.cli("query", "--kind", "attempts")["total"], 1)

    def test_unknown_dll_stays_unknown_and_missing_question_blocks_analysis(self):
        sample = (self.root / "unknown.dll").resolve()
        sample.write_text("not a binary", encoding="utf-8")
        task = self.task(str(sample))
        del task["check"]
        task.update(entry=str(sample))
        task["config"]["mission_id"] = "reverse"
        self.write_task(task)
        started = self.start("--execute-local")
        call = started["execution"]
        output = json.loads((self.case / call["capture_dir"] / "stdout").read_text(encoding="utf-8"))
        self.cli("review", "--attempt", call["attempt_id"], "--verdict", "done",
                 "--summary", "Unknown format confirmed; no native or managed claim", "--valid-for", "600")
        data = dict(target=str(sample), resource=str(sample), target_version="sha256:" + output["sha256"],
                    identity_ref="local-read-only", source_check=started["check_id"], evidence_ids=call["evidence_ids"],
                    features=output["feature_hints"], inputs={})
        self.assertNotIn("selected", self.route(data))
        # Explicit synthetic router facts, not a classification claim about the text fixture.
        data["features"] = ["binary.profiled", "binary.native"]
        blocked = self.route(data)
        self.assertEqual(blocked["decisions"][0]["missing"], ["inputs.question"])

    def test_dotnet_binding_uses_real_cli_name_and_missing_tool_stays_unready(self):
        sample = (self.root / "sample.dll").resolve()
        sample.write_bytes(test_specialist_tools.pe_fixture(True))
        data = {"target": str(sample), "resource": str(sample), "target_version": "synthetic"}
        procedure = next(p for p in procedures() if p["id"] == "managed-context")
        with patch("fusion_specialist_bindings.shutil.which", return_value=None):
            self.assertEqual(tool_binding(data, procedure)["status"], "tool_selection_required")
        with patch("fusion_specialist_bindings.shutil.which", return_value="/synthetic/bin/ilspycmd"):
            self.assertEqual(local_binding(data, procedure)["argv"],
                             ["/synthetic/bin/ilspycmd", "-l", "c", str(sample)])
        data["target"] = str(self.root / "different-target")
        self.assertIsNone(local_binding(data, procedure))

    def test_proxy_route_makes_three_real_requests_then_holds_and_reuses(self):
        if not shutil.which("curl"):
            self.skipTest("HTTP entry fixture requires existing curl")
        with test_specialist_tools.proxy_fixture() as (base, requests):
            target = base + "/trusts-client"
            task = self.task(target)
            del task["check"]
            task["entry"] = target
            self.write_task(task)
            started = self.start("--execute-local")
            call = started["execution"]
            self.cli("review", "--attempt", call["attempt_id"], "--verdict", "done",
                     "--summary", "Real loopback baseline has diagnostic IP and denied protected access", "--valid-for", "600")
            data = dict(target=target, resource=target, target_version="unversioned", identity_ref="anonymous",
                        source_check=started["check_id"], evidence_ids=call["evidence_ids"],
                        features=["http.entry", "http.proxy-trust"], inputs={})
            routed = self.route(data, "--execute-local")
            self.assertEqual(routed["selected"]["id"], "proxy-trust")
            self.assertEqual(len(requests), 4)
            output = json.loads((self.case / routed["call"]["capture_dir"] / "stdout").read_text(encoding="utf-8"))
            self.assertEqual(len(output["requests"]), 3)
            self.assertEqual(output["verdict"], "observations_only")
            self.cli("resume")
            held = self.route(data, "--execute-local")
            self.assertNotIn("call", held)
            self.assertEqual(next(d for d in held["decisions"] if d["procedure_id"] == "proxy-trust")["status"], "review")
            self.cli("review", "--attempt", routed["call"]["attempt_id"], "--verdict", "done",
                     "--summary", "Only diagnostic IP changed; protected access stayed false", "--valid-for", "600")
            repeated = self.route(data, "--execute-local")
            self.assertNotIn("call", repeated)
            self.assertEqual(next(d for d in repeated["decisions"] if d["procedure_id"] == "proxy-trust")["status"], "done")
            self.assertEqual(len(requests), 4)

    def test_crash_log_executes_read_only_and_reproduction_needs_real_materials(self):
        log = (self.root / "synthetic-asan.log").resolve()
        log.write_text("SYNTHETIC\nERROR: AddressSanitizer: stack-overflow\n", encoding="utf-8")
        target = str(self.root.resolve())
        task = self.task(target)
        self.write_task(task)
        started = self.start("--", sys.executable, "-c", "print('Controlled local diagnostic fixture')")
        call = started["execution"]
        self.cli("review", "--attempt", call["attempt_id"], "--verdict", "done",
                 "--summary", "Fixture directory bound", "--valid-for", "600")
        data = dict(target=target, resource=str(log), target_version="unversioned", identity_ref="local-read-only",
                    source_check=started["check_id"], evidence_ids=call["evidence_ids"], features=["crash.log"], inputs={})
        routed = self.route(data, "--execute-local")
        self.assertEqual(routed["selected"]["id"], "crash-triage")
        output = json.loads((self.case / routed["call"]["capture_dir"] / "stdout").read_text(encoding="utf-8"))
        self.assertEqual(output["classification"], ["stack-exhaustion"])
        self.assertFalse(output["executed_sample"])
        data["features"] = ["crash.classified"]
        result = self.route(data)
        self.assertNotIn("selected", result)
        self.assertIn("inputs.control_ref", result["decisions"][0]["missing"])
        self.assertIn("sample.controlled", result["decisions"][0]["missing"])

    def test_expected_crash_exit_can_be_reviewed_and_its_own_artifact_routed(self):
        sample = (self.root / "sample.bin").resolve()
        sample.write_bytes(test_specialist_tools.pe_fixture())
        task = self.task(str(sample))
        task["check"].update(skill_id="fusion-binary", capability_id="memory.reproduce",
                             inputs={"expected_exit_codes": [7]}, purpose="Capture a synthetic process diagnostic")
        self.write_task(task)
        command = "import sys;sys.stderr.write('SYNTHETIC AddressSanitizer: heap-use-after-free\\n');sys.exit(7)"
        started = self.start("--", sys.executable, "-c", command)
        call = started["execution"]
        self.assertEqual(call["returncode"], 7)
        self.assertEqual(call["status"], "review")
        receipt = json.loads((self.case / call["capture_dir"] / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["expected_exit_codes"], [7])
        self.cli("review", "--attempt", call["attempt_id"], "--verdict", "done",
                 "--summary", "Captured the declared synthetic diagnostic; no actual sanitizer invoked", "--valid-for", "600")
        case = Case(self.case)
        try:
            artifact = next(a for a in case.artifacts(call["attempt_id"])
                            if (self.case / a["path"]).read_bytes().startswith(b"SYNTHETIC"))
        finally:
            case.close()
        data = dict(target=str(sample), resource="evidence:" + artifact["id"], target_version="unversioned",
                    identity_ref="local-read-only", source_check=started["check_id"], evidence_ids=call["evidence_ids"],
                    features=["crash.log"], inputs={})
        routed = self.route(data, "--execute-local")
        result = json.loads((self.case / routed["call"]["capture_dir"] / "stdout").read_text(encoding="utf-8"))
        self.assertEqual(result["classification"], ["heap-use-after-free"])
        data["resource"] = "evidence:E-from-a-different-case"
        foreign = self.route(data, "--execute-local")
        self.assertEqual(foreign["execution"]["status"], "tool_selection_required")
        self.assertNotIn("call", foreign)

    def test_nonzero_expectation_is_not_a_generic_ignore_errors_switch(self):
        task = self.task()
        task["check"]["inputs"] = {"expected_exit_codes": [7]}
        self.write_task(task)
        result = self.start("--", sys.executable, "-c", "raise SystemExit(7)", expected=2)
        self.assertIn("memory.reproduce", str(result))


if __name__ == "__main__":
    unittest.main()

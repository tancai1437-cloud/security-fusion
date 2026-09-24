"""Execute the entire adapter path against a test-only stdio MCP and real loopback HTTP."""
import json
from pathlib import Path
import sys
import unittest

import test_start


FIXTURE = Path(__file__).parent / "fixtures" / "stdio_mcp.py"


class ExecutionFlowTests(unittest.TestCase):
    setUp = test_start.StartTests.setUp
    cli = test_start.StartTests.cli
    task = test_start.StartTests.task
    write_task = test_start.StartTests.write_task
    start = test_start.StartTests.start

    def setup_call(self, url, mode="ok"):
        self.write_task(self.task(url))
        started = self.start()
        self.check = started["check_id"]
        self.trace = self.root / "protocol.jsonl"
        self.profile = self.root / "mcp.json"
        self.arguments = self.root / "arguments.json"
        self.profile.write_text(json.dumps({"transport": "stdio", "context_mode": "explicit-target",
            "provider": "burp", "command": [sys.executable, "-u", str(FIXTURE), str(self.trace), mode],
            "bindings": {"http.request": {"tool": "fixture_http_read", "target_argument": "target"}}}), encoding="utf-8")
        self.arguments.write_text(json.dumps({"target": url}), encoding="utf-8")
        return started

    def call(self, *args, **kwargs):
        return self.cli("mcp-run", "--check", self.check, "--profile", self.profile,
                        "--arguments", self.arguments, *args, **kwargs)

    def methods(self):
        return [json.loads(l)["method"] for l in self.trace.read_text().splitlines()] if self.trace.exists() else []

    def test_real_mcp_call_advance_and_restart_dedup(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            result = self.call()
            self.assertEqual(result["status"], "review")
            self.assertEqual(requests, ["/baseline"])
            self.assertEqual(self.methods(), ["initialize", "notifications/initialized", "tools/list", "tools/call"])
            captured = json.loads((self.case / result["capture_dir"] / "result.json").read_text())
            self.assertIn("fusion-local-baseline", captured["content"][0]["text"])
            restored = self.cli("resume")
            self.assertEqual(restored["current"]["status"], "review")
            self.assertEqual(self.call()["decision"], "hold")
            routed = self.cli("advance", "--check", self.check, "--summary", "Loopback JSON marker inspected",
                              "--valid-for", "600", "--feature", "api.operation", "--resource", "/api/items")
            self.assertEqual(routed["check"]["skill_id"], "fusion-api")
            self.assertEqual(routed["selected"]["id"], "api-contract")
            self.assertEqual(self.call()["decision"], "reuse")
            self.assertEqual(self.methods().count("tools/call"), 1)
            self.assertEqual(requests, ["/baseline"])
            self.assertLessEqual(len(json.dumps(routed, ensure_ascii=False)), 6000)
            audit = self.cli("report")
            self.assertEqual(audit["registered_attempts"], 1)

    def test_foreign_session_and_target_rejected_before_process_launch(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            self.call(session="foreign", expected=2)
            self.arguments.write_text(json.dumps({"target": "http://outside.invalid"}))
            self.assertIn("target", self.call(expected=2)["error"])
            self.assertEqual(self.methods(), [])
            self.assertEqual(requests, [])
            self.assertEqual(self.cli("query", "--kind", "attempts")["total"], 0)

    def test_missing_tool_is_blocked_and_tool_error_is_failed(self):
        for mode, expected in [("missing", "blocked"), ("error", "failed")]:
            with self.subTest(mode=mode), test_start.local_service() as (url, requests):
                self.case = self.root / mode
                self.workspace = self.root / (mode + "-workspace")
                self.setup_call(url, mode)
                result = self.call()
                self.assertEqual(result["status"], expected)
                self.assertEqual(self.call()["decision"], "hold")
                self.assertEqual(requests, [])

    def test_timeout_and_pending_task_are_unknown_without_retry(self):
        for mode in ["timeout", "task", "rpc-error"]:
            with self.subTest(mode=mode), test_start.local_service() as (url, requests):
                self.case = self.root / mode
                self.workspace = self.root / (mode + "-workspace")
                self.setup_call(url, mode)
                result = self.call("--timeout", "2" if mode == "timeout" else "5")
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(self.call()["decision"], "hold")
                self.assertEqual(requests, [])

    def test_live_pagination_and_changed_arguments(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url, "paged")
            result = self.call()
            self.assertEqual(result["status"], "review")
            self.assertEqual(self.methods().count("tools/list"), 2)
            self.arguments.write_text(json.dumps({"target": url, "different_condition": True}))
            self.assertIn("Command changed", self.call(expected=2)["error"])
            self.assertEqual(requests, ["/baseline"])

    def test_advance_does_not_review_without_judgement_or_on_invalid_fact(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            self.call()
            self.cli("advance", "--check", self.check, "--feature", "api.operation", expected=2)
            self.cli("advance", "--check", self.check, "--summary", "Read marker", "--valid-for", "600",
                     "--feature", "invented", expected=2)
            self.assertEqual(self.cli("resume")["current"]["status"], "review")
            self.assertEqual(requests, ["/baseline"])

    def test_stateful_profile_is_not_bypassed(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            profile = json.loads(self.profile.read_text())
            profile["context_mode"] = "current-browser"
            self.profile.write_text(json.dumps(profile))
            self.assertIn("explicit-target", self.call(expected=2)["error"])
            self.assertEqual(self.methods(), [])
            self.assertEqual(requests, [])

    def test_nonanonymous_identity_requires_an_explicit_matching_argument(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            spec = self.task(url)["check"]
            spec.update(key="authenticated", identity_ref="controlled-role")
            plan = self.root / "plan.json"
            plan.write_text(json.dumps([spec]))
            self.check = self.cli("plan", "--input", plan)["checks"][0]["check_id"]
            self.assertIn("identity_argument", self.call(expected=2)["error"])
            profile = json.loads(self.profile.read_text())
            profile["bindings"]["http.request"]["identity_argument"] = "identity_ref"
            self.profile.write_text(json.dumps(profile))
            self.arguments.write_text(json.dumps({"target": url, "identity_ref": "other-role"}))
            self.assertIn("identity", self.call(expected=2)["error"])
            self.assertEqual(self.methods(), [])
            self.assertEqual(requests, [])

    def test_advance_keeps_login_shell_out_of_input_testing(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            self.call()
            inputs = self.root / "observed.json"
            inputs.write_text(json.dumps({"request_ref": "fixture", "parameter": "q"}))
            routed = self.cli("advance", "--check", self.check, "--summary", "Synthetic branching assertion only",
                              "--valid-for", "600", "--feature", "http.login-shell", "--feature", "input.text",
                              "--feature", "response.business", "--inputs", inputs)
            self.assertEqual(routed["selected"]["id"], "login-shell-map")
            self.assertEqual(routed["check"]["skill_id"], "fusion-js")
            decision = next(d for d in routed["decisions"] if d["procedure_id"] == "input-context")
            self.assertEqual(decision["status"], "suppressed")
            self.assertEqual(requests, ["/baseline"])

    def test_advance_selects_configured_mcp_without_claiming_ready_or_calling_it(self):
        with test_start.local_service() as (url, requests):
            self.setup_call(url)
            self.call()
            inputs = self.root / "parameters.json"
            inputs.write_text(json.dumps({"request_ref": "fixture-observation", "parameter": "fixture"}))
            routed = self.cli("advance", "--check", self.check, "--summary", "Synthetic routing fixture only",
                              "--valid-for", "600", "--feature", "input.text", "--feature", "response.business",
                              "--inputs", inputs, "--mcp-profile", self.profile, "--execute-local")
            self.assertEqual(routed["selected"]["id"], "input-context")
            self.assertEqual(routed["execution"]["name"], "fixture_http_read")
            self.assertEqual(routed["execution"]["status"], "mcp_preflight_required")
            self.assertNotIn("command", routed["execution"])
            self.assertNotIn("call", routed)
            self.assertEqual(requests, ["/baseline"])
            restored = self.cli("resume")
            self.assertEqual(restored["routing"]["adapter_hint"]["profile"], str(self.profile.resolve()))
            self.assertEqual(restored["routing"]["adapter_hint"]["status"], "mcp_preflight_required")


if __name__ == "__main__":
    unittest.main()

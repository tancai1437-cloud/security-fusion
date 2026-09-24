"""Structured observations -> real MCP/HTTP -> evidence; not an LLM or real-provider benchmark."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import unittest

import test_start
import test_observation_routing


CASES = {
    "function-boundary": ("api.role-operation", ["identity.verified", "roles.controlled"]),
    "reset-binding": ("auth.password-reset", ["accounts.controlled"]),
    "order-transition": ("business.transition", ["identity.verified", "business.fixture"]),
    "single-use-effect": ("business.single-use", ["identity.verified", "business.fixture"]),
}


def inputs(operation):
    return {"identity_refs": ["fixture-a", "fixture-b"], "request_ref": "fixture-normal-request",
            "challenge_ref": "fixture-a-proof", "state_ref": "fixture-initial-state",
            "fixture_ref": "fixture-owned-pair", "rule_ref": "fixture-service-contract",
            "operation": operation, "scope_ref": "local-disposable-test-only"}


@contextmanager
def business_service():
    """A disposable stateful lab; all four controls correctly reject invalid effects."""
    calls = []
    state = {"normal": "ready", "variant": "draft", "redemptions": 0,
             "account_a_revision": 0, "account_b_revision": 0}

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.send(200, {"fixture": "TEST ONLY", "state": state})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            identity = self.headers.get("X-Fixture-Identity")
            calls.append((identity, body))
            action, code = body["action"], 200
            if action == "role":
                code = 200 if identity == "fixture-admin" else 403
            elif action == "recover":
                if body["account"] != "fixture-a" or body["proof_ref"] != "fixture-a-proof":
                    code = 403
                else:
                    state["account_a_revision"] += 1
            elif action == "ship":
                order = body["order"]
                if state[order] != "ready":
                    code = 409
                else:
                    state[order] = "shipped"
            elif action == "redeem":
                # Repeated success is intentional: only one durable effect for this operation.
                state["redemptions"] = 1
            else:
                code = 400
            self.send(code, {"fixture": "TEST ONLY", "state": state})

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:{}/operation".format(server.server_port), calls, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class BusinessRoutingTests(unittest.TestCase):
    setUp = test_start.StartTests.setUp
    cli = test_start.StartTests.cli
    task = test_start.StartTests.task
    write_task = test_start.StartTests.write_task
    start = test_start.StartTests.start
    seed = test_observation_routing.ObservationRoutingTests.seed
    observation = test_observation_routing.ObservationRoutingTests.observation
    route = test_observation_routing.ObservationRoutingTests.route

    def test_each_method_blocks_missing_prerequisites_or_references(self):
        self.seed()
        for method, (feature, prerequisites) in CASES.items():
            features = [feature, *prerequisites, "operation.permitted"]
            for missing in prerequisites + ["operation.permitted"]:
                with self.subTest(method=method, missing=missing):
                    data = self.observation(*[f for f in features if f != missing], inputs=inputs(method))
                    result = self.route(data)
                    self.assertNotIn("check_id", result)
                    self.assertIn(missing, result["decisions"][0]["missing"])
            data = self.observation(*features, inputs=inputs(method))
            del data["inputs"]["scope_ref"]
            self.assertNotIn("check_id", self.route(data))
        self.assertEqual(self.cli("query", "--kind", "checks")["total"], 1)

    def test_specific_business_fact_cannot_fall_back_to_generic_when_blocked(self):
        self.seed()
        for feature in ("business.transition", "business.single-use"):
            result = self.route(self.observation("business.order", "identity.verified", feature,
                                                inputs=inputs("bounded-operation")))
            self.assertNotIn("check_id", result)
            generic = next(d for d in result["decisions"] if d["procedure_id"] == "business-transition")
            self.assertEqual(generic["status"], "suppressed")
        result = self.route(self.observation("business.order", "identity.verified",
                                            inputs=inputs("normal-flow-observation")))
        self.assertEqual(result["selected"]["id"], "business-transition")

    def test_reset_can_be_anonymous_and_changed_control_gets_distinct_check(self):
        self.seed()
        data = self.observation("auth.password-reset", "accounts.controlled", "operation.permitted",
                                identity_ref="anonymous", inputs=inputs("account-binding"))
        first = self.route(data)
        self.assertEqual(first["selected"]["id"], "reset-binding")
        self.assertEqual(self.route(data)["check_id"], first["check_id"])
        data["inputs"]["challenge_ref"] = "fixture-new-proof"
        self.assertNotEqual(self.route(data)["check_id"], first["check_id"])
        data["features"].append("http.login-shell")
        shell = self.route(data)
        self.assertEqual(next(d for d in shell["decisions"] if d["procedure_id"] == "reset-binding")["status"],
                         "suppressed")

    def test_four_methods_reach_http_capture_controls_and_recover_without_replay(self):
        experiments = {
            "function-boundary": [("fixture-admin", {"action": "role"}), ("fixture-user", {"action": "role"})],
            "reset-binding": [("anonymous", {"action": "recover", "account": account,
                                "proof_ref": "fixture-a-proof"}) for account in ("fixture-a", "fixture-b")],
            "order-transition": [("fixture-a", {"action": "ship", "order": order})
                                 for order in ("normal", "variant")],
            "single-use-effect": [("fixture-a", {"action": "redeem", "operation_ref": "same-operation"})] * 2,
        }
        for method, (feature, prerequisites) in CASES.items():
            with self.subTest(method=method), business_service() as (url, calls, state):
                self.case, self.workspace = self.root / method, self.root / (method + "-workspace")
                task = self.task(url)
                task["config"]["constraints"] = ["Disposable loopback lab only; controlled mutations permitted"]
                self.write_task(task)
                started = self.start("--", sys.executable, "-c",
                                     "import sys,urllib.request; print(urllib.request.urlopen(sys.argv[1]).read().decode())", url)
                parameters = self.root / "parameters.json"
                parameters.write_text(json.dumps(inputs(method)), encoding="utf-8")
                profile, arguments, trace = [self.root / name for name in ("profile.json", "args.json", "trace.jsonl")]
                profile.write_text(json.dumps({"transport": "stdio", "context_mode": "explicit-target",
                    "provider": "burp", "command": [sys.executable, "-u",
                    str(Path(__file__).parent / "fixtures" / "business_mcp.py"), str(trace)],
                    "bindings": {"http.request": {"tool": "fixture_compare_requests", "target_argument": "target",
                                                   "identity_argument": "identity_ref"}}}), encoding="utf-8")
                identity = "anonymous" if method == "reset-binding" else "fixture-controlled-pair"
                flags = [value for f in [feature, *prerequisites, "operation.permitted"] for value in ("--feature", f)]
                chosen = self.cli("advance", "--check", started["check_id"], "--summary", "Lab initial states read",
                                  "--valid-for", "600", "--identity", identity, *flags,
                                  "--inputs", parameters, "--mcp-profile", profile)
                self.assertEqual(chosen["selected"]["id"], method)
                self.assertEqual(chosen["execution"]["name"], "fixture_compare_requests")
                self.assertEqual(calls, [])
                self.assertLessEqual(len(json.dumps(chosen, ensure_ascii=False)), 6000)
                arguments.write_text(json.dumps({"target": url, "identity_ref": identity,
                    "requests": [{"identity_ref": role, "body": body} for role, body in experiments[method]]}), encoding="utf-8")
                command = ("mcp-run", "--check", chosen["check_id"], "--profile", profile, "--arguments", arguments)
                executed = self.cli(*command)
                self.assertEqual(executed["status"], "review")
                captured = json.loads((self.case / executed["capture_dir"] / "result.json").read_text())
                responses = json.loads(captured["content"][0]["text"])
                expected_status = {"function-boundary": [200, 403], "reset-binding": [200, 403],
                                   "order-transition": [200, 409], "single-use-effect": [200, 200]}[method]
                self.assertEqual([r["status"] for r in responses], expected_status)
                self.assertEqual(len(calls), 2)
                if method == "reset-binding":
                    self.assertEqual((state["account_a_revision"], state["account_b_revision"]), (1, 0))
                elif method == "order-transition":
                    self.assertEqual((state["normal"], state["variant"]), ("shipped", "draft"))
                elif method == "single-use-effect":
                    self.assertEqual(state["redemptions"], 1)
                restored = self.cli("resume")
                self.assertEqual(restored["guidance"]["procedure"], chosen["selected"])
                self.assertLessEqual(len(json.dumps(restored, ensure_ascii=False, separators=(",", ":"))), 6000)
                self.assertEqual(self.cli(*command)["decision"], "hold")
                self.cli("review", "--attempt", executed["attempt_id"], "--verdict", "done",
                         "--summary", "Lab controls and server state verified; expected boundary held", "--valid-for", "600")
                self.assertEqual(self.cli(*command)["decision"], "reuse")
                self.assertEqual(len(calls), 2)
                again = self.cli("advance", "--check", started["check_id"], "--identity", identity,
                                 *flags, "--inputs", parameters, "--mcp-profile", profile)
                self.assertNotIn("check_id", again)
                self.assertEqual(again["decisions"][0]["status"], "done")
                delivery = self.cli("report")
                self.assertEqual(delivery["registered_attempts"], 2)
                self.assertEqual(delivery["status"], "partial")


if __name__ == "__main__":
    unittest.main()

"""First-action integration tests: real local processes and loopback HTTP only."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fusion.py"


@contextmanager
def local_service():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            body = b'{"fixture":"fusion-local-baseline","authenticated":false}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:{}/baseline".format(server.server_port), requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class StartTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fusion-start-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = self.root / "case"
        self.workspace = self.root / "workspace"
        self.input = self.root / "task.json"

    def task(self, target="local-fixture"):
        return {
            "project": "integration-fixtures", "targets": [target],
            "config": {"mission_id": "pentest", "objective": "Capture a local baseline",
                       "scope": "Only the explicitly bound local fixture; no external targets",
                       "constraints": ["Read only; no vulnerability claims"]},
            "check": {"key": "baseline", "target": target, "target_version": "unversioned",
                      "identity_ref": "anonymous", "check_type": "baseline-read",
                      "inputs": {"endpoint_ref": target}, "method_version": "baseline-read-v1",
                      "capability_id": "http.request", "skill_id": "fusion-web",
                      "purpose": "Read the fixture response and verify its marker", "depends_on": []},
        }

    def write_task(self, task):
        self.input.write_text(json.dumps(task), encoding="utf-8")

    def cli(self, command, *args, session="session-a", case=None, expected=0):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), command,
             "--workspace", str(self.workspace), "--session", session,
             "--case", str(case or self.case), *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout if expected == 0 else result.stderr)

    def start(self, *args, **kwargs):
        return self.cli("start", "--input", self.input, *args, **kwargs)

    def test_first_command_reaches_http_then_recovers_without_replaying(self):
        with local_service() as (url, requests):
            self.write_task(self.task(url))
            command = [sys.executable, "-c",
                       "import sys,urllib.request; print(urllib.request.urlopen(sys.argv[1], timeout=5).read().decode())", url]
            started = self.start("--", *command)
            execution = started["execution"]
            self.assertEqual(requests, ["/baseline"])
            self.assertEqual(execution["status"], "review")
            capture = self.case / execution["capture_dir"] / "stdout"
            self.assertEqual(json.loads(capture.read_text())["fixture"], "fusion-local-baseline")

            # Every CLI invocation is a new process, so recovery cannot rely on model/process memory.
            recovered = self.cli("resume")
            self.assertEqual(recovered["in_flight"][0]["id"], execution["attempt_id"])
            held = self.start("--expect-case", started["case_id"], "--", *command)
            self.assertEqual(held["execution"]["decision"], "hold")
            self.assertEqual(len(requests), 1)
            self.cli("review", "--attempt", execution["attempt_id"], "--verdict", "done",
                     "--summary", "Fixture JSON and marker verified; baseline only", "--valid-for", "600")
            reused = self.start("--expect-case", started["case_id"], "--", *command)
            self.assertEqual(reused["execution"]["decision"], "reuse")
            self.assertEqual(len(requests), 1)
            report = self.cli("report")
            self.assertEqual(report["ledger_status"], "completed")
            self.assertEqual(report["status"], "partial")
            self.assertEqual(report["delivery_status"], "missing_artifacts")
            self.assertIn("baseline only", (self.case / "report" / "ledger.md").read_text())
            self.assertGreater(len(json.loads((self.case / "evidence" / "records.json").read_text())), 0)

    def test_recovery_brings_back_method_and_unreviewed_result_before_next_specialist(self):
        with local_service() as (url, requests):
            task = self.task(url)
            task["check"].update(skill_id="fusion-recon", capability_id="web.crawl")
            self.write_task(task)
            command = [sys.executable, "-c",
                       "import sys,urllib.request; print(urllib.request.urlopen(sys.argv[1], timeout=5).read().decode())", url]
            started = self.start("--", *command)
            card = started["guidance"]["specialist"]
            self.assertEqual(card["skill_id"], "fusion-recon")
            self.assertTrue(card["method"])
            self.assertIn("specialists/fusion-recon/baselines.json", card["stage_outputs"])
            self.assertEqual(started["execution"]["route"]["tool"], Path(sys.executable).name)

            next_spec = self.task(url)["check"]
            next_spec.update(key="api-next", check_type="api-read", skill_id="fusion-api")
            plan = self.root / "next.json"
            plan.write_text(json.dumps([next_spec]), encoding="utf-8")
            planned = self.cli("plan", "--input", plan)
            self.assertEqual(planned["guidance"]["specialist"]["skill_id"], "fusion-api")

            # Process/conversation memory is absent: recover the unreviewed recon, not the pending API.
            recovered = self.cli("resume")
            self.assertEqual(recovered["current"]["status"], "review")
            self.assertEqual(recovered["guidance"]["specialist"], card)
            self.assertLessEqual(len(json.dumps(recovered, ensure_ascii=False, separators=(",", ":"))), 6000)
            self.assertTrue(recovered["current"]["evidence"])
            self.assertEqual(self.cli("run", "--check", "baseline", "--", *command)["decision"], "hold")
            self.assertEqual(requests, ["/baseline"])

            self.cli("review", "--attempt", started["execution"]["attempt_id"], "--verdict", "done",
                     "--summary", "Fixture marker read; no scope-wide conclusion", "--valid-for", "600")
            advanced = self.cli("resume")
            self.assertEqual(advanced["current"]["skill"], "fusion-api")
            self.assertEqual(advanced["guidance"]["specialist"]["skill_id"], "fusion-api")
            audit = self.cli("report")
            self.assertEqual(audit["registered_attempts"], 1)
            self.assertEqual(audit["status"], "partial")
            self.assertEqual(requests, ["/baseline"])

    def test_start_without_command_does_not_invent_execution_or_mcp_readiness(self):
        self.write_task(self.task())
        result = self.start()
        self.assertEqual(result["status"], "planned_not_executed")
        self.assertNotIn("execution", result)
        self.assertEqual(self.cli("query", "--kind", "attempts")["total"], 0)
        resumed = self.cli("resume")
        self.assertEqual(resumed["current"]["status"], "pending")
        self.assertEqual(resumed["current"]["target"], "local-fixture")

    def test_existing_case_requires_id_and_preserves_session_scope_and_config(self):
        task = self.task()
        self.write_task(task)
        started = self.start()
        self.assertIn("--expect-case", self.start(expected=2)["error"])
        self.assertIn("Wrong expected", self.start("--expect-case", "CASE-wrong", expected=2)["error"])
        self.assertIn("owner", self.start("--expect-case", started["case_id"], session="session-b", expected=2)["error"])
        task["config"]["scope"] = "Different scope"
        self.write_task(task)
        self.assertIn("config changed", self.start("--expect-case", started["case_id"], expected=2)["error"])
        self.assertEqual(self.cli("resume")["config"]["scope"], self.task()["config"]["scope"])
        self.assertEqual(self.cli("query", "--kind", "attempts")["total"], 0)

    def test_invalid_initial_check_creates_no_case_or_workspace(self):
        for change in ({"target": "outside-binding"}, {"depends_on": ["missing"]}, {"skill_id": "invented"}):
            with self.subTest(change=change):
                task = self.task()
                task["check"].update(change)
                self.write_task(task)
                self.start(expected=2)
                self.assertFalse(self.case.exists())
                self.assertFalse(self.workspace.exists())

    def test_historical_files_are_not_overwritten_by_a_new_ledger(self):
        self.case.mkdir()
        old = self.case / "tested-results.json"
        old.write_text('{"negative":"already tested"}')
        self.write_task(self.task())
        self.assertIn("migrate", self.start(expected=2)["error"])
        self.assertFalse((self.case / "case.sqlite3").exists())
        self.assertEqual(old.read_text(), '{"negative":"already tested"}')

    def test_failed_process_is_captured_and_does_not_complete_check(self):
        self.write_task(self.task())
        result = self.start("--", sys.executable, "-c", "import sys; sys.stderr.write('fixture failure'); sys.exit(7)")
        self.assertEqual(result["execution"]["status"], "failed")
        self.assertEqual(result["execution"]["returncode"], 7)
        stderr = self.case / result["execution"]["capture_dir"] / "stderr"
        self.assertEqual(stderr.read_text(), "fixture failure")
        self.assertEqual(self.cli("report")["status"], "partial")

    def test_workspace_reused_while_two_target_sessions_remain_isolated(self):
        self.write_task(self.task("target-a"))
        first = self.start()
        self.write_task(self.task("target-b"))
        second_case = self.root / "case-b"
        second = self.start(session="session-b", case=second_case)
        self.assertNotEqual(first["case_id"], second["case_id"])
        self.assertEqual(self.cli("resume")["current"]["target"], "target-a")
        self.assertEqual(self.cli("resume", session="session-b", case=second_case)["current"]["target"], "target-b")
        self.cli("resume", session="session-a", case=second_case, expected=2)


if __name__ == "__main__":
    unittest.main()

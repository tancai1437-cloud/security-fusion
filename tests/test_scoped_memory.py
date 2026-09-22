"""Cross-case isolation, experience lifecycle, and retrieval evaluation fixtures."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from fusion_store import Case, FusionError, encode
from fusion_memory import Memory
from fusion_search import text_digest
from fusion_views import resume
from fusion_workspace import Workspace, file_lock
from test_runtime import CONFIG, spec


def card(**changes):
    document = {"title": "Object ownership checks", "lesson": "Compare object ownership under distinct test identities.",
                "conditions": ["An authenticated object API with test accounts"],
                "counterexamples": ["A successful status code alone is not evidence of access"],
                "tags": ["api", "authorization"], "skill_id": "fusion-api"}
    document.update(changes)
    return document


class ScopedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fusion-scope-")
        self.root = Path(self.temporary.name)
        self.workspace = Workspace.create(self.root / "registry")
        self.memory = Memory(self.workspace)
        self.cases = []
        self.a = self.new_case("a", "project-one", "session-a")
        self.b = self.new_case("b", "project-one", "session-b")
        self.c = self.new_case("c", "project-two", "session-c")

    def new_case(self, name, project, session):
        config = dict(CONFIG, objective="Offline case " + name)
        case = Case.create(self.root / name, config)
        self.cases.append(case)
        self.workspace.bind(case, session, project, case.meta("case_id"), ["local-fixture"])
        case.plan([spec()])
        return case

    def tearDown(self):
        for case in self.cases:
            case.close()
        self.workspace.close()
        self.temporary.cleanup()

    def source(self, case=None):
        case = case or self.a
        raw = self.root / ("raw-" + case.meta("case_id"))
        raw.write_text("offline control evidence", encoding="utf-8")
        call = case.begin("one", "host", "fixture")
        if call["decision"] == "execute":
            case.record(call["attempt_id"], "review", "Observed offline fixture", [raw])
            case.review(call["attempt_id"], "done", "Fixture reviewed")
        evidence = [a["id"] for a in case.artifacts(call["attempt_id"])]
        return case.note("negative", "Control observation under specific fixture conditions", "one", evidence)["note_id"]

    def add(self, document=None, case=None, active=True, scope="project", supersedes=None):
        case = case or self.a
        identity = self.memory.candidate(case, document or card(), self.source(case), supersedes)["memory_id"]
        if active:
            self.memory.review(case, identity, "accept", scope, "Fixture evidence and applicability reviewed", True, 3600)
        return identity

    def cli(self, command, case=None, session="session-a", *rest, expected=0):
        args = [sys.executable, "-X", "utf8", str(SCRIPTS / "fusion.py"), command,
                "--case", str((case or self.a).root), "--workspace", str(self.workspace.root), "--session", session, *rest]
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout if expected == 0 else result.stderr)

    def test_wrong_case_recovery_and_write_rejected(self):
        for command, extra in [("resume", []), ("note", ["--kind", "fact", "--text", "wrong-case"])]:
            result = self.cli(command, self.b, "session-a", *extra, expected=2)
            self.assertIn("session_case_mismatch", result["error"])
        self.assertEqual(self.b.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0], 0)

    def test_same_project_cases_keep_facts_separate(self):
        self.a.note("fact", "A-only-marker", "one")
        self.b.note("fact", "B-only-marker", "one")
        self.assertNotIn("B-only-marker", encode(self.cli("resume")))
        self.assertNotIn("A-only-marker", encode(self.cli("resume", self.b, "session-b")))

    def test_binding_requires_expected_case_and_unique_owner(self):
        with self.assertRaisesRegex(FusionError, "Wrong expected"):
            self.workspace.bind(self.a, "another", "project-one", self.b.meta("case_id"), ["local-fixture"])
        with self.assertRaisesRegex(FusionError, "owner"):
            self.workspace.bind(self.a, "another", "project-one", self.a.meta("case_id"), ["local-fixture"])
        with self.assertRaises(FusionError):
            self.workspace.bind(self.a, "session-b", "project-one", self.a.meta("case_id"), ["local-fixture"])

    def test_handoff_fences_old_session_and_preserves_unknown_calls(self):
        call = self.a.begin("one", "host", "fixture")
        self.a.record(call["attempt_id"], "unknown", "Interrupted fixture")
        self.workspace.handoff(self.a, "session-a", "session-new", "Explicit recovery after host exit")
        self.cli("resume", self.a, "session-a", expected=2)
        packet = self.cli("resume", self.a, "session-new")
        self.assertEqual(packet["in_flight"][0]["status"], "unknown")

    def test_file_lock_blocks_same_case_but_not_other_case(self):
        with file_lock(self.workspace.lock_path(self.a)):
            result = self.cli("resume", expected=2)
            self.assertIn("case_busy", result["error"])
            self.assertEqual(self.cli("resume", self.b, "session-b")["case_id"], self.b.meta("case_id"))
        self.assertEqual(self.cli("resume")["case_id"], self.a.meta("case_id"))

    def test_scope_edit_detected(self):
        self.a.db.execute("UPDATE meta SET value=? WHERE key='config'", (encode(dict(CONFIG, scope="changed")),))
        with self.assertRaisesRegex(FusionError, "snapshot_mismatch"):
            self.workspace.check_session(self.a, "session-a")

    def test_case_cannot_be_rebound_through_a_second_registry(self):
        other = Workspace.create(self.root / "other-registry")
        try:
            with self.assertRaisesRegex(FusionError, "pinned"):
                other.bind(self.a, "bypass", "project-one", self.a.meta("case_id"), ["local-fixture"])
        finally:
            other.close()

    def test_failed_binding_does_not_pin_a_new_case(self):
        case = Case.create(self.root / "unbound", CONFIG)
        self.cases.append(case)
        with self.assertRaises(FusionError):
            self.workspace.bind(case, "session-a", "mistaken-project", case.meta("case_id"), ["local-fixture"])
        self.assertIsNone(case.db.execute("SELECT value FROM meta WHERE key='workspace_binding'").fetchone())
        self.workspace.bind(case, "fresh-session", "correct-project", case.meta("case_id"), ["local-fixture"])

    def test_cli_target_guard_rejects_plan_before_write(self):
        path = self.root / "plan.json"
        path.write_text(encode([spec("outside", target="outside-fixture")]), encoding="utf-8")
        self.cli("plan", self.a, "session-a", "--input", str(path), expected=2)
        self.assertEqual(self.a.db.execute("SELECT COUNT(*) FROM checks").fetchone()[0], 1)

    def observation(self, **changes):
        result = {"provider": "burp", "context_id": "fixture-project", "target": "local-fixture",
                  "identity_ref": "test-user-a", "observed_at": time.time(), "evidence_ref": "host-fixture-observation"}
        result.update(changes)
        return result

    def test_tool_slot_exclusive_and_identity_checked(self):
        self.workspace.context_set(self.a, "host/burp/instance", self.observation())
        with self.assertRaisesRegex(FusionError, "another case"):
            self.workspace.context_set(self.b, "host/burp/instance", self.observation())
        self.workspace.context_check(self.a, "one", "burp", "host/burp/instance")
        self.workspace.context_set(self.a, "host/burp/instance", self.observation(identity_ref="other-user"))
        with self.assertRaisesRegex(FusionError, "identity"):
            self.workspace.context_check(self.a, "one", "burp", "host/burp/instance")

    def test_context_staleness_and_pending_call_release(self):
        self.workspace.context_set(self.a, "slot", self.observation())
        with patch("fusion_workspace.time.time", return_value=time.time() + 400):
            with self.assertRaisesRegex(FusionError, "stale"):
                self.workspace.context_check(self.a, "one", "burp", "slot")
        call = self.a.begin("one", "burp", "fixture")
        with self.assertRaisesRegex(FusionError, "pending"):
            self.workspace.context_release(self.a, "slot")
        with self.assertRaisesRegex(FusionError, "pending"):
            self.workspace.context_set(self.a, "slot", self.observation(context_id="other-project"))
        self.a.record(call["attempt_id"], "failed", "Confirmed fixture call did not proceed")
        self.workspace.context_release(self.a, "slot")
        self.workspace.context_set(self.b, "slot", self.observation())

    def test_missing_mcp_context_does_not_reserve_a_call(self):
        result = self.cli("begin", self.a, "session-a", "--check", "one", "--provider", "burp",
                          "--tool", "fixture", expected=2)
        self.assertIn("--context", result["error"])
        self.assertEqual(self.a.db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 0)

    def test_only_reviewed_experiences_retrieved(self):
        identity = self.add(active=False)
        self.assertEqual(self.memory.search("project-one", "fusion-api", "ownership")["items"], [])
        with self.assertRaisesRegex(FusionError, "redaction"):
            self.memory.review(self.a, identity, "accept", "project", "Unchecked", False, 3600)
        self.memory.review(self.a, identity, "accept", "project", "Reviewed fixture", True, 3600)
        self.assertEqual(self.memory.search("project-one", "fusion-api", "ownership")["items"][0]["memory_id"], identity)

    def test_project_namespace_filters_before_ranking(self):
        identity = self.add()
        self.assertEqual(self.memory.search("project-two", "fusion-api", "ownership")["items"], [])
        self.assertEqual(self.memory.search("project-two", "fusion-api", "ownership", True)["items"], [])
        self.assertEqual(self.memory.search("project-one", "fusion-api", "ownership")["items"][0]["memory_id"], identity)
        self.assertEqual(self.memory.search("project-one", "fusion-web", "ownership")["items"], [])
        with self.assertRaises(FusionError):
            self.memory.show("project-two", identity)

    def test_general_memory_requires_opt_in_and_does_not_mark_checks_done(self):
        self.add(scope="general")
        self.assertEqual(self.memory.search("project-two", "fusion-api", "ownership")["items"], [])
        result = self.memory.search("project-two", "fusion-api", "ownership", True)
        self.assertEqual(len(result["items"]), 1)
        self.assertNotIn("source", result["items"][0])
        self.assertEqual(self.b.check("one")["status"], "pending")

    def test_changed_source_cannot_be_promoted(self):
        identity = self.add(active=False)
        source = json.loads(self.memory.row(identity)["source"])
        self.a.note("refuted", "Previous observation corrected", "one", supersedes=source["note_id"])
        with self.assertRaises(FusionError):
            self.memory.review(self.a, identity, "accept", "general", "Stale source", True, 3600)

    def test_unreviewed_supporting_evidence_cannot_enter_experience(self):
        self.source()
        self.a.plan([spec("unreviewed", inputs={"sample": "unreviewed"})])
        call = self.a.begin("unreviewed", "host", "fixture")
        raw = self.root / "unreviewed.txt"
        raw.write_text("unreviewed output", encoding="utf-8")
        result = self.a.record(call["attempt_id"], "review", "Captured only", [raw])
        note = self.a.note("fact", "Unreviewed supporting claim", "one", result["evidence_ids"])
        with self.assertRaisesRegex(FusionError, "currently valid"):
            self.memory.candidate(self.a, card(), note["note_id"])

    def test_version_supersession_and_retirement(self):
        old = self.add()
        new = self.add(card(lesson="Use paired identities and verify actual object ownership."), supersedes=old)
        self.assertEqual(self.memory.row(old)["state"], "retired")
        with self.assertRaisesRegex(FusionError, "reactivated"):
            self.memory.review(self.a, old, "accept", "project", "Outdated version", True, 3600)
        ids = {r["memory_id"] for r in self.memory.search("project-one", "fusion-api", "ownership")["items"]}
        self.assertEqual(ids, {new})
        self.memory.review(self.a, new, "retire", "project", "Method no longer applicable")
        self.assertEqual(self.memory.search("project-one", "fusion-api", "ownership")["items"], [])

    def test_expiry_and_duplicate_memory(self):
        identity = self.add()
        duplicate = self.memory.candidate(self.a, card(), self.source())
        self.assertEqual(duplicate["memory_id"], identity)
        self.assertTrue(duplicate["existing"])
        with patch("fusion_memory.time.time", return_value=time.time() + 7200):
            self.assertEqual(self.memory.search("project-one", "fusion-api", "ownership")["items"], [])

    def test_chinese_substring_and_fts_query_escaping(self):
        identity = self.add(card(title="对象归属校验", lesson="对不同身份执行对象权限对照，保存失败反例。"))
        result = self.memory.search("project-one", "fusion-api", '对象权限 " OR *')
        self.assertEqual(result["items"][0]["memory_id"], identity)

    def test_vector_model_hash_dimension_and_finite_validation(self):
        identity = self.add()
        digest = self.memory.row(identity)["digest"]
        data = {"model": "fixture-vector-v1", "text_sha256": digest, "vector": [1, 0]}
        self.memory.embed("project-one", identity, data)
        for invalid in (dict(data, text_sha256="wrong"), dict(data, vector=[math.nan, 0]),
                        dict(data, vector=[0, 0]), dict(data, vector=[1, 0, 0])):
            with self.assertRaises(FusionError):
                self.memory.embed("project-one", identity, invalid)

    def test_hybrid_vector_recall_with_namespace_filter(self):
        identity = self.add(card(title="Paired account procedure", lesson="Use two controlled principals.",
                                 conditions=["Fixture conditions"], counterexamples=["Fixture limits"], tags=["fixture"]))
        foreign = self.add(case=self.c)
        for project, mid in (("project-one", identity), ("project-two", foreign)):
            self.memory.embed(project, mid, {"model": "fixture-v1", "text_sha256": self.memory.row(mid)["digest"], "vector": [1, 0]})
        query = "tenant separation"
        vector = {"model": "fixture-v1", "text_sha256": text_digest(query), "vector": [1, 0]}
        self.assertEqual(self.memory.search("project-one", "fusion-api", query)["items"], [])
        result = self.memory.search("project-one", "fusion-api", query, data=vector)
        self.assertEqual([r["memory_id"] for r in result["items"]], [identity])
        self.assertEqual(result["items"][0]["matched_by"], ["vector"])

    def test_budget_preserves_conditions_and_combined_resume_limit(self):
        self.add()
        memories = self.memory.search("project-one", "fusion-api", "ownership", maximum=1800)
        packet = resume(self.a, maximum=2500, binding={"project": "project-one"}, experiences=memories)
        self.assertLessEqual(len(encode(packet)), 2500)
        if packet["experience_hints"]:
            self.assertEqual(packet["experience_hints"][0]["document"]["conditions"], card()["conditions"])
        with self.assertRaisesRegex(FusionError, "context_budget_exceeded"):
            self.memory.search("project-one", "fusion-api", "ownership", maximum=512)

    def test_python_bm25_fallback_and_no_network_requirement(self):
        identity = self.add()
        self.workspace.db.execute("UPDATE settings SET value='python_bm25' WHERE key='search_engine'")
        result = self.memory.search("project-one", "fusion-api", "ownership")
        self.assertEqual(result["engine"], "python_bm25")
        self.assertEqual(result["items"][0]["memory_id"], identity)

    def test_cli_resume_includes_only_opted_in_experience(self):
        self.add(scope="general")
        plain = self.cli("resume", self.c, "session-c")
        self.assertNotIn("experience_hints", plain)
        enriched = self.cli("resume", self.c, "session-c", "--memory-query", "ownership", "--skill", "fusion-api", "--include-general")
        self.assertEqual(len(enriched["experience_hints"]), 1)
        self.assertEqual(enriched["current"]["status"], "pending")
        self.assertLessEqual(len(encode(enriched)), 6000)

    def test_cli_case_learning_handoff_round_trip(self):
        def execute(*args):
            result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "fusion.py"), *map(str, args)],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        directory = self.root / "cli-case"
        registry = self.root / "cli-registry"
        config = self.root / "cli-config.json"
        plan = self.root / "cli-plan.json"
        document = self.root / "cli-experience.json"
        for path, value in ((config, CONFIG), (plan, [spec()]), (document, card())):
            path.write_text(encode(value), encoding="utf-8")
        execute("workspace-init", "--workspace", registry)
        created = execute("init", "--case", directory, "--input", config)
        flags = ("--workspace", registry, "--case", directory, "--session", "cli-session")
        execute("bind", *flags, "--expect-case", created["case_id"], "--project", "cli-project", "--target", "local-fixture")
        execute("plan", *flags, "--input", plan)
        run = execute("run", *flags, "--check", "one", "--", sys.executable, "-c", "print('offline fixture')")
        execute("review", *flags, "--attempt", run["attempt_id"], "--verdict", "done", "--summary", "Fixture output reviewed")
        note = execute("note", *flags, "--kind", "fact", "--check", "one", "--text", "Fixture method observation",
                       "--evidence", run["evidence_ids"][0])
        candidate = execute("memory-add", *flags, "--input", document, "--note", note["note_id"])
        execute("memory-review", *flags, "--memory", candidate["memory_id"], "--verdict", "accept",
                "--scope", "project", "--redacted", "--validation", "Source and conditions reviewed", "--valid-for", 3600)
        hits = execute("memory-search", *flags, "--skill", "fusion-api", "--query", "ownership")
        self.assertEqual(hits["items"][0]["memory_id"], candidate["memory_id"])
        self.assertEqual(execute("report", *flags)["ledger_status"], "completed")
        execute("handoff", *flags, "--to-session", "cli-next", "--reason", "Continue in next conversation")
        identified = execute("identify", "--case", directory)
        self.assertEqual(identified["binding_hint"]["session"], "cli-next")
        restored = execute("resume", "--workspace", registry, "--case", directory, "--session", "cli-next",
                           "--skill", "fusion-api", "--memory-query", "ownership")
        self.assertEqual(restored["stored_status_counts"], {"done": 1})
        self.assertEqual(len(restored["experience_hints"]), 1)


if __name__ == "__main__":
    unittest.main()

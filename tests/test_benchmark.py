"""No model or target calls: fair scheduling and tool-observation accounting."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_dsh_trace import evaluate
from prepare_benchmark import build_plan, DEFAULT_SUITE, render_plan


class BenchmarkTests(unittest.TestCase):
    def test_direct_and_nested_leaf_execution_use_the_same_counter(self):
        for nested in (False, True):
            rows = [{"type": "tool/call", "data": {"name": "http", "arguments": {}}},
                    {"type": "observed-tool-result", "execution_id": "one", "tool": "http", "child": nested},
                    {"type": "tool/result", "data": {"message": {"content": []}}}]
            result = evaluate(rows, ["http"])
            self.assertEqual(result["observed_tool_calls"], 1)
            self.assertEqual(result["shared_leaf_calls"], 1)
            self.assertEqual(result["status"], "executed_without_delivery")

    def test_wrapper_not_counted_as_an_additional_shared_leaf(self):
        rows = [{"type": "observed-tool-result", "tool": "fusion", "execution_id": "parent"},
                {"type": "observed-tool-result", "tool": "http", "child": True, "execution_id": "child"}]
        self.assertEqual(evaluate(rows, ["http", "http"])["shared_leaf_calls"], 1)
        self.assertIsNone(evaluate(rows)["shared_leaf_calls"])

    def test_replayed_event_deduplicated_but_real_repeated_calls_and_other_sessions_retained(self):
        row = {"type": "observed-tool-result", "tool": "http", "execution_id": "one", "session": "a"}
        result = evaluate([row, dict(row), {**row, "execution_id": "two"}, {**row, "session": "b"}])
        self.assertEqual(result["observed_tool_calls"], 3)
        self.assertEqual(result["observations_without_identity"], 0)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            evaluate([row, {**row, "isError": True}])

    def test_legacy_observations_and_failures_are_not_silently_removed(self):
        row = {"type": "observed-tool-result", "tool": "http", "isError": True}
        result = evaluate([row, row], ["http"])
        self.assertEqual(result["observations_without_identity"], 2)
        self.assertEqual(result["shared_leaf_failed_calls"], 2)

    def test_schedule_has_balanced_conditions_unique_workspaces_and_no_claimed_results(self):
        suite = json.loads(DEFAULT_SUITE.read_text(encoding="utf-8"))
        plan = build_plan(suite, seed=71)
        self.assertEqual(plan, build_plan(suite, seed=71))
        self.assertEqual(len(plan["runs"]), 32)
        self.assertEqual(len({r["workspace"] for r in plan["runs"]}), 32)
        self.assertEqual(len({r["private_observer"] for r in plan["runs"]}), 32)
        for arm in suite["arms"]:
            positions = [i % 4 for i, row in enumerate(plan["runs"]) if row["arm"] == arm["id"]]
            self.assertEqual([positions.count(i) for i in range(4)], [2, 2, 2, 2])
        self.assertEqual(plan["suite"], suite)
        for pair in {r["pair"] for r in plan["runs"]}:
            rows = [r for r in plan["runs"] if r["pair"] == pair]
            self.assertEqual({r["arm"] for r in rows}, {r["id"] for r in suite["arms"]})
            self.assertEqual(len({r["fixture_seed"] for r in rows}), 1)
        self.assertFalse(plan["execution_enabled"])
        self.assertIsNone(plan["approved_budget_cny"])
        self.assertEqual(plan["grades"], [])
        self.assertIn("尚未运行模型", render_plan(plan))

    def test_discovery_is_separate_from_explicit_invocation(self):
        suite = json.loads(DEFAULT_SUITE.read_text(encoding="utf-8"))
        self.assertTrue(all(r["invoke_skill"] is None for r in build_plan(suite, mode="natural")["runs"]))
        rows = build_plan(suite)["runs"]
        self.assertEqual({r["invoke_skill"] for r in rows if r["arm"] == "reverse-skill"}, {"reverse-skill"})

    def test_path_traversal_and_duplicate_task_ids_rejected(self):
        suite = json.loads(DEFAULT_SUITE.read_text(encoding="utf-8"))
        suite["tasks"][0]["id"] = "../other-run"
        with self.assertRaises(ValueError):
            build_plan(suite)
        suite["tasks"][0]["id"] = suite["tasks"][1]["id"]
        with self.assertRaises(ValueError):
            build_plan(suite)


if __name__ == "__main__":
    unittest.main()

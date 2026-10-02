"""Composition must narrow actual methods, preserve host limits and never dispatch."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fusion_composition import compose, component_card
from fusion_store import FusionError, encode, manifest


class CompositionTests(unittest.TestCase):
    def test_every_existing_route_composes_without_loading_unrelated_specialists(self):
        for module in manifest("specialists.json", "modules"):
            for capability in module["execution_routes"]:
                with self.subTest(skill=module["id"], capability=capability):
                    packet = compose(module["id"], capability, host="dsh")
                    self.assertFalse(packet["target_action_executed"])
                    self.assertEqual(packet["method"]["skill_id"], module["id"])
                    self.assertEqual(packet["execution"]["capability_id"], capability)
                    self.assertLessEqual(len(encode(packet)), 5000)
                    self.assertNotIn("upstreams", packet["runtime"])

    def test_phase_and_host_do_not_invent_enforcement_or_health(self):
        execution = compose("fusion-api", "http.request")
        recovery = compose("fusion-api", "http.request", "recover")
        review = compose("fusion-api", "http.request", "review")
        self.assertNotIn("node-review", execution["runtime"]["components"])
        self.assertIn("node-review", review["runtime"]["components"])
        self.assertIn("recovery", recovery["runtime"]["components"])
        text = compose("fusion-api", "http.request", host="text")
        self.assertEqual(text["runtime"]["binding"], "instructions_only_no_hooks")
        self.assertEqual(execution["runtime"]["binding"], "managed_commands_only")
        with self.assertRaises(FusionError):
            compose("fusion-api", "binary.profile")

    def test_components_reference_real_implementations_and_test_files(self):
        for item in manifest("components.json", "components"):
            self.assertEqual(item, component_card(item["id"]))
            for filename in item["implementation"] + item["tests"]:
                self.assertTrue((ROOT / filename).exists(), filename)
            self.assertTrue(item["gap"])

    def test_cli_is_read_only_and_component_query_is_separate(self):
        for args in (("compose", "--skill", "fusion-api", "--capability", "http.request", "--host", "text"),
                     ("catalog", "--component", "recovery")):
            result = subprocess.run([sys.executable, str(ROOT / "scripts/fusion.py"), *args],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)

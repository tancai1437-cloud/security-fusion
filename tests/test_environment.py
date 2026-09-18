"""Offline fixtures for bootstrap state, not a live Kali/DSH integration test."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from fusion_environment import Environment, recipes, routes
from fusion_environment_config import configure, render
from fusion_store import FusionError, encode
from fusion_workspace import file_lock


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fusion-env-test-")
        self.root = Path(self.temporary.name).resolve()
        self.environment = Environment(self.root, "dsh")
        self.fixture = self.root / "fake-server.py"
        self.fixture.write_text("# Offline fixture, never deployed as a real MCP server\n", encoding="utf-8")
        self.connection = {"transport": "stdio", "command": sys.executable, "args": [str(self.fixture)]}
        self.instance = "offline-fixture-host"
        self.tool = "mcp__js-reverse__navigate_page"
        self.raw = self.root / "smoke.json"
        self.raw.write_text(encode({"content": [{"type": "text", "text": "OFFLINE TEST FIXTURE ONLY"}]}), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def receipt(self, provider="js-reverse", capability="browser.observe", name=None):
        name = name or self.tool
        entry = self.environment.data["providers"][provider]
        return {"instance": self.instance, "observed_at": time.time(),
                "connection_sha256": entry["connection_sha256"],
                "tools": [{"name": name, "inputSchema": {"type": "object", "properties": {}}}],
                "checks": [{"capability": capability, "tool": name, "result_file": str(self.raw),
                            "outcome": "pass", "scope": "local_fixture", "fixture_ref": "offline-unit-test",
                            "validation": "Synthetic receipt validates index behavior only, not a real MCP."}]}

    def ready(self):
        self.environment.register("js-reverse", self.connection)
        return self.environment.verify("js-reverse", self.receipt(), self.instance)

    def state(self, instance=None):
        return self.environment.lookup("browser.observe", instance or self.instance)

    def cli(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "fusion_bootstrap.py"), command,
            "--root", str(self.root), "--agent", "dsh", *map(str, args)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout if expected == 0 else result.stderr)

    def test_all_route_providers_have_setup_recipes(self):
        used = {c["provider"] for r in routes().values() for c in r["choices"]}
        self.assertEqual(used, set(recipes()))

    def test_scan_is_read_only_discovery_never_ready(self):
        marker = self.root / "hexstrike_mcp.py"
        marker.write_text("raise RuntimeError('must never execute')", encoding="utf-8")
        with patch("fusion_environment.shutil.which", return_value=None):
            result = self.environment.scan([self.root])
        self.assertIn(str(marker), result["providers"]["hexstrike"]["entrypoint_candidates"])
        self.assertEqual(self.state()["status"], "setup_required")

    def test_agent_machine_path_namespaces_do_not_mix(self):
        self.environment.register("js-reverse", self.connection)
        with self.assertRaisesRegex(FusionError, "different machine"):
            Environment(self.root, "pi")
        with patch("fusion_environment.machine_id", return_value="different-machine"):
            with self.assertRaises(FusionError):
                Environment(self.root, "dsh")
        with self.assertRaisesRegex(FusionError, "outside"):
            Environment(SCRIPTS.parent / "work/env", "dsh")

    def test_configuration_is_not_a_working_capability(self):
        self.environment.register("js-reverse", self.connection)
        result = configure(self.environment, ["js-reverse"])
        self.assertEqual(result["status"], "configuration_generated_not_connected")
        self.assertEqual(self.state()["status"], "setup_required")

    def test_unchanged_registration_preserves_verified_binding(self):
        self.ready()
        result = self.environment.register("js-reverse", self.connection)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(self.state()["status"], "ready")
        self.assertEqual(self.state()["bindings"][0]["target_context"], "must_bind_per_case")

    def test_connection_change_drops_old_verification(self):
        self.ready()
        self.environment.register("js-reverse", dict(self.connection, args=[str(self.fixture), "--changed"]))
        self.assertEqual(self.state()["status"], "setup_required")

    def test_executable_or_config_change_invalidates_readiness(self):
        self.ready()
        self.fixture.write_text("# changed input longer than before\n" * 3, encoding="utf-8")
        self.assertEqual(self.state()["gaps"][0]["status"], "configuration_changed")
        with self.assertRaisesRegex(FusionError, "changed"):
            self.environment.verify("js-reverse", self.receipt(), self.instance)

    def test_host_instance_expiry_and_evidence_tampering(self):
        self.ready()
        self.assertEqual(self.state("new-host")["gaps"][0]["status"], "host_verification_required")
        with patch("fusion_environment.time.time", return_value=time.time() + 3700):
            self.assertEqual(self.state()["gaps"][0]["status"], "expired")
        self.raw.write_text("{}", encoding="utf-8")
        self.assertEqual(self.state()["gaps"][0]["status"], "evidence_invalid")

    def test_schema_discovery_without_actual_check_is_rejected(self):
        self.environment.register("js-reverse", self.connection)
        receipt = self.receipt()
        receipt["checks"] = []
        with self.assertRaisesRegex(FusionError, "smoke"):
            self.environment.verify("js-reverse", receipt, self.instance)

    def test_error_empty_or_non_mcp_result_never_ready(self):
        self.environment.register("js-reverse", self.connection)
        for raw in ({"isError": True, "content": []}, {"error": {"code": -1}}, {"status": "success"}):
            self.raw.write_text(encode(raw), encoding="utf-8")
            with self.assertRaises(FusionError):
                self.environment.verify("js-reverse", self.receipt(), self.instance)
        self.assertEqual(self.state()["status"], "setup_required")

    def test_wrong_route_connection_or_stale_observation_rejected(self):
        self.environment.register("js-reverse", self.connection)
        for field, value in (("instance", "wrong"), ("connection_sha256", "wrong"),
                             ("observed_at", time.time() - 301), ("observed_at", float("nan"))):
            receipt = self.receipt()
            receipt[field] = value
            with self.assertRaises(FusionError):
                self.environment.verify("js-reverse", receipt, self.instance)
        receipt = self.receipt(capability="binary.analysis")
        with self.assertRaisesRegex(FusionError, "selected route"):
            self.environment.verify("js-reverse", receipt, self.instance)

    def test_failed_semantic_review_or_unknown_schema_rejected(self):
        self.environment.register("js-reverse", self.connection)
        receipt = self.receipt()
        receipt["checks"][0]["outcome"] = "fail"
        with self.assertRaises(FusionError):
            self.environment.verify("js-reverse", receipt, self.instance)
        receipt = self.receipt()
        del receipt["tools"][0]["inputSchema"]
        with self.assertRaises(FusionError):
            self.environment.verify("js-reverse", receipt, self.instance)

    def test_batch_verification_is_all_or_nothing(self):
        self.environment.register("js-reverse", self.connection)
        receipt = self.receipt()
        receipt["checks"].append(dict(receipt["checks"][0], capability="binary.analysis"))
        with self.assertRaises(FusionError):
            self.environment.verify("js-reverse", receipt, self.instance)
        self.assertEqual(self.environment.data["providers"]["js-reverse"]["verified"], {})

    def test_native_alias_preserves_real_host_tool_name(self):
        self.environment.register("host", {"transport": "native"})
        receipt = self.receipt("host", "code.inspect", "actual_host_read")
        receipt["tools"][0]["native_alias"] = "read_file"
        self.environment.verify("host", receipt, self.instance)
        binding = self.environment.lookup("code.inspect", self.instance)["bindings"][0]
        self.assertEqual(binding["name"], "actual_host_read")

    def test_plan_reuses_working_provider_and_defaults_to_open_binary_path(self):
        self.ready()
        self.assertEqual(self.environment.plan(["browser.observe"], self.instance)["providers_to_reconcile"], [])
        self.assertEqual(self.environment.plan(["binary.analysis"], self.instance)["providers_to_reconcile"], ["ghidra"])
        self.environment.register("ida", self.connection)
        self.assertEqual(self.environment.plan(["binary.analysis"], self.instance)["providers_to_reconcile"], ["ida"])
        self.environment.invalidate("ida", "License unavailable in this offline fixture")
        self.assertEqual(self.environment.plan(["binary.analysis"], self.instance)["providers_to_reconcile"], ["ghidra"])

    def test_unregistered_blockers_are_recorded_without_faking_install(self):
        self.environment.invalidate("burp", "Interactive dependency unavailable")
        lookup = self.environment.lookup("http.request", self.instance)
        self.assertEqual(lookup["status"], "setup_required")
        self.assertEqual(lookup["gaps"][0]["reason"], "Interactive dependency unavailable")

    def test_detected_ida_is_reused_before_new_ghidra_install(self):
        def locate(name):
            return "/fixture/ida" if name == "ida" else None
        with patch("fusion_environment.shutil.which", side_effect=locate):
            self.environment.scan()
        self.assertEqual(self.environment.plan(["binary.analysis"], self.instance)["providers_to_reconcile"], ["ida"])

    def test_invalidation_removes_ready_and_persists(self):
        self.ready()
        self.environment.invalidate("js-reverse", "Actual connection failed")
        restarted = Environment(self.root, "dsh")
        self.assertEqual(restarted.lookup("browser.observe", self.instance)["status"], "setup_required")

    def test_dsh_generation_uses_env_references_not_values(self):
        connection = dict(self.connection, env_refs={"API_KEY": "FUSION_TEST_SECRET"})
        self.environment.register("js-reverse", connection)
        with patch.dict("os.environ", {"FUSION_TEST_SECRET": "must-never-be-written"}):
            result = configure(self.environment, ["js-reverse"])
        text = Path(result["path"]).read_text(encoding="utf-8")
        self.assertIn('process.env["FUSION_TEST_SECRET"]', text)
        self.assertNotIn("must-never-be-written", text)
        self.assertNotIn("must-never-be-written", self.environment.path.read_text(encoding="utf-8"))

    def test_generated_configs_are_idempotent_backed_up_and_preserve_edits(self):
        self.environment.register("js-reverse", self.connection)
        first = configure(self.environment, ["js-reverse"])
        original = Path(first["path"]).read_text(encoding="utf-8")
        self.assertEqual(configure(self.environment, ["js-reverse"])["status"], "unchanged_not_live_verified")
        self.environment.register("hexstrike", self.connection)
        changed = configure(self.environment, ["js-reverse", "hexstrike"])
        self.assertEqual(Path(changed["backup"]).read_text(encoding="utf-8"), original)
        Path(changed["path"]).write_text("user edit", encoding="utf-8")
        with self.assertRaisesRegex(FusionError, "changed outside"):
            configure(self.environment, ["js-reverse"])
        self.assertEqual(Path(changed["path"]).read_text(), "user edit")

    def test_overlay_change_invalidates_previous_host_receipts(self):
        self.ready()
        configure(self.environment, ["js-reverse"])
        self.assertEqual(self.state()["status"], "setup_required")
        self.ready()
        configure(self.environment, ["js-reverse"])
        self.assertEqual(self.state()["status"], "ready")

    def test_opencode_and_pi_transport_shapes(self):
        _, text = render("opencode", {"js-reverse": self.connection})
        self.assertEqual(json.loads(text)["mcp"]["js-reverse"]["command"], [sys.executable, str(self.fixture)])
        _, text = render("pi", {"js-reverse": self.connection})
        self.assertEqual(json.loads(text)["mcpServers"]["js-reverse"]["args"], [str(self.fixture)])
        with self.assertRaisesRegex(FusionError, "authentication"):
            render("pi", {"js-reverse": dict(self.connection, env_refs={"KEY": "KEY"})})

    def test_missing_executable_and_embedded_credentials_rejected(self):
        for spec in ({"transport": "stdio", "command": "fusion-missing-12345"},
                     {"transport": "streamable-http", "url": "https://user:secret@example.invalid/mcp"},
                     {"transport": "streamable-http", "url": "https://example.invalid/mcp?token=secret"},
                     dict(self.connection, env={"KEY": "secret"}),
                     dict(self.connection, env_refs={"KEY": "not a variable"})):
            with self.assertRaises(FusionError):
                self.environment.register("js-reverse", spec)

    def test_cli_and_catalog_use_verified_index(self):
        connection_file = self.root / "connection.json"
        connection_file.write_text(encode(self.connection), encoding="utf-8")
        self.cli("scan")
        self.cli("register", "--provider", "js-reverse", "--input", connection_file)
        self.environment = Environment(self.root, "dsh")
        receipt_file = self.root / "receipt.json"
        receipt_file.write_text(encode(self.receipt()), encoding="utf-8")
        self.cli("configure", "--provider", "js-reverse")
        self.cli("verify", "--provider", "js-reverse", "--instance", self.instance, "--input", receipt_file)
        result = self.cli("plan", "--instance", self.instance, "--capability", "browser.observe")
        self.assertEqual(result["status"], "ready")
        command = [sys.executable, str(SCRIPTS / "fusion.py"), "catalog", "--capability", "browser.observe",
                   "--environment", str(self.root), "--agent", "dsh", "--instance", self.instance]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["bindings"][0]["name"], self.tool)

    def test_cli_refuses_concurrent_writer(self):
        with file_lock(self.root / ".bootstrap.lock"):
            result = self.cli("scan", expected=2)
        self.assertIn("busy", result["error"])


if __name__ == "__main__":
    unittest.main()

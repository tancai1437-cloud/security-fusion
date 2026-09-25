"""Managed-profile updates preserve user settings and support removal without data deletion."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install_dsh_adapter import BEGIN, FILES, NAME, install


class DshInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "profile"
        self.profile.mkdir()
        (self.profile / "package.json").write_text(json.dumps({"dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base"]}}}))
        self.patch = self.profile / "cordis.patch.yml"
        self.original = "# user settings\n- id: existing-mcp\n  disabled: false\n"
        self.patch.write_text(self.original)

    def run_install(self, **options):
        return install(self.profile, self.root / "private", sys.executable, **options)

    def test_repeat_install_and_remove_preserve_original_settings_and_state(self):
        result = self.run_install()
        self.assertEqual(result["status"], "configured_requires_restart")
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(Path(result["backup"]).read_text(), self.original)
        self.assertTrue(all((self.profile / NAME / name).is_file() for name in FILES))
        self.run_install()
        self.assertEqual(self.patch.read_text().count(BEGIN), 1)
        (self.root / "private").mkdir()
        (self.root / "private" / "evidence").write_text("keep")
        self.run_install(uninstall=True)
        self.assertEqual(self.patch.read_text().strip(), self.original.strip())
        self.assertEqual((self.root / "private" / "evidence").read_text(), "keep")

    def test_preview_and_rejected_formats_do_not_modify_files(self):
        self.run_install(dry_run=True)
        self.assertFalse((self.profile / NAME).exists())
        for invalid in ["plugins:\n  other: true\n", "- id: security-fusion-host\n  name: ./user-code.mjs\n", BEGIN + "\n- id: unfinished\n"]:
            self.patch.write_text(invalid)
            with self.assertRaises(ValueError):
                self.run_install()
            self.assertEqual(self.patch.read_text(), invalid)
            self.assertFalse((self.profile / NAME).exists())

    def test_json_patch_remains_valid_and_retains_existing_entry(self):
        original = [{"id": "existing", "config": {"enabled": True}}]
        self.patch.write_text(json.dumps(original))
        self.run_install()
        self.run_install()
        self.assertEqual(len(json.loads(self.patch.read_text())), 2)
        self.run_install(uninstall=True)
        self.assertEqual(json.loads(self.patch.read_text()), original)

    def test_managed_upgrade_preserves_extra_config_and_empty_removal_is_valid(self):
        self.patch.write_text("")
        self.run_install()
        text = self.patch.read_text()
        line = next(x for x in text.splitlines() if x.startswith('- {'))
        entry = json.loads(line[2:])
        entry['insert'][0]['config']['boundTools'] = {'mcp__fixture__read': 'fixed-target'}
        self.patch.write_text(text.replace(line, '- ' + json.dumps(entry)))
        self.run_install()
        self.assertIn('fixed-target', self.patch.read_text())
        self.run_install(uninstall=True)
        self.assertEqual(json.loads(self.patch.read_text()), [])

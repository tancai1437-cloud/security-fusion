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
        entry['insert'][0]['config']['requireMission'] = False
        self.patch.write_text(text.replace(line, '- ' + json.dumps(entry)))
        self.run_install()
        self.assertIn('fixed-target', self.patch.read_text())
        upgraded = json.loads(next(x[2:] for x in self.patch.read_text().splitlines() if x.startswith('- {')))
        self.assertIs(upgraded['insert'][0]['config']['requireMission'], False)
        self.run_install(uninstall=True)
        self.assertEqual(json.loads(self.patch.read_text()), [])

    def test_purge_preview_rejects_wrong_sdk_without_writing_then_migrates_only_owned_row(self):
        runtime = self.root / 'runtime'
        runtime.mkdir()
        (runtime / 'package.json').write_text('{}')
        for name in ('dsh-tools', 'dsh-session', 'dsh-llm', 'dsh-web-app'):
            package = runtime / 'node_modules/@deepseek-ai' / name
            package.mkdir(parents=True)
            (package / 'package.json').write_text(json.dumps({'version': '0.1.2-rc.1'}))
        with self.assertRaisesRegex(ValueError, '0.2.0-rc.2'):
            self.run_install(purge=True, runtime=runtime, dsh_home=self.root, dry_run=True)
        self.assertEqual(self.patch.read_text(), self.original)
        self.assertFalse((self.profile / NAME).exists())
        for package in (runtime / 'node_modules/@deepseek-ai').iterdir():
            (package / 'package.json').write_text(json.dumps({'version': '0.2.0-rc.2'}))
        standard = runtime / 'node_modules/@deepseek-ai/dsh-web-app/presets'
        standard.mkdir()
        (standard / 'standard.patch.yml').write_text('[]')
        self.run_install()  # legacy adapter installed before purge appeared
        purge = self.profile / 'node_modules/dsh-purge'
        (purge / 'lib/redteam').mkdir(parents=True)
        (purge / 'lib/redteam/tools.js').write_text('// fixture only, never executed')
        (purge / 'package.json').write_text(json.dumps({'name': 'dsh-purge', 'version': '1.1.47', 'dshTarget': '0.2.0-rc.2'}))
        preview = self.run_install(purge=True, runtime=runtime, dsh_home=self.root, dry_run=True)
        self.assertFalse(preview['runtime_verified'])
        with self.assertRaisesRegex(ValueError, '--purge'):
            self.run_install()
        self.run_install(purge=True, runtime=runtime, dsh_home=self.root)
        self.run_install()  # ordinary upgrade preserves preset scoping
        content = self.patch.read_text()
        self.assertIn(self.original.strip(), content)
        self.assertIn('dsh-purge-preset.mjs', content)
        self.assertEqual(content.count(BEGIN), 1)
        self.run_install(uninstall=True)
        self.assertEqual(self.patch.read_text().strip(), self.original.strip())

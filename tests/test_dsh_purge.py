"""Purge coexistence contracts; upstream/SDK tests are opt-in and explicitly skip in offline CI."""
from pathlib import Path
import shutil
import subprocess
import unittest


class DshPurgeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_coexistence_contracts(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', '--test', 'tests/dsh-purge.test.mjs'], cwd=root,
                                capture_output=True, text=True, encoding='utf-8', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

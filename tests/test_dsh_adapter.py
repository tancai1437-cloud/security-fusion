"""Run the dependency-free host bridge tests when Node is available."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import contextlib
import io


class DshAdapterTests(unittest.TestCase):
    def test_note_error_explains_valid_kinds_without_source_inspection(self):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / 'scripts'))
        from fusion import parser
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            parser().parse_args(['note', '--case', 'x', '--workspace', 'y', '--session', 'z',
                                 '--kind', 'summary', '--text', 'observed input from live evaluation'])
        self.assertIn('invalid choice', output.getvalue())
        self.assertIn('decision', output.getvalue())
        self.assertIn('negative', output.getvalue())

    @unittest.skipUnless(shutil.which('node'), 'Optional DSH adapter requires Node')
    def test_host_bridge_contracts(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', '--test', 'tests/dsh-runtime.test.mjs'], cwd=root,
            env=dict(os.environ, FUSION_TEST_PYTHON=sys.executable), capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

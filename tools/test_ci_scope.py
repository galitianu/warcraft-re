"""Missing artifacts cannot turn a reduced, explicit CI scope into a pass."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from summarize_ci import summarize


class ScopeTests(unittest.TestCase):
    def test_missing_active_artifacts_fail_and_windows_is_explicitly_disabled(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            self.assertEqual(summarize(root / 'missing', root / 'report'), 1)
            report = json.loads((root / 'report/scope.json').read_text())
            self.assertEqual(set(report['errors']), {'mac-arm-release', 'mac-arm-debug',
                                                    'linux-gcc-release', 'linux-clang-debug'})
            self.assertEqual(report['disabled_configurations'], ['windows-msvc-release'])
            self.assertIn('DISABLED / UNOBSERVED', (root / 'report/summary.md').read_text())

    def test_historical_five_configuration_mode_requires_windows_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            self.assertEqual(summarize(root / 'missing', root / 'report', include_windows=True), 1)
            report = json.loads((root / 'report/scope.json').read_text())
            self.assertIn('windows-msvc-release', report['errors'])
            self.assertEqual(report['disabled_configurations'], [])


if __name__ == '__main__':
    unittest.main()

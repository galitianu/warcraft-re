"""Scenario v2 and the MOV-0013 gate: rejections, v1 equivalence, downloaded regrade.

Uses the built runner (WC3TEST_RUNNER), generator (ORACLE_CODEGEN) and the
wc3states tool beside the runner. Tampering happens only in temporary copies.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from trace_contract import ROOT, load, write_json

EXT = '.exe' if os.name == 'nt' else ''
RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' / f'wc3test{EXT}'))
CODEGEN = Path(os.environ.get('ORACLE_CODEGEN', ROOT / 'build' / f'oracle_codegen{EXT}'))
STATES = RUNNER.parent / f'wc3states{EXT}'
V2 = (ROOT / 'scenarios/MOV-0013/MOV-0013-c.yaml').read_text()
CASES = [f'MOV-{n:04d}' for n in range(1, 11)]


def runner(*args):
    return subprocess.run([str(RUNNER), *map(str, args)], cwd=ROOT, capture_output=True,
                          text=True, timeout=120)


class ScenarioV2Tests(unittest.TestCase):
    def test_invalid_v2_descriptions_and_runs_fail_before_any_output(self):
        two_units = V2.replace('    facing: 0\n', '    facing: 0\n  - name: u1\n    type: hfoo\n'
                               '    position: [1, 1]\n    facing: 0\n', 1)
        cases = {
            'v1-start': (V2.replace('version: 2', 'version: 1'), (), "unsupported field 'start' in observe"),
            'v1-clock': (V2.replace('version: 2', 'version: 1').replace('  start: 0.02\n', ''), (),
                         "unsupported field 'state_clock' in observe"),
            'clock': (V2.replace('state_clock: 10', 'state_clock: 5'), (), 'state_clock must be in [10, 10]'),
            'start': (V2.replace('start: 0.02', 'start: 1.5'), (), 'start must be in [0, 1] seconds'),
            'rounding': (V2.replace('start: 0.02', 'start: 0.0000005'), (), 'whole number of microseconds'),
            'units': (two_units, (), 'declare exactly one'),
            'outlast': (V2.replace('callbacks: 1000', 'callbacks: 9990'), (), 'must outlast'),
            'period': (V2.replace('period: 0.001', 'period: 0.005'), (), 'captured 0.001/0.01/0.02/0.025/0.05 s'),
            'model': (V2, ('--model', 'v3'), 'defined for --model v4 --phase after only'),
            'phase': (V2, ('--phase', 'before'), 'defined for --model v4 --phase after only'),
            'alone': (V2, ('--scenario', 'scenarios/MOV-0001.yaml'), 'must be the only scenario'),
        }
        with tempfile.TemporaryDirectory() as temp:
            for name, (text, extra, message) in cases.items():
                with self.subTest(name):
                    path = Path(temp) / f'{name}.yaml'
                    path.write_text(text, newline='\n')
                    out = Path(temp) / f'out-{name}'
                    result = runner('--model', 'v4', '--scenario', path, *extra, '--out', out)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(out.exists(), 'invalid input produced output')

    def test_v1_scenarios_as_version_2_keep_every_v4_observation(self):
        # The scheduled rule (H0) is the v1 v4 rule wherever no start or STATE is declared.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(runner(*[a for c in CASES for a in ('--scenario', f'scenarios/{c}.yaml')],
                                    '--model', 'v4', '--out', root / 'v1').returncode, 0)
            for case in CASES:
                with self.subTest(case):
                    path = root / f'{case}.yaml'
                    path.write_text((ROOT / f'scenarios/{case}.yaml').read_text()
                                    .replace('\nversion: 1\n', '\nversion: 2\n'), newline='\n')
                    result = runner('--scenario', path, '--model', 'v4', '--out', root / case)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    rows = lambda trace: [{k: v for k, v in r.items() if k != 'seq'} for r in trace['records']
                                          if r['kind'] in ('SAMPLE', 'ACTION')]
                    v1, v2 = load(root / 'v1' / f'{case}.json'), load(root / case / f'{case}.json')
                    for record in rows(v1) + rows(v2):
                        record['time'].pop('state_us', None)
                    self.assertEqual(rows(v1), rows(v2))
                    self.assertEqual(v2['identity']['build']['observation_phase'], 'scheduled-sampler-time')


class Mov0013GateTests(unittest.TestCase):
    def test_gate_passes_only_with_the_reviewed_differences_and_regrades_downloads(self):
        from run_mov0013 import run, KNOWN
        from summarize_ci import verify_mov0013
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run(RUNNER, STATES, CODEGEN, root / 'mov-0013', root / 'reports'), 0)
            result = dict(mov0013_required=True, mov0013=dict(status='PASS'))
            self.assertEqual(verify_mov0013(root, result)['cases'], 4)
            for missing in ({}, dict(mov0013_required=False, mov0013=dict(status='PASS')),
                            dict(mov0013_required=True, mov0013=dict(status='FAIL'))):
                with self.assertRaisesRegex(ValueError, 'required MOV-0013 gate'):
                    verify_mov0013(root, missing)
            self.assertIsNone(verify_mov0013(root, {}, legacy=True))
            # A changed reviewed list is a failing gate, not a new expectation.
            with mock.patch.dict(KNOWN, {'MOV-0013-a': dict(KNOWN['MOV-0013-a'], state=[15])}):
                self.assertEqual(run(RUNNER, STATES, CODEGEN, root / 'again', root / 'again-reports'), 1)
            # A forged trace cannot keep a PASS report.
            path = root / 'mov-0013/traces/MOV-0013-d/MOV-0013.json'
            trace = load(path)
            next(r for r in trace['records'] if r['kind'] == 'SAMPLE')['values']['x'] = '1.000000'
            write_json(path, trace, compact_records=True)
            with self.assertRaisesRegex(ValueError, 'does not reproduce'):
                verify_mov0013(root, result)
            shutil.rmtree(root / 'mov-0013/traces')
            with self.assertRaises(OSError):
                verify_mov0013(root, result)


if __name__ == '__main__':
    unittest.main()

"""Scenario v2 and the MOV-0013/0014 gates: rejections, v1 equivalence, downloaded regrade.

Uses the built runner (WC3TEST_RUNNER), generator (ORACLE_CODEGEN) and the
wc3states tool beside the runner. Tampering happens only in temporary copies.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
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


class ExperimentGateTests(unittest.TestCase):
    def test_gates_pass_only_with_the_reviewed_differences_and_regrade_downloads(self):
        from run_mov0013 import EXPERIMENTS, KNOWN, labels, run
        from summarize_ci import verify_experiment
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for experiment in EXPERIMENTS:
                with self.subTest(experiment):
                    name, key = experiment.lower(), experiment.lower().replace('-', '')
                    self.assertEqual(run(RUNNER, STATES, CODEGEN, root / name, root / 'reports',
                                         experiment=experiment), 0)
                    result = {f'{key}_required': True, key: dict(status='PASS')}
                    self.assertEqual(verify_experiment(root, result, experiment)['cases'], len(labels(experiment)))
                    for missing in ({}, {f'{key}_required': False, key: dict(status='PASS')},
                                    {f'{key}_required': True, key: dict(status='FAIL')}):
                        with self.assertRaisesRegex(ValueError, f'required {experiment} gate'):
                            verify_experiment(root, missing, experiment)
                    self.assertIsNone(verify_experiment(root, {}, experiment, legacy=True))
            # A changed reviewed list is a failing gate, not a new expectation.
            for label, changed in (('MOV-0013-a', dict(state=[15])), ('MOV-0014-b', dict(state=[15, 20])),
                                   ('MOV-0014-c', dict(clock=(1, None)))):
                with self.subTest(label), mock.patch.dict(KNOWN, {label: dict(KNOWN[label], **changed)}):
                    experiment = label[:8]
                    self.assertEqual(run(RUNNER, STATES, CODEGEN, root / 'again', root / 'again-reports',
                                         experiment=experiment), 1)
            # A forged trace cannot keep a PASS report: changed state fails the regrade,
            # and a clock that disagrees with its samples fails the trace contract.
            result = dict(mov0014_required=True, mov0014=dict(status='PASS'))
            path = root / 'mov-0014/traces/MOV-0014-c/MOV-0014.json'
            original = load(path)
            for kind, forge, message in (('SAMPLE', lambda r: r['values'].update(x='1.000000'), 'does not reproduce'),
                                         ('TICK', lambda r: r['time'].update(reported='0.000000'), 'time differs')):
                trace = load(path)
                forge(next(r for r in trace['records'] if r['kind'] == kind))
                write_json(path, trace, compact_records=True)
                with self.subTest(kind), self.assertRaisesRegex(ValueError, message):
                    verify_experiment(root, result, 'MOV-0014')
                write_json(path, original, compact_records=True)
            shutil.rmtree(root / 'mov-0014/traces')
            with self.assertRaises(OSError):
                verify_experiment(root, result, 'MOV-0014')


class Mov0014PredictionTests(unittest.TestCase):
    def test_committed_predictions_regenerate_byte_for_byte(self):
        # The pre-registration (docs/mov-0014.md) must stay reproducible from the tools.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'predictions.json'
            result = subprocess.run([sys.executable, str(ROOT / 'tools/predict_mov0014.py'), '--runner', str(RUNNER),
                                     '--states', str(STATES), '--out', str(out)],
                                    capture_output=True, text=True, timeout=600)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(out.read_bytes(), (ROOT / 'results/mov-0014/predictions.json').read_bytes())


if __name__ == '__main__':
    unittest.main()

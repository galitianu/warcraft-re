"""Negative controls use temporary copies of real C++ output, never oracle edits."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compare_traces import actions, compare_suite, samples
from regression import assess
from run_ci import execute, repeatability
from trace_contract import BUILD, ROOT, SCENARIOS, counts, load, write_json

RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' /
              ('wc3test.exe' if os.name == 'nt' else 'wc3test')))
FIXTURES = ROOT / 'oracle/canonical' / BUILD


class RegressionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.base = cls.root / 'baseline'
        subprocess.run([str(RUNNER), *SCENARIOS, '--out', str(cls.base), '--model', 'v2'],
                       cwd=ROOT, check=True, capture_output=True, timeout=60)
        cls.baseline = compare_suite(FIXTURES, cls.base)

    def changed(self, case, mutation):
        # Supply the rest of the complete suite independently of the changed case.
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            for path in self.base.glob('MOV-*.json'):
                trace = load(path)
                if path.stem == case:
                    mutation(trace)
                write_json(dest / path.name, trace)
            suite = compare_suite(FIXTURES, dest)
            return suite, assess(self.baseline, suite)

    def test_complete_known_incompatibility_is_not_regression(self):
        report = assess(self.baseline, self.baseline)
        self.assertEqual((report['regression_verdict'], report['compatibility_passes']), ('PASS', 1))
        self.assertEqual(report['changes'], [])
        # Current primary independently requires ten passes, under the same policy.
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(RUNNER), *SCENARIOS, '--out', temp, '--model', 'v4'], cwd=ROOT, check=True,
                           capture_output=True, timeout=60)
            suite = compare_suite(FIXTURES, Path(temp))
            report = assess(load(ROOT / 'results/footman-v4/comparison.json'), suite)
            self.assertEqual((report['regression_verdict'], report['compatibility_passes']), ('PASS', 10))

    def test_stationary_regression(self):
        suite, report = self.changed('MOV-0001', lambda t: samples(t)[1]['values'].update(x='1'))
        self.assertEqual(suite['cases'][0]['status'], 'FAIL')
        self.assertEqual(report['regression_verdict'], 'FAIL')
        self.assertTrue(any(c['metric'] == 'failures' for c in report['regressions']))

    def test_worse_error_inside_already_failing_case(self):
        _, report = self.changed('MOV-0002', lambda t: samples(t)[-2]['values'].update(y='-1000'))
        self.assertEqual(report['regression_verdict'], 'FAIL')
        # Even with the same overall 1/10 count and same first Y failure.
        self.assertEqual(report['compatibility_passes'], 1)
        self.assertTrue(any(c['metric'] == 'max_abs_delta' for c in report['regressions']))
        self.assertTrue(any(c['metric'] == 'final_delta_by_unit/u0' for c in report['regressions']))

    def test_earlier_failure_is_protected(self):
        def earlier(trace):
            next(r for r in samples(trace) if r['callback'] == 1)['values']['x'] = '100'
        _, report = self.changed('MOV-0003', earlier)
        self.assertTrue(any(c['metric'] == 'first_location' for c in report['regressions']))

    def test_command_and_equal_time_action_order_changes(self):
        def command(trace):
            actions(trace)[0].update(command='stop', target=None)
        _, report = self.changed('MOV-0002', command)
        self.assertTrue(any(c['metric'] == 'structural_differences' for c in report['regressions']))
        def reorder(trace):
            action = actions(trace)[0]
            # An extra action at the same callback cannot be hidden by grouping
            # actions separately from sample/observable order.
            extra = copy.deepcopy(action)
            extra['unit'] = 'u1'
            trace['records'].insert(trace['records'].index(action), extra)
            for seq, row in enumerate(trace['records']):
                row['seq'] = seq
            trace['completion'] = counts(trace['records'])
        _, report = self.changed('MOV-0002', reorder)
        self.assertTrue(any(c['metric'] == 'structural_differences' for c in report['regressions']))

    def test_improvement_is_a_completed_valid_result(self):
        ref = load(FIXTURES / 'MOV-0002-r2.json')
        def improve(trace):
            for row, expected in zip(samples(trace), samples(ref)):
                row['values'] = copy.deepcopy(expected['values'])
        suite, report = self.changed('MOV-0002', improve)
        self.assertEqual(suite['cases'][1]['status'], 'PASS')
        self.assertEqual(report['regression_verdict'], 'PASS')
        self.assertTrue(report['improvements'])
        self.assertEqual(report['compatibility_passes'], 2)

    def test_legacy_clock_and_action_diagnostics_remain_visible(self):
        case4 = self.baseline['cases'][3]['properties']['t']
        self.assertEqual((case4['failures'], case4['first_divergence']['callback']), (53, 503))
        first = self.baseline['cases'][1]['properties']['y']['first_divergence']
        self.assertEqual((first['callback'], first['delta']), (1, -0.014648))
        self.assertEqual(self.baseline['cases'][8]['properties']['x']['first_divergence']['callback'], 7)
        for index in (5, 6):
            self.assertGreater(self.baseline['cases'][index]['action_properties']['target_x']['failures'], 0)
            self.assertGreater(self.baseline['cases'][index]['action_properties']['target_y']['failures'], 0)

    def test_invalid_overflow_missing_truncated_inputs_are_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            command = [sys.executable, str(ROOT / 'tools/compare_traces.py'), '--actual', temp,
                       '--case', 'MOV-0001', '--json', str(dest / 'report.json')]
            path = dest / 'MOV-0001.json'
            def truncated(t): t['records'].pop()
            mutations = [lambda t: t.update(version=99),
                         lambda t: t['completion'].update(samples=10**100),
                         lambda t: samples(t)[1]['values'].update(x='1e999'), truncated]
            for mutation in mutations:
                trace = load(self.base / path.name)
                mutation(trace)
                write_json(path, trace)
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((dest / 'report.json').exists())
            path.unlink()
            self.assertEqual(subprocess.run(command, capture_output=True, timeout=30).returncode, 2)

    def test_comparator_exit_one_is_evaluated_and_exit_two_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            baseline = dest / 'baseline.json'
            write_json(baseline, self.baseline)
            comparison = dest / 'comparison.json'
            code = execute([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', self.base,
                            '--json', comparison], dest, 'known-failure', accepted=(0, 1))
            self.assertEqual(code, 1)
            policy = [sys.executable, ROOT / 'tools/regression.py', '--baseline', baseline,
                      '--actual', comparison, '--out', dest / 'assessment']
            self.assertEqual(execute(policy, dest, 'policy'), 0)
            with self.assertRaisesRegex(ValueError, 'exit 2'):
                execute([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', dest / 'missing'],
                        dest, 'invalid', accepted=(0, 1))
            bad = copy.deepcopy(self.baseline)
            bad['cases'][0]['properties'].pop('x')
            write_json(comparison, bad)
            self.assertEqual(subprocess.run([str(v) for v in policy], capture_output=True, timeout=30).returncode, 2)

    def test_nonzero_runner_timeout_and_missing_artifact_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp)
            with self.assertRaisesRegex(ValueError, 'exit 7'):
                execute([sys.executable, '-c', 'raise SystemExit(7)'], logs, 'runner-failure')
            with self.assertRaisesRegex(ValueError, 'timed out'):
                execute([sys.executable, '-c', 'import time; time.sleep(5)'], logs, 'timeout', timeout=0.1)
            with self.assertRaisesRegex(ValueError, '31 required'):
                repeatability(self.base, logs)
            self.assertEqual(load(logs / 'runner-failure.json')['exit_code'], 7)
            self.assertEqual(load(logs / 'timeout.json')['error'], 'timeout')


if __name__ == '__main__':
    unittest.main()

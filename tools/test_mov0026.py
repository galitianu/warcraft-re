"""Negative controls for preregistered stop-transition decisions."""
import copy
import unittest

from predict_mov0026 import transition
from trace_contract import ROOT, load


class StopTransitionTests(unittest.TestCase):
    def fixture(self, variant):
        return load(ROOT / f'results/mov-0026/predicted/MOV-0026-{variant}.json')

    def post(self, trace, callback):
        return next(r['values'] for r in trace['records'] if r['kind'] == 'SAMPLE'
                    and r['unit'] == 'u0' and r['callback'] == callback)

    def test_blocked_stop_distinguishes_position_and_grid(self):
        trace = self.fixture('b')
        result = transition(trace, 'MOV-0026-b')
        self.assertEqual(result['setup'], 'PASS')
        self.assertEqual(result['hypotheses']['stop_in_place'], 'SURVIVES')
        self.assertEqual(result['hypotheses']['blocked_grid'], 'REFUTED')
        # A synthetic cell-center displacement refutes S and supports B/G.
        row = self.post(trace, 97)
        row.update(x='-48', y='16')
        result = transition(trace, 'MOV-0026-b')
        self.assertEqual(result['grid_center_error'], [0, 0])
        self.assertEqual(result['hypotheses'], dict(stop_in_place='REFUTED',
                         blocked_grid='SURVIVES', unconditional_grid='SURVIVES'))
        row['order'] = '851986'
        self.assertEqual(set(transition(trace, 'MOV-0026-b')['hypotheses'].values()), {'REFUTED'})

    def test_moving_control_distinguishes_conditional_rule(self):
        trace = self.fixture('c')
        result = transition(trace, 'MOV-0026-c')
        self.assertEqual(result['setup'], 'PASS')
        self.assertEqual(result['hypotheses']['blocked_grid'], 'SURVIVES')
        self.post(trace, 81).update(x='-80', y='16')
        result = transition(trace, 'MOV-0026-c')
        self.assertEqual(result['hypotheses']['blocked_grid'], 'REFUTED')
        self.assertEqual(result['hypotheses']['unconditional_grid'], 'SURVIVES')

    def test_invalid_setup_is_not_a_rule_pass(self):
        original = self.fixture('a')
        for callback, changes in ((0, dict(x='-499')), (88, dict(x='-20')),
                                  (89, dict(order='0'))):
            trace = copy.deepcopy(original)
            self.post(trace, callback).update(changes)
            result = transition(trace, 'MOV-0026-a')
            self.assertEqual(result['setup'], 'INCONCLUSIVE')
            self.assertEqual(set(result['hypotheses'].values()), {'INCONCLUSIVE'})

    def test_grid_phase_is_not_translation_invariant(self):
        trace = self.fixture('d')
        self.post(trace, 97).update(x='-32', y='32')
        result = transition(trace, 'MOV-0026-d')
        self.assertEqual(result['grid_center_error'], [16, 16])
        self.assertEqual(result['hypotheses']['blocked_grid'], 'REFUTED')

class StopEvidenceTests(unittest.TestCase):
    def test_frozen_verdicts_cannot_be_hidden(self):
        from compare_traces import compare
        from run_mov0026 import LABELS, assess
        from trace_contract import BUILD
        reviewed = load(ROOT / 'results/mov-0026/reviewed.json')
        for label in LABELS:
            reference = load(ROOT / f'oracle/canonical-generated/{BUILD}/{label}.json')
            actual = load(ROOT / f'results/mov-0026/predicted/{label}.json')
            comparison = compare(reference, actual)
            self.assertTrue(assess(comparison, reviewed['cases'][label]['comparison']))
            changed = copy.deepcopy(comparison)
            changed['status'] = 'FAIL' if comparison['status'] == 'PASS' else 'PASS'
            self.assertFalse(assess(changed, reviewed['cases'][label]['comparison']))
            changed = copy.deepcopy(actual)
            row = next(r for r in changed['records'] if r['kind'] == 'SAMPLE'
                       and r['unit'] == 'u0' and r['callback'] == 100)
            row['values']['x'] = str(float(row['values']['x']) + 20)
            self.assertFalse(assess(compare(reference, changed), reviewed['cases'][label]['comparison']))

    def test_finite_gate_and_artifact_regrade(self):
        import os
        from pathlib import Path
        import tempfile
        from run_mov0026 import LABELS, run, verify_download
        from trace_contract import write_json
        ext = '.exe' if os.name == 'nt' else ''
        runner = Path(os.environ.get('WC3TEST_RUNNER', ROOT / f'build/wc3test{ext}'))
        codegen = Path(os.environ.get('ORACLE_CODEGEN', ROOT / f'build/oracle_codegen{ext}'))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(run(runner, codegen, root / 'mov-0026', root / 'reports'), 0)
            report = load(root / 'reports/mov0026.json')
            self.assertEqual([c['map_revision'] for c in report['cases']], list(LABELS))
            result = dict(mov0026_required=True, mov0026=dict(status='PASS'))
            self.assertEqual(verify_download(root, result)['cases'], 4)
            for missing in ({}, dict(mov0026_required=False, mov0026=dict(status='PASS'))):
                with self.assertRaisesRegex(ValueError, 'required MOV-0026'):
                    verify_download(root, missing)
            for kind in ('missing', 'verdict', 'transition', 'summary'):
                changed = copy.deepcopy(report)
                if kind == 'missing':
                    changed['cases'].pop()
                elif kind == 'verdict':
                    changed['cases'][0]['comparison']['status'] = 'INVENTED'
                elif kind == 'summary':
                    changed['hypotheses']['blocked_grid'] = 'INVENTED'
                else:
                    changed['cases'][0]['transition']['delta_xy'] = [0, 0]
                    changed['cases'][0]['transition']['setup'] = 'INVENTED'
                write_json(root / 'reports/mov0026.json', changed)
                with self.assertRaises(ValueError):
                    verify_download(root, result)


if __name__ == '__main__':
    unittest.main()

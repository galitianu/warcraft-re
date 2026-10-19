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


if __name__ == '__main__':
    unittest.main()

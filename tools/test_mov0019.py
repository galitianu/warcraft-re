"""MOV-0019 pre-registration: committed scenarios and the adopted model's predictions.

The predictions were made by footman-v4 as committed in d6da91c, which the post-hoc
refit has since changed, so they are checked against committed evidence rather than
rerun: the scenario bytes regenerate, and the adopted outcome of every variant is the
P3 description of the pre-refit C++ trace that each capture bundle produced
(results/mov-0019/before/description.json).
"""
import json
import unittest

from predict_mov0019 import ADOPTED, VARIANTS, variant_text
from trace_contract import ROOT, load


def p3(d):
    """predict_mov0019.summary's description, from analyze_mov0018's."""
    out = dict(final=[round(d['final']['x'], 1), round(d['final']['y'], 1), d['final']['order']])
    if d['ordered']:
        out.update(side=d['passes_other_on'], arrival=d['arrival_callback'],
                   waits=[[w['first'], w['last']] for w in d['waits']],
                   deviation=round(d['largest_sideways_deviation']['units'], 1))
    return out


class PreRegistrationTests(unittest.TestCase):
    def test_scenarios_and_adopted_predictions_match_the_pre_refit_traces(self):
        predictions = load(ROOT / 'results/mov-0019/predictions.json')
        before = load(ROOT / 'results/mov-0019/before/description.json')
        comparison = load(ROOT / 'results/mov-0019/before/comparison.json')
        self.assertEqual(list(predictions['variants']), list(VARIANTS))
        keys = predictions['candidate_keys']
        self.assertEqual(predictions['candidates'][predictions['adopted_index']], [ADOPTED[k] for k in keys])
        for label, row in predictions['variants'].items():
            with self.subTest(label):
                path = ROOT / 'scenarios/MOV-0019' / f'{label}.yaml'
                self.assertEqual(path.read_bytes(), variant_text(label).encode())
                cpp = {unit: p3(d) for unit, d in before[label]['cpp'].items()}
                self.assertEqual(json.loads(json.dumps(cpp)), row['outcomes'][row['adopted_outcome']])
                self.assertEqual(len(row['candidate_outcome']), len(predictions['candidates']))
                self.assertEqual(comparison['cases'][label]['cpp']['model'], 'footman-v4')


if __name__ == '__main__':
    unittest.main()

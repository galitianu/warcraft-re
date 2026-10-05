"""MOV-0021 pre-registration: committed scenarios and each hypothesis's waiting unit.

The model's predictions are not rerun: the model may be refitted after capture, and
predictions.json records the one that made them.
"""
import unittest

from predict_mov0021 import VARIANTS, hypotheses, variant_text
from trace_contract import ROOT, load


class PreRegistrationTests(unittest.TestCase):
    def test_scenarios_and_hypotheses_regenerate(self):
        predictions = load(ROOT / 'results/mov-0021/predictions.json')
        self.assertEqual(list(predictions['variants']), list(VARIANTS))
        for label, row in predictions['variants'].items():
            with self.subTest(label):
                path = ROOT / 'scenarios/MOV-0021' / f'{label}.yaml'
                self.assertEqual(path.read_bytes(), variant_text(label).encode())
                self.assertEqual(row['hypotheses'], hypotheses(label))
        # The design separates every pair of hypotheses in some variant.
        rows = [hypotheses(label) for label in VARIANTS]
        for a, b in (('heading', 'rotation'), ('heading', 'line'), ('rotation', 'line')):
            self.assertTrue(any(h[a] != h[b] for h in rows), (a, b))


if __name__ == '__main__':
    unittest.main()

"""MOV-0022 pre-registration: committed scenarios and predicted traces.

The model is not rerun: it may change after capture, and predictions.json records the
build that made each prediction.
"""
import unittest

from predict_mov0022 import VARIANTS, variant_text
from trace_contract import ROOT, load, sha256


class PreRegistrationTests(unittest.TestCase):
    def test_scenarios_and_predicted_traces(self):
        predictions = load(ROOT / 'results/mov-0022/predictions.json')
        self.assertEqual(list(predictions['variants']), list(VARIANTS))
        for label, row in predictions['variants'].items():
            with self.subTest(label):
                path = ROOT / 'scenarios/MOV-0022' / f'{label}.yaml'
                self.assertEqual(path.read_bytes(), variant_text(label).encode())
                self.assertEqual(sha256(ROOT / row['trace']), row['sha256'])
                self.assertEqual(load(ROOT / row['trace'])['scenario']['map_revision'], label)


if __name__ == '__main__':
    unittest.main()

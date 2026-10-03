"""MOV-0019 pre-registration: committed scenarios and the adopted model's predictions.

The full candidate grid takes minutes, so only the adopted set is rerun here. Uses the
built wc3pathing beside the runner (WC3TEST_RUNNER).
"""
import json
import os
from pathlib import Path
import tempfile
import unittest

from predict_mov0019 import ADOPTED, FIXED, VARIANTS, run_sets, summary, targets_of, variant_text
from trace_contract import ROOT, load

EXT = '.exe' if os.name == 'nt' else ''
RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' / f'wc3test{EXT}'))
PATHING = RUNNER.parent / f'wc3pathing{EXT}'


class PreRegistrationTests(unittest.TestCase):
    def test_scenarios_and_adopted_predictions_regenerate(self):
        predictions = load(ROOT / 'results/mov-0019/predictions.json')
        self.assertEqual(list(predictions['variants']), list(VARIANTS))
        keys = predictions['candidate_keys']
        self.assertEqual(predictions['candidates'][predictions['adopted_index']], [ADOPTED[k] for k in keys])
        adopted = dict(FIXED, **ADOPTED)
        for label, row in predictions['variants'].items():
            with self.subTest(label):
                path = ROOT / 'scenarios/MOV-0019' / f'{label}.yaml'
                self.assertEqual(path.read_bytes(), variant_text(label).encode())
                units = next(run_sets(PATHING, path, [adopted]))
                self.assertEqual(json.loads(json.dumps(summary(units, targets_of(path)))),
                                 row['outcomes'][row['adopted_outcome']])
                self.assertEqual(len(row['candidate_outcome']), len(predictions['candidates']))


if __name__ == '__main__':
    unittest.main()

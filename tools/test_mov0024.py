"""Negative controls for occupied-goal evidence, including rejected hypotheses."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from compare_traces import compare
from run_mov0024 import LABELS, assess, candidate, intervention, run, verify_download, predictions
from trace_contract import BUILD, ROOT, load, write_json

class OccupiedGoalGateTests(unittest.TestCase):
    def test_retained_verdicts_cannot_be_hidden(self):
        reviewed = load(ROOT / 'results/mov-0024/reviewed.json')
        for label in LABELS:
            reference = load(ROOT / f'oracle/canonical-generated/{BUILD}/{label}.json')
            actual = load(ROOT / predictions('H0')['cases'][label]['trace'])
            comparison = compare(reference, actual)
            self.assertTrue(assess(comparison, reviewed['cases'][label]['comparison']))
            hidden = copy.deepcopy(comparison)
            hidden['status'] = 'PASS' if comparison['status'] == 'FAIL' else 'FAIL'
            self.assertFalse(assess(hidden, reviewed['cases'][label]['comparison']))
            self.assertEqual(candidate(label, reference), reviewed['cases'][label]['candidate'])

    def test_blocked_occupant_intervention_is_observed(self):
        reference = load(ROOT / f'oracle/canonical-generated/{BUILD}/MOV-0024-c.json')
        changed = copy.deepcopy(reference)
        row = next(r for r in changed['records'] if r['kind'] == 'SAMPLE' and r['callback'] == 400 and r['unit'] == 'u1')
        row['values']['order'] = '0'
        self.assertEqual(intervention('MOV-0024-c', changed)['status'], 'INCONCLUSIVE')
        row['values']['x'] = '20'
        self.assertFalse(intervention('MOV-0024-c', changed)['occupant_state'])

    def test_timed_intervention_cannot_hide_stop_relocation(self):
        reference = load(ROOT / f'oracle/canonical-generated/{BUILD}/MOV-0024-f.json')
        self.assertEqual(intervention('MOV-0024-f', reference)['status'], 'INCONCLUSIVE')
        changed = copy.deepcopy(reference)
        row = next(r for r in changed['records'] if r['kind'] == 'SAMPLE'
                   and r['callback'] == 97 and r['unit'] == 'u0')
        self.assertEqual(row['values']['order'], '0')
        row['values']['x'], row['values']['y'] = '-30.222656', '0.012695'
        self.assertEqual(intervention('MOV-0024-f', changed)['status'], 'PASS')
        row['values']['order'] = '851986'
        self.assertEqual(intervention('MOV-0024-f', changed)['status'], 'INCONCLUSIVE')

    def test_finite_gate_and_download_regrade(self):
        ext = '.exe' if os.name == 'nt' else ''
        runner = Path(os.environ.get('WC3TEST_RUNNER', ROOT / f'build/wc3test{ext}'))
        codegen = Path(os.environ.get('ORACLE_CODEGEN', ROOT / f'build/oracle_codegen{ext}'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run(runner, codegen, root / 'mov-0024', root / 'reports'), 0)
            report = load(root / 'reports/mov0024.json')
            self.assertEqual([c['map_revision'] for c in report['cases']], list(LABELS))
            result = dict(mov0024_required=True, mov0024=dict(status='PASS'))
            self.assertEqual(verify_download(root, result)['cases'], 6)
            with self.assertRaisesRegex(ValueError, 'required MOV-0024'):
                verify_download(root, {})
            for change in ('missing', 'candidate', 'intervention'):
                altered = copy.deepcopy(report)
                if change == 'missing': altered['cases'].pop()
                elif change == 'candidate': altered['cases'][0]['candidate']['comparison']['status'] = 'INVENTED'
                else: altered['cases'][0]['intervention']['status'] = 'INVENTED'
                write_json(root / 'reports/mov0024.json', altered)
                with self.assertRaises(ValueError): verify_download(root, result)

if __name__ == '__main__':
    unittest.main()

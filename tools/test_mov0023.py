"""Negative controls for the frozen three-unit prediction/evidence gate."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from compare_traces import compare
from predict_mov0023 import describe
from run_mov0023 import LABELS, assess, run, verify_download
from trace_contract import BUILD, ROOT, load


class ThreeFootmanGateTests(unittest.TestCase):
    def test_retained_failure_cannot_be_hidden_or_changed(self):
        reviewed = load(ROOT / 'results/mov-0023/reviewed.json')['cases']['MOV-0023-a']
        reference = load(ROOT / f'oracle/canonical-generated/{BUILD}/MOV-0023-a.json')
        actual = load(ROOT / 'results/mov-0023/predicted/MOV-0023-a.json')
        comparison = compare(reference, actual)
        self.assertEqual(comparison['status'], 'FAIL')
        self.assertTrue(assess(comparison, reviewed['comparison']))
        # An invented pass, an erased order failure or another route divergence fails.
        changes = []
        hidden = copy.deepcopy(comparison)
        hidden['status'] = 'PASS'
        changes.append(hidden)
        erased = copy.deepcopy(comparison)
        erased['properties']['order']['failures'] = 0
        changes.append(erased)
        changed = copy.deepcopy(actual)
        row = next(r for r in changed['records'] if r['kind'] == 'SAMPLE' and r['callback'] == 100 and r['unit'] == 'u0')
        row['values']['x'] = str(float(row['values']['x']) + 10)
        changes.append(compare(reference, changed))
        for candidate in changes:
            self.assertFalse(assess(candidate, reviewed['comparison']))
        self.assertFalse(assess(compare(reference, reference), reviewed['comparison']))

    def test_descriptions_include_both_blockers_and_nonarrival(self):
        for label in LABELS:
            trace = load(ROOT / f'results/mov-0023/predicted/{label}.json')
            for unit, value in describe(trace).items():
                self.assertEqual(set(value['pairs']), {'u0', 'u1', 'u2'} - {unit})
                if label != 'MOV-0023-d':
                    self.assertIsNone(value['arrival_callback'])
                    self.assertNotEqual(value['final']['order'], 0)

    def test_finite_evidence_gate(self):
        ext = '.exe' if os.name == 'nt' else ''
        runner = Path(os.environ.get('WC3TEST_RUNNER', ROOT / f'build/wc3test{ext}'))
        codegen = Path(os.environ.get('ORACLE_CODEGEN', ROOT / f'build/oracle_codegen{ext}'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run(runner, codegen, root / 'mov-0023', root / 'reports'), 0)
            report = load(root / 'reports/mov0023.json')
            self.assertEqual([c['map_revision'] for c in report['cases']], list(LABELS))
            self.assertEqual(report['cases'][0]['compatibility'], 'FAIL')
            result = dict(mov0023_required=True, mov0023=dict(status='PASS'))
            self.assertEqual(verify_download(root, result)['cases'], 4)
            for missing in ({}, dict(mov0023_required=False, mov0023=dict(status='PASS'))):
                with self.assertRaisesRegex(ValueError, 'required MOV-0023'):
                    verify_download(root, missing)
            # Truncated layouts and altered downloaded grades cannot pass regrading.
            from trace_contract import write_json
            changed = copy.deepcopy(report)
            changed['cases'].pop()
            write_json(root / 'reports/mov0023.json', changed)
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                verify_download(root, result)
            changed = copy.deepcopy(report)
            changed['cases'][0]['comparison']['status'] = 'PASS'
            write_json(root / 'reports/mov0023.json', changed)
            with self.assertRaisesRegex(ValueError, 'does not reproduce'):
                verify_download(root, result)


if __name__ == '__main__':
    unittest.main()

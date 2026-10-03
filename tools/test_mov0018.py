"""MOV-0018 gate (shared by MOV-0019/0020): P3 acceptance, the reviewed differences,
downloaded regrade.

Uses the built runner (WC3TEST_RUNNER) and generator (ORACLE_CODEGEN). Tampering
happens only in temporary copies.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from trace_contract import ROOT, load, write_json

EXT = '.exe' if os.name == 'nt' else ''
RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' / f'wc3test{EXT}'))
CODEGEN = Path(os.environ.get('ORACLE_CODEGEN', ROOT / 'build' / f'oracle_codegen{EXT}'))


class CollisionGateTests(unittest.TestCase):
    def test_gate_requires_acceptance_and_reviewed_differences_and_regrades_downloads(self):
        from run_mov0018 import KNOWN, acceptance, run
        from summarize_ci import verify_collision
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run(RUNNER, CODEGEN, root / 'mov-0018', root / 'reports'), 0)
            result = dict(mov0018_required=True, mov0018=dict(status='PASS'))
            self.assertEqual(verify_collision(root, result, 'MOV-0018')['cases'], 4)
            for missing in ({}, dict(mov0018_required=False, mov0018=dict(status='PASS')),
                            dict(mov0018_required=True, mov0018=dict(status='FAIL'))):
                with self.assertRaisesRegex(ValueError, 'required MOV-0018 gate'):
                    verify_collision(root, missing, 'MOV-0018')
            self.assertIsNone(verify_collision(root, {}, 'MOV-0018', legacy=True))
            # A changed reviewed list is a failing gate, not a new expectation:
            # a new pass, one failure more or less, and a tighter bound all fail.
            for label, failing in (('MOV-0018-a', {'facing': (1, 1.0)}), ('MOV-0018-c', {}),
                                   ('MOV-0018-b', dict(KNOWN['MOV-0018-b']['failing'], x=(510, .032))),
                                   ('MOV-0018-b', dict(KNOWN['MOV-0018-b']['failing'], facing=(127, 1.0)))):
                known = dict(KNOWN[label], failing=failing)
                with self.subTest(label, failing=failing), mock.patch.dict(KNOWN, {label: known}):
                    self.assertEqual(run(RUNNER, CODEGEN, root / 'again', root / 'again-reports'), 1)
            # Reviewed open P3 differences must be exactly the failing checks: one
            # claimed where every check passes fails the gate.
            known = dict(KNOWN['MOV-0018-a'], open={'u0': {'side': 'P3'}})
            with mock.patch.dict(KNOWN, {'MOV-0018-a': known}):
                self.assertEqual(run(RUNNER, CODEGEN, root / 'open', root / 'open-reports'), 1)
            # P3 acceptance: the wrong side, a late arrival and a different final position each fail.
            reference = load(root / 'mov-0018/references/MOV-0018-a.json')
            self.assertEqual(acceptance(reference, reference)['status'], 'PASS')
            for name, forge in (('side', lambda r: r['values'].update(y=str(-float(r['values']['y'])))),
                                ('arrival', lambda r: r['values'].update(order='851986') if r['callback'] in (185, 186, 187, 188) else None),
                                ('final', lambda r: r['values'].update(x='990.000000') if r['callback'] == 600 else None)):
                trace = load(root / 'mov-0018/references/MOV-0018-a.json')
                for record in trace['records']:
                    if record['kind'] == 'SAMPLE' and record['unit'] == 'u0':
                        forge(record)
                checks = acceptance(reference, trace)
                with self.subTest(name):
                    self.assertEqual(checks['status'], 'FAIL')
                    self.assertFalse(checks['checks']['u0'][name])
            # A forged downloaded trace cannot keep a PASS report.
            path = root / 'mov-0018/traces/MOV-0018-b/MOV-0018.json'
            trace = load(path)
            next(r for r in trace['records'] if r['kind'] == 'SAMPLE' and r['callback'] == 300)['values'].update(x='1.000000')
            write_json(path, trace, compact_records=True)
            with self.assertRaisesRegex(ValueError, 'does not reproduce'):
                verify_collision(root, result, 'MOV-0018')


if __name__ == '__main__':
    unittest.main()

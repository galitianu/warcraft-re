"""Scenario v1 through wc3test: migration, provenance, invalid input and ordering.

Uses the built runner (WC3TEST_RUNNER, default build/wc3test). Retail fixtures are
read only for comparison; no scenario can redefine the canonical trace contract.
"""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from trace_contract import ROOT, digest, load, payload, validate

RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' /
              ('wc3test.exe' if os.name == 'nt' else 'wc3test')))
SCENARIOS = ROOT / 'scenarios'
CASES = [f'MOV-{n:04d}' for n in range(1, 11)]
SUITES = (('v1', 'after'), ('v2', 'after'), ('v2', 'before'), ('v3', 'after'), ('v4', 'after'))


def runner(*args):
    return subprocess.run([str(RUNNER), *map(str, args)], cwd=ROOT, capture_output=True,
                          text=True, timeout=120)


def f32(text):
    return struct.unpack('<f', struct.pack('<f', float(text)))[0]


def without_scenario_identity(trace):
    """The only metadata a scenario run adds: build.scenarios and provenance.scenario."""
    trace = dict(trace, provenance={})
    build = {k: v for k, v in trace['identity']['build'].items() if k != 'scenarios'}
    trace['identity'] = dict(trace['identity'], build=build)
    return trace


ORDERED = '''schema: wc3-scenario
version: 1
experiment: ORD-9002
map_revision: ORD-9002
units:
  - name: u0
    type: hfoo
    position: [0, 0]
    facing: 0
  - name: u1
    type: hfoo
    position: [0.5, 384]
    facing: 90
    move_speed: 100
observe:
  period: 0.02
  callbacks: 60
  properties: [x, "y", facing, order]
actions:
  - at: 0
    unit: u0
    order: move
    target: [1000, 0]
  - at: 1.0
    unit: u1
    order: move
    offset: [0, 100]
  - at: 1.0
    unit: u0
    order: stop
  - at: 1.0
    unit: u0
    order: move
    offset: [-0.5, 2.25]
...
'''


class ScenarioRunnerTests(unittest.TestCase):
    def test_migrated_scenarios_reproduce_hard_coded_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            for model, phase in SUITES:
                coded, declared = Path(temp) / f'{model}-{phase}', Path(temp) / f'{model}-{phase}-scenario'
                common = ('--model', model, '--phase', phase, '--seed', '1')
                self.assertEqual(runner(*common, '--out', coded).returncode, 0)
                result = runner(*common, '--scenario', 'scenarios', '--out', declared)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(sorted(p.name for p in coded.iterdir()), sorted(p.name for p in declared.iterdir()))
                for case in CASES:
                    for suffix in ('.csv', '-actions.csv'):
                        self.assertEqual((coded / f'{case}{suffix}').read_bytes(), (declared / f'{case}{suffix}').read_bytes())
                    a, b = validate(load(coded / f'{case}.json')), validate(load(declared / f'{case}.json'))
                    self.assertEqual(digest(payload(a)), digest(payload(b)), f'{model}-{phase} {case}')
                    self.assertNotEqual((coded / f'{case}.json').read_bytes(), (declared / f'{case}.json').read_bytes())
                    self.assertEqual(without_scenario_identity(b), a)
                    self.assertEqual(a['provenance'], {})

    def test_provenance_binds_the_exact_scenario_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'one'
            result = runner('--model', 'v4', '--scenario', 'scenarios/MOV-0006.yaml', '--out', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ['MOV-0006-actions.csv', 'MOV-0006.csv', 'MOV-0006.json', 'identity.json'])
            trace = validate(load(out / 'MOV-0006.json'))
            expected = hashlib.sha256((SCENARIOS / 'MOV-0006.yaml').read_bytes()).hexdigest()
            self.assertEqual(trace['provenance'], {'scenario': {
                'schema': 'wc3-scenario', 'version': 1, 'path': 'scenarios/MOV-0006.yaml', 'sha256': expected}})
            build = trace['identity']['build']
            self.assertEqual(build['cases'], [{'test': 'MOV-0006', 'callbacks': 250, 'units': 1, 'samples': 251}])
            self.assertEqual(build['scenarios'], [{'experiment': 'MOV-0006', 'map_revision': 'MOV-0006',
                                                   'path': 'scenarios/MOV-0006.yaml', 'sha256': expected}])
            # The unchanged comparator grades it against the independent WC3 fixture.
            compared = subprocess.run([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', out,
                                       '--case', 'MOV-0006'], cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            # Altered provenance is caught by the contract.
            altered = dict(trace, provenance={'scenario': dict(trace['provenance']['scenario'], sha256='0' * 64)})
            with self.assertRaisesRegex(ValueError, 'scenario provenance differs'):
                validate(altered)

    def test_a_description_cannot_redefine_a_retained_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'MOV-0006.yaml'
            path.write_text((SCENARIOS / 'MOV-0006.yaml').read_text().replace('callbacks: 250', 'callbacks: 300'), newline='\n')
            out = Path(temp) / 'out'
            self.assertEqual(runner('--model', 'v4', '--scenario', path, '--out', out).returncode, 0)
            with self.assertRaisesRegex(ValueError, 'build case table cannot redefine|scenario identity/shape'):
                validate(load(out / 'MOV-0006.json'))
            compared = subprocess.run([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', out,
                                       '--case', 'MOV-0006'], cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(compared.returncode, 2)

    def test_migration_gate_detects_changed_meaning_and_identity(self):
        from run_ci import migration
        suite = {'cases': []}  # Report equality is exercised by run_ci itself.
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            copy = temp / 'scenarios'
            shutil.copytree(SCENARIOS, copy)
            dirs = {name: temp / name for name in ('coded', 'declared', 'edited')}
            self.assertEqual(runner('--model', 'v4', '--out', dirs['coded']).returncode, 0)
            self.assertEqual(runner('--model', 'v4', '--scenario', 'scenarios', '--out', dirs['declared']).returncode, 0)
            self.assertEqual(migration(dirs['coded'], dirs['declared'], suite, suite)['status'], 'EQUIVALENT')
            # A changed relative offset changes the payload and fails migration.
            edited = copy / 'MOV-0006.yaml'
            edited.write_text(edited.read_text().replace('offset: [0, 1000]', 'offset: [0, 999.5]'), newline='\n')
            self.assertEqual(runner('--model', 'v4', '--scenario', copy, '--out', dirs['edited']).returncode, 0)
            with self.assertRaisesRegex(ValueError, 'MOV-0006: scenario observation payload differs'):
                migration(dirs['coded'], dirs['edited'], suite, suite)
            # A comment edit keeps the meaning but not the identity; a file changed after
            # the run no longer matches the recorded hash.
            edited.write_text((SCENARIOS / 'MOV-0006.yaml').read_text() + '# reviewed\n', newline='\n')
            shutil.rmtree(dirs['edited'])
            self.assertEqual(runner('--model', 'v4', '--scenario', copy, '--out', dirs['edited']).returncode, 0)
            self.assertEqual(migration(dirs['coded'], dirs['edited'], suite, suite)['status'], 'EQUIVALENT')
            edited.write_text(edited.read_text() + '# changed later\n', newline='\n')
            with self.assertRaisesRegex(ValueError, 'scenario hash differs'):
                migration(dirs['coded'], dirs['edited'], suite, suite)

    def test_invalid_descriptions_fail_before_any_output(self):
        base = (SCENARIOS / 'MOV-0006.yaml').read_text()
        cases = {
            'version': (base.replace('version: 1', 'version: 2'), 'unsupported scenario version 2'),
            'field': (base.replace('  callbacks: 250', '  callbacks: 250\n  seed: 7'), "unsupported field 'seed'"),
            'action': (base.replace('order: move\n    offset', 'order: patrol\n    offset'), "unsupported order 'patrol'"),
            'type': (base.replace('type: hfoo', 'type: hpea'), "unsupported unit type 'hpea'"),
            'unit-ref': (base.replace('    unit: u0\n    order: move\n    offset', '    unit: u7\n    order: move\n    offset'), "unknown unit 'u7'"),
            'duplicate': (base.replace('    facing: 0\n', '    facing: 0\n  - name: u0\n    type: hfoo\n    position: [1, 1]\n    facing: 0\n', 1), "duplicate unit name 'u0'"),
            'truncated': (base[:base.index('  - at: 1.0')], "missing document end marker"),
            'mid-line': (base[:-10], 'must end with a newline'),
            'nonfinite': (base.replace('[1000, 0]', '[.inf, 0]'), 'unquoted decimal'),
            'overflow': (base.replace('[1000, 0]', '[1' + '0' * 40 + ', 0]'), 'out of range'),
            'period': (base.replace('period: 0.02', 'period: 0'), 'period must be in (0, 10] seconds'),
            'rounding': (base.replace('period: 0.02', 'period: 0.0200005'), 'whole number of microseconds'),
            'off-schedule': (base.replace('at: 1.0', 'at: 1.01'), 'not a callback time'),
            'after-end': (base.replace('at: 1.0', 'at: 5.02'), 'after the last callback'),
            'capability': (base.replace('period: 0.02', 'period: 0.01').replace('callbacks: 250', 'callbacks: 500'),
                           'supports only the 0.020000 s period'),
        }
        with tempfile.TemporaryDirectory() as temp:
            for name, (text, message) in cases.items():
                with self.subTest(name):
                    path = Path(temp) / f'{name}.yaml'
                    path.write_text(text, newline='\n')
                    out = Path(temp) / f'out-{name}'
                    # A valid description in the same run must not produce output either.
                    result = runner('--model', 'v4', '--scenario', 'scenarios/MOV-0001.yaml', '--scenario', path, '--out', out)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn(message, result.stderr)
                    self.assertFalse(out.exists(), 'invalid input produced output')
            out = Path(temp) / 'out-repeat'
            result = runner('--model', 'v4', '--scenario', 'scenarios/MOV-0001.yaml',
                            '--scenario', 'scenarios/MOV-0001.yaml', '--out', out)
            self.assertEqual(result.returncode, 2)
            self.assertIn('already declared', result.stderr)
            missing = runner('--model', 'v4', '--scenario', Path(temp) / 'absent.yaml', '--out', out)
            self.assertEqual(missing.returncode, 2)
            self.assertIn('scenario not found', missing.stderr)
            self.assertFalse(out.exists())

    def test_equal_time_actions_keep_file_order_and_relative_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'ORD-9002.yaml'
            path.write_text(ORDERED, newline='\n')
            out = Path(temp) / 'out'
            result = runner('--model', 'v4', '--scenario', path, '--out', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            trace = load(out / 'ORD-9002.json')
            # No independent retail shape exists, so the contract gives it no verdict.
            with self.assertRaisesRegex(ValueError, 'unsupported scenario revision'):
                validate(trace)
            records = [r for r in trace['records'] if r.get('callback') == 50]
            self.assertEqual([(r['kind'], r.get('unit'), r.get('command')) for r in records],
                             [('TICK', None, None), ('SAMPLE', 'u0', None), ('SAMPLE', 'u1', None),
                              ('ACTION', 'u1', 'move'), ('ACTION', 'u0', 'stop'), ('ACTION', 'u0', 'move')])
            self.assertEqual([r['seq'] for r in records], list(range(records[0]['seq'], records[0]['seq'] + 6)))
            u0, u1 = records[1]['values'], records[2]['values']
            self.assertGreater(f32(u0['x']), 0)
            moved = records[5]['target']
            self.assertEqual(f32(moved['x']), f32(f32(u0['x']) + f32('-0.5')))
            self.assertEqual(f32(moved['y']), f32(f32(u0['y']) + f32('2.25')))
            self.assertEqual(records[3]['target'], {'x': u1['x'], 'y': '484'})
            self.assertEqual(trace['units'][1]['speed'], '150')  # SetUnitMoveSpeed 100, clamped by the world.
            self.assertEqual(trace['completion']['actions'], 4)


if __name__ == '__main__':
    unittest.main()

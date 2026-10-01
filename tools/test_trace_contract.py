"""Contract/migration integrity, separate from retail compatibility."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compare_traces import actions, compare, samples
from normalize_traces import normalize_all, normalize_capture
from oracle_parse import parse
from trace_contract import BUILD, LABELS, ROOT, counts, digest, load, payload, validate

FIXTURES = ROOT / 'oracle/canonical' / BUILD


class NormalizationTests(unittest.TestCase):
    def test_all_45_runs_reproduce_lossless_fixtures(self):
        with tempfile.TemporaryDirectory() as temp:
            summary = normalize_all(Path(temp))
            self.assertEqual(sum(s['runs_validated'] for s in summary), 45)
            for name in [f'{l}.json' for l in LABELS] + ['index.json']:
                self.assertEqual((Path(temp) / name).read_bytes(), (FIXTURES / name).read_bytes())
            for label in LABELS:
                trace = validate(load(FIXTURES / f'{label}.json'))
                raw = parse(ROOT / f'oracle/captures/{BUILD}/{label}/run-01.txt')
                self.assertEqual([r['source']['payload'] for r in trace['records']], raw['_records'])
                self.assertEqual([r['values'] for r in samples(trace)], [{k: row[k] for k in ('x', 'y', 'facing', 'order')} for row in raw['_samples']])

    def test_equal_time_and_action_order_retained(self):
        base = ROOT / f'oracle/captures/{BUILD}/MOV-0002-r2'
        raw = parse(base / 'run-01.txt')
        ticks = raw['_ticks']
        text = (base / 'run-01.txt').read_text().replace(f'|{ticks[6]["t"]}|', f'|{ticks[5]["t"]}|')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'equal-time.txt'
            path.write_text(text)
            altered = parse(path)
            trace = normalize_capture(altered, load(base / 'manifest.json'))
        seq = [(r['callback'], r['unit']) for r in samples(trace) if r['time']['reported'] == ticks[5]['t']]
        self.assertEqual(seq, [(5, 'u0'), (5, 'u1'), (6, 'u0'), (6, 'u1')])
        action = actions(trace)[0]
        self.assertGreater(action['seq'], max(r['seq'] for r in samples(trace) if r['callback'] == 0))
        trace50 = load(FIXTURES / 'MOV-0006.json')
        self.assertGreater(actions(trace50)[1]['seq'], next(r['seq'] for r in samples(trace50) if r['callback'] == 50))

    def test_nine_decimal_clock_payload_and_transport_preserved(self):
        trace = load(FIXTURES / 'JASS-0001-p001.json')
        event = next(r for r in trace['records'] if r['kind'] == 'EVENT' and r['callback'] == 1)
        self.assertEqual(event['values']['c1000_9'], '0.001037598')
        self.assertEqual(event['time']['requested'], '0.001000')
        self.assertEqual(event['time']['reported'], '0.001038')
        self.assertEqual(trace['provenance']['repeatability']['distinct_raw_files'], 2)
        self.assertEqual([r['footer'] for r in trace['provenance']['runs']], ['call PreloadEnd( 0.6 )', 'call PreloadEnd( 0.7 )', 'call PreloadEnd( 0.6 )'])

    def test_reference_identity_and_source_mapping_rejected(self):
        ref = load(FIXTURES / 'MOV-0001.json')
        for mutation in (lambda t: t['identity'].update(build='wc3-other'),
                         lambda t: t['identity']['source']['case'].update(path='other.j'),
                         lambda t: t['identity']['source']['case'].update(sha256='0'*64),
                         lambda t: t['records'][5]['source'].update(seq=99),
                         lambda t: t['provenance']['runs'].pop(),
                         lambda t: t['provenance']['runs'][0].update(payload_sha256='0'*64)):
            t = copy.deepcopy(ref); mutation(t)
            with self.assertRaises(ValueError): validate(t)

    def test_reference_cannot_forge_its_own_raw_identity(self):
        from compare_traces import verify_reference_provenance
        ref = load(FIXTURES / 'MOV-0001.json')
        ref['provenance']['runs'][0]['sha256'] = '0'*64
        # Self-consistent shape alone is insufficient for a trusted CLI reference.
        validate(ref)
        with self.assertRaisesRegex(ValueError, 'retained capture manifest'):
            verify_reference_provenance(ref)


class CanonicalComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        cls.addClassCleanup(cls.temp.cleanup)
        subprocess.run([str(ROOT / 'build/wc3test'), '--out', str(cls.out), '--model', 'v2'], check=True, stdout=subprocess.DEVNULL)

    def setUp(self):
        self.ref = load(FIXTURES / 'MOV-0001.json')
        self.act = load(self.out / 'MOV-0001.json')

    def test_circular_facing_and_clock_quantization(self):
        for rec in samples(self.act): rec['values']['facing'] = '359.9998'
        self.assertEqual(compare(self.ref, self.act)['status'], 'PASS')
        self.assertEqual(compare(load(FIXTURES / 'MOV-0002-r2.json'), load(self.out / 'MOV-0002.json'))['properties']['t']['status'], 'PASS')

    def test_first_divergence_and_continued_per_unit_error(self):
        rows = samples(self.act)
        rows[1]['values']['x'] = '.0011' # syntax itself must be lossless and valid
        with self.assertRaises(ValueError): validate(self.act)
        rows[1]['values']['x'] = '0.0011'
        rows[-1]['values']['x'] = '12'
        rows[2]['values']['order'] = '851986'
        report = compare(self.ref, self.act)
        self.assertEqual(report['first_divergence']['callback'], 1)
        self.assertEqual(report['first_divergence']['reference_seq'], samples(self.ref)[1]['seq'])
        self.assertEqual(report['properties']['x']['max_abs_delta_by_unit'], {'u0': 12})
        self.assertEqual(report['properties']['x']['final_delta_by_unit'], {'u0': 12})
        self.assertEqual(report['properties']['order']['first_divergence']['callback'], 2)

    def test_missing_reordered_duplicate_and_nonfinite_records_rejected(self):
        def reverse(t): t['records'][3:5] = t['records'][3:5][::-1]
        mutations = [lambda t: t['records'].pop(), reverse,
                     lambda t: t['records'][4].update(seq=3),
                     lambda t: t['completion'].update(complete=False),
                     lambda t: t['scenario'].update(callbacks=1),
                     lambda t: t['scenario'].update(requested_period='0.010000'),
                     lambda t: t['identity']['build']['cases'][0].update(units=999),
                     lambda t: t['time'].update(unit='ms'),
                     lambda t: t['time'].update(state_lag_us=1000),
                     lambda t: t['records'][4]['time'].update(state_us=1)]
        for field, value in [('x', 'NaN'), ('x', '1e999'), ('x', '1e309'), ('order', '99999999999999999999'), ('facing', '360')]:
            mutations.append(lambda t, f=field, v=value: samples(t)[0]['values'].update({f:v}))
        for i, mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                trace = copy.deepcopy(self.act); mutation(trace)
                with self.assertRaises(ValueError): validate(trace)

    def test_actions_acceptance_target_and_structure(self):
        ref = load(FIXTURES / 'MOV-0006.json'); act = load(self.out / 'MOV-0006.json')
        action = actions(act)[1]
        action['accepted'] = False
        report = compare(ref, act)
        self.assertEqual(report['action_properties']['accepted']['status'], 'FAIL')
        self.assertEqual(report['action_properties']['target_x']['status'], 'FAIL')
        self.assertEqual(report['action_properties']['target_x']['final_delta_by_unit']['u0'], float(action['target']['x'])-float(actions(ref)[1]['target']['x']))
        # Honest complete trace missing an action: structural incompatibility, not input error.
        act['records'].remove(action)
        for seq, rec in enumerate(act['records']): rec['seq'] = seq
        act['completion'] = counts(act['records'])
        self.assertEqual(compare(ref, act)['first_structural_divergence']['property'], 'action_count')

    def test_sample_before_action_order_and_action_sequence(self):
        ref = load(FIXTURES / 'MOV-0010.json'); act = load(self.out / 'MOV-0010.json')
        # Valid but reversed command meanings at their recorded callbacks.
        a, b = actions(act)
        a['command'], b['command'] = b['command'], a['command']
        a['target'], b['target'] = b['target'], a['target']
        report = compare(ref, act)
        self.assertEqual(report['action_properties']['command']['failures'], 2)
        # Moving callback-0 action ahead of samples violates the format's ordering.
        act = load(self.out / 'MOV-0010.json')
        action = actions(act)[0]
        act['records'].remove(action); act['records'].insert(4, action)
        for seq, rec in enumerate(act['records']): rec['seq'] = seq
        with self.assertRaisesRegex(ValueError, 'precedes samples'): validate(act)

    def test_unit_type_mismatch_is_structural_failure(self):
        self.act['units'][0]['type'] = 'other-unit'
        report = compare(self.ref, self.act)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['first_structural_divergence']['property'], 'unit_type')

    def test_command_timing_mismatch_is_a_completed_failure(self):
        ref = load(FIXTURES / 'MOV-0006.json'); act = load(self.out / 'MOV-0006.json')
        action = actions(act)[1]
        act['records'].remove(action)
        next_sample = next(r for r in samples(act) if r['callback'] == 51)
        action['callback'] = 51
        action['time'] = copy.deepcopy(next_sample['time'])
        act['records'].insert(act['records'].index(next_sample)+1, action)
        for seq, rec in enumerate(act['records']): rec['seq'] = seq
        report = compare(ref, act)
        self.assertEqual(report['action_properties']['callback']['status'], 'FAIL')
        self.assertEqual(report['action_properties']['t']['status'], 'FAIL')

    def test_phase_and_known_failures_survive(self):
        for label, cb, prop in [('MOV-0002-r2', 1, 'y'), ('MOV-0009', 7, 'x')]:
            name = 'MOV-0002' if label.endswith('-r2') else label
            first = compare(load(FIXTURES / f'{label}.json'), load(self.out / f'{name}.json'))['state_first_divergence']
            self.assertEqual((first['callback'], first['property']), (cb, prop))
        clock = compare(load(FIXTURES / 'MOV-0004.json'), load(self.out / 'MOV-0004.json'))['properties']['t']
        self.assertEqual(clock['failures'], 53)
        self.assertEqual(clock['first_divergence']['callback'], 503)
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(ROOT / 'build/wc3test'), '--out', temp, '--phase', 'before'], check=True, stdout=subprocess.DEVNULL)
            before = load(Path(temp) / 'MOV-0006.json'); validate(before)
            self.assertEqual(samples(before)[0]['time']['state_us'], 0)
            self.assertEqual(next(r for r in samples(before) if r['callback'] == 50)['time']['state_us'], 999000)
            self.assertEqual(actions(before)[1]['time']['state_us'], 1000000)

    def test_event_payloads_are_compared_and_missing_properties_unobserved(self):
        ref = load(FIXTURES / 'JASS-0001-p001.json')
        report = compare(ref, ref)
        self.assertEqual(report['event_properties']['CLOCKS.c1000_9']['status'], 'PASS')
        # C++ explicitly lacks CLOCKS, rather than claiming they passed.
        report = compare(load(FIXTURES / 'MOV-0002-r2.json'), load(self.out / 'MOV-0002.json'))
        self.assertEqual(report['unobserved_properties'], [])
        # Synthetic event extension in a copy only: unavailable C++ property is
        # excluded from the named scope and is never assigned a passing statistic.
        mov = copy.deepcopy(self.ref)
        event = dict(seq=0, kind='EVENT', source=None, callback=0,
                     time=copy.deepcopy(samples(mov)[0]['time']), name='TEST_CLOCK', values={'seconds':'0.000000'})
        mov['records'].insert(6, event)
        for seq, rec in enumerate(mov['records']):
            rec['seq'] = seq
            if rec is event:
                raw = f'@O|{seq}|EVENT|0.000000|TEST_CLOCK|seconds=0.000000'
            else:
                fields = rec['source']['payload'].split('|'); fields[1] = str(seq)
                raw = '|'.join(fields)
            rec['source'] = {'seq':seq, 'payload':raw}
        mov['completion'] = counts(mov['records'])
        raw_hash = hashlib.sha256('\n'.join(r['source']['payload'] for r in mov['records']).encode()).hexdigest()
        for run in mov['provenance']['runs']: run['payload_sha256'] = raw_hash
        repeat = mov['provenance']['repeatability']
        repeat['observation_payload_sha256'] = [raw_hash]*3
        repeat['canonical_payload_sha256'] = [digest(payload(mov))]*3
        report = compare(mov, self.act)
        self.assertEqual(report['unobserved_properties'], ['TEST_CLOCK.seconds'])
        self.assertEqual(report['event_properties'], {})
        from compare_traces import compare_suite
        self.assertEqual(compare_suite(FIXTURES, self.out)['timing_variants']['status'], 'UNOBSERVED')

    def test_equal_time_event_action_interleaving_is_compared(self):
        ref = load(FIXTURES / 'JASS-0001-p001.json')
        act = copy.deepcopy(ref)
        action = actions(act)[0]
        event = next(r for r in act['records'] if r['kind'] == 'EVENT')
        i, j = act['records'].index(action), act['records'].index(event)
        act['records'][i], act['records'][j] = event, action
        for seq, rec in enumerate(act['records']):
            rec['seq'] = seq
            fields = rec['source']['payload'].split('|'); fields[1] = str(seq)
            rec['source'] = {'seq':seq, 'payload':'|'.join(fields)}
        raw_hash = hashlib.sha256('\n'.join(r['source']['payload'] for r in act['records']).encode()).hexdigest()
        for run in act['provenance']['runs']: run['payload_sha256'] = raw_hash
        act['provenance']['repeatability']['observation_payload_sha256'] = [raw_hash]*3
        act['provenance']['repeatability']['canonical_payload_sha256'] = [digest(payload(act))]*3
        report = compare(ref, act)
        self.assertEqual(report['first_structural_divergence']['property'], 'observable_record_order')

    def test_cli_exit_0_1_2_and_overflow_without_traceback(self):
        command = [sys.executable, str(ROOT / 'tools/compare_traces.py'), '--actual', str(self.out)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(command + ['--case', 'MOV-0001'], capture_output=True).returncode, 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'MOV-0001.json'
            bad = copy.deepcopy(self.act)
            mutations = [lambda t: t.update(version=2), lambda t: t['completion'].update(samples=1e999),
                         lambda t: t['scenario'].update(callbacks=10**100),
                         lambda t: t['identity']['build']['parameters'].update(stop_radius=1e999)]
            cli = [sys.executable, str(ROOT / 'tools/compare_traces.py'), '--actual', temp, '--case', 'MOV-0001']
            for mutation in mutations:
                trace = copy.deepcopy(bad); mutation(trace)
                path.write_text(json.dumps(trace))
                result = subprocess.run(cli, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
            for text in ('{"schema":"wc3-trace","schema":"wc3-trace"}', '{"n":1e999}', '{'):
                path.write_text(text)
                result = subprocess.run(cli, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
            path.unlink()
            self.assertEqual(subprocess.run(cli, capture_output=True).returncode, 2)


class FootmanV3ContractTests(unittest.TestCase):
    """footman-v3 emits the same contract; its parameters are validated separately."""
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        cls.addClassCleanup(cls.temp.cleanup)
        subprocess.run([str(ROOT / 'build/wc3test'), '--out', str(cls.out), '--model', 'v3'], check=True, stdout=subprocess.DEVNULL)

    def test_v3_traces_validate_and_keep_honest_verdicts(self):
        for n in range(1, 11):
            label = 'MOV-0002-r2' if n == 2 else f'MOV-{n:04d}'
            report = compare(load(FIXTURES / f'{label}.json'), validate(load(self.out / f'MOV-{n:04d}.json')))
            self.assertEqual(report['status'], 'PASS' if n == 1 else 'FAIL')
        first = compare(load(FIXTURES / 'MOV-0002-r2.json'), load(self.out / 'MOV-0002.json'))['state_first_divergence']
        self.assertEqual((first['callback'], first['property']), (1, 'y'))

    def test_v3_parameter_rules_cannot_be_redefined(self):
        trace = load(self.out / 'MOV-0001.json')
        for mutation in (lambda p: p.update(float_rounding='nearest'),
                         lambda p: p.update(exposure_period_steps=7),
                         lambda p: p.pop('turn_rate_radians'),
                         lambda p: p.update(position_period_steps=5)):
            bad = copy.deepcopy(trace)
            mutation(bad['identity']['build']['parameters'])
            bad['identity']['model']['parameters'] = bad['identity']['build']['parameters']
            with self.assertRaises(ValueError): validate(bad)


if __name__ == '__main__': unittest.main()

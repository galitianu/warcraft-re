"""Generated capture provenance and downloaded comparison integrity tests.

Temporary synthetic derivatives exercise tamper rejection, alongside a downloaded
artifact check of the real retained captures. Tests never retain retail evidence.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from compare_traces import compare
from normalize_generated import normalize
from oracle_parse import parse
from trace_contract import BUILD, GENERATED_SHAPES, ROOT, load, sha256, validate, write_json

RUNNER = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' /
              ('wc3test.exe' if os.name == 'nt' else 'wc3test')))
LABEL = 'MOV-0006-g1'


class GeneratedLoopTests(unittest.TestCase):
    @unittest.skipUnless(all((ROOT / f'oracle/captures/{BUILD}/{label}/manifest.json').exists()
                            for label in GENERATED_SHAPES), 'real generated captures not yet retained')
    def test_downloaded_loop_regrades_bytes_and_rejects_forged_success(self):
        from run_generated import run
        from summarize_ci import verify_generated_loop
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run(RUNNER, root / 'generated-loop', root / 'reports'), 0)
            result = dict(generated_capture_loop_required=True, generated_capture_loop=dict(status='PASS'))
            self.assertEqual(verify_generated_loop(root, result)['compatibility_passes'], 4)
            with self.assertRaisesRegex(ValueError, 'required generated capture loop'):
                verify_generated_loop(root, dict(generated_capture_loop_required=True))
            report_path = root / 'reports/generated-loop.json'
            report = load(report_path)
            actual_path = root / 'generated-loop/traces/MOV-0002-g1/MOV-0002.json'
            actual = load(actual_path)
            # A forged digest and PASS declaration must not hide changed state.
            next(r for r in actual['records'] if r['kind'] == 'SAMPLE')['values']['x'] = '1.000000'
            write_json(actual_path, actual, compact_records=True)
            report['cases'][0]['comparison']['actual_sha256'] = sha256(actual_path)
            write_json(report_path, report)
            with self.assertRaisesRegex(ValueError, 'comparison does not reproduce'):
                verify_generated_loop(root, result)
            shutil.rmtree(root / 'generated-loop/traces')
            report['cases'].pop()
            write_json(report_path, report)
            with self.assertRaisesRegex(ValueError, 'missing or unexpected revisions'):
                verify_generated_loop(root, result)

    def setup_synthetic(self, root):
        self.base = root / 'oracle/captures' / BUILD / LABEL
        self.base.mkdir(parents=True)
        def retain(path, data):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return dict(path=path, sha256=sha256(target))
        scenario = retain('scenarios/MOV-0006.yaml', (ROOT / 'scenarios/MOV-0006.yaml').read_bytes())
        case_path = f'oracle/generated/maps/{LABEL}.j'
        case_bytes = (ROOT / case_path).read_bytes()
        case = retain(case_path, case_bytes)
        lib = retain('oracle/jass/lib/oracle-v1.j', (ROOT / 'oracle/jass/lib/oracle-v1.j').read_bytes())
        env_path = f'oracle/environment/{BUILD}.json'
        env_bytes = (ROOT / env_path).read_bytes()
        environment = retain(env_path, env_bytes)
        env = load(root / env_path)
        verification = dict(reference_build=BUILD, target='vm', os_architecture='ARM64',
                            files=[dict(f, pe_machine=332) if 'version' in f else f for f in env['files']])
        verify_path = 'oracle/environment/synthetic-verification.json'
        write_json(root / verify_path, verification)
        generation_path = f'oracle/generated/maps/{LABEL}-generation.json'
        generation = retain(generation_path, (ROOT / generation_path).read_bytes())
        map_info = retain(f'oracle-maps/{LABEL}.w3m', b'SYNTHETIC UNIT TEST; NEVER A RETAIL MAP')
        setup = re.search(rb'call OracleSetup\("([^"\n]+)"\)', case_bytes)[1].decode()
        raw = (ROOT / f'oracle/captures/{BUILD}/MOV-0006/run-01.txt').read_text()
        raw = raw.replace('map=MOV-0006|', f'map={LABEL}|')
        raw = re.sub(r'(@O\|\d+\|SETUP\|)[^"\n]*', lambda m: m[1] + setup, raw)
        for run in (1, 2, 3):
            (self.base / f'run-{run:02}.txt').write_text(raw, newline='\n')
        self.manifest = dict(experiment='MOV-0006', map_label=LABEL, reference_build=BUILD,
            map=map_info, library=lib, case=case, environment=environment,
            scenario=dict(schema='wc3-scenario', version=1, **scenario), generation=generation,
            verification=dict(path=verify_path, sha256=sha256(root / verify_path)),
            check_map=dict(ok=True, trigger_matches_source=True, war3map_j_contains_source=True,
                           war3map_j_runs_init_triggers=False, w3i_format=18,
                           sha256=map_info['sha256'], case_sha256=case['sha256'], library_sha256=lib['sha256']))
        self.refresh_runs()

    def refresh_runs(self):
        runs = []
        for run in (1, 2, 3):
            path = self.base / f'run-{run:02}.txt'
            c = parse(path, map_label=LABEL)
            runs.append(dict(run=run, file=path.name, sha256=c['sha256'], payload_sha256=c['payload_sha256'], footer=c['footer'],
                             map_sha256=self.manifest['map']['sha256'], fresh_game_process=True, previous_output_removed=True))
        self.manifest['runs'] = runs
        write_json(self.base / 'manifest.json', self.manifest)

    def test_normalization_exact_reproduction_and_same_scenario_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.setup_synthetic(root)
            # The real independently captured control is read only for comparison.
            control = root / f'oracle/captures/{BUILD}/MOV-0006/run-01.txt'
            control.parent.mkdir(parents=True)
            control.write_bytes((ROOT / f'oracle/captures/{BUILD}/MOV-0006/run-01.txt').read_bytes())
            actual = root / 'actual'
            result = subprocess.run([str(RUNNER), '--scenario', 'scenarios/MOV-0006.yaml', '--model', 'v4', '--out', str(actual)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            with patch('normalize_generated.ROOT', root), patch('trace_contract.ROOT', root):
                report = normalize(LABEL, root / 'references')
                self.assertEqual(report['status'], 'PASS')
                reference = validate(load(root / 'references' / f'{LABEL}.json'))
                trace = load(actual / 'MOV-0006.json')
                self.assertEqual(compare(reference, trace)['status'], 'PASS')
                trace['provenance']['scenario']['sha256'] = '0' * 64
                # Consistent but different C++ input bytes cannot use this fixture.
                trace['identity']['build']['scenarios'][0]['sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'scenario bytes'):
                    compare(reference, trace)
                # A deterministic WC3 divergence stays a named first failure.
                for path in self.base.glob('run-*.txt'):
                    text = path.read_text().replace('|u0|0.000000|0.000000|0.000000|0', '|u0|1.000000|0.000000|0.000000|0', 1)
                    path.write_text(text, newline='\n')
                self.refresh_runs()
                report = normalize(LABEL, root / 'changed')
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(report['observations']['first_divergence']['generated'][0], 'SAMPLE')

    def test_source_freshness_and_repeatability_fail_closed(self):
        for mode, error in (('case', 'case source hash'), ('fresh', 'procedure'),
                            ('repeat', 'runs disagree'), ('map-check', 'saved-map verification')):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.setup_synthetic(root)
                if mode == 'case':
                    (root / self.manifest['case']['path']).write_bytes(b'changed')
                elif mode == 'fresh':
                    self.manifest['runs'][0]['fresh_game_process'] = False
                    write_json(self.base / 'manifest.json', self.manifest)
                elif mode == 'map-check':
                    self.manifest['check_map']['ok'] = False
                    write_json(self.base / 'manifest.json', self.manifest)
                else:
                    path = self.base / 'run-02.txt'
                    path.write_text(path.read_text().replace('|u0|0.000000|0.000000|0.000000|0', '|u0|1.000000|0.000000|0.000000|0', 1), newline='\n')
                    self.refresh_runs()
                with patch('normalize_generated.ROOT', root), patch('trace_contract.ROOT', root):
                    with self.assertRaisesRegex(ValueError, error):
                        normalize(LABEL, root / 'references')


if __name__ == '__main__':
    unittest.main()

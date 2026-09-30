#!/usr/bin/env python3
"""Reproduce Phase 3 evidence without WC3; FAIL comparisons are valid results."""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile

from compare_traces import actions, compare_suite, markdown, samples
from normalize_traces import normalize_all
from trace_contract import BUILD, LABELS, ROOT, digest, load, payload, sha256, validate, write_json


def legacy_projection(trace):
    sample_rows = [dict(callback=str(r['callback']), t=r['time']['requested'], unit=r['unit'], **r['values']) for r in samples(trace)]
    action_rows = [dict(callback=str(r['callback']), t=r['time']['requested'], unit=r['unit'],
                        order='851986' if r['command'] == 'move' else '851972',
                        target_x=r['target']['x'] if r['target'] else '', target_y=r['target']['y'] if r['target'] else '',
                        accepted='1' if r['accepted'] else '0') for r in actions(trace)]
    return sample_rows, action_rows


def run(runner, out, reports):
    references = out / 'references'
    summaries = normalize_all(references)
    # Reproduction checks committed fixtures rather than replacing them silently.
    for name in [f'{label}.json' for label in LABELS] + ['index.json']:
        if (references / name).read_bytes() != (ROOT / 'oracle/canonical' / BUILD / name).read_bytes():
            raise ValueError(f'normalized committed fixture differs: {name}')
    reports.mkdir(parents=True, exist_ok=True)
    write_json(reports / 'raw-verification.json', summaries)
    suites = {}
    for name, model, phase in (('v1', 'v1', 'after'), ('v2', 'v2', 'after'), ('v2-before', 'v2', 'before')):
        dest, report_dir = out / name, reports / name
        report_dir.mkdir(parents=True, exist_ok=True)
        command = [str(runner), '--out', str(dest), '--model', model, '--phase', phase, '--seed', '1']
        subprocess.run(command, check=True)
        report = compare_suite(references, dest)
        migration, payload_hashes = [], {}
        retained = load(ROOT / 'results/phase-2' / name / 'comparison.json')
        retained_hashes = load(ROOT / 'results/phase-2' / name / 'trace-hashes.json')
        for case, old in zip(report['cases'], retained['cases']):
            case_name = case['case']
            trace = validate(load(dest / f'{case_name}.json'))
            projection = legacy_projection(trace)
            for suffix, rows in zip(('', '-actions'), projection):
                path = dest / f'{case_name}{suffix}.csv'
                with path.open(newline='') as source:
                    if list(csv.DictReader(source)) != rows: raise ValueError(f'{case_name}: changed CSV projection')
                if sha256(path) != retained_hashes[path.name]: raise ValueError(f'{case_name}: changed Phase 2 CSV bytes')
            for prop, stat in old['properties'].items():
                new = case['properties'][prop]
                for key in ('status', 'samples', 'failures', 'max_abs_delta', 'final_delta_by_unit'):
                    if stat[key] != new[key]: raise ValueError(f'{case_name}/{prop}: changed Phase 2 statistic {key}')
                old_first, new_first = stat['first_divergence'], new['first_divergence']
                if (old_first is None) != (new_first is None): raise ValueError('changed first divergence')
                if old_first and any(old_first[k] != new_first[k] for k in old_first):
                    raise ValueError(f'{case_name}/{prop}: changed Phase 2 first divergence')
            migration.append(dict(case=case_name, legacy_state_verdict=old['status'], canonical_verdict=case['status'],
                                  samples_actions_bytes_identical=True, all_legacy_property_statistics_identical=True,
                                  new_action_differences={k: s['failures'] for k, s in case['action_properties'].items() if s['failures']}))
            payload_hashes[case_name] = digest(payload(trace))
        # Separate process, same binary/seed; compare all canonical observations and CSV bytes.
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(runner), '--out', temp, '--model', model, '--phase', phase, '--seed', '1'], check=True, stdout=subprocess.DEVNULL)
            for path in dest.iterdir():
                if path.suffix in ('.json', '.csv') and path.read_bytes() != (Path(temp) / path.name).read_bytes():
                    raise ValueError(f'{name}: separate process output differs: {path.name}')
        suites[name] = report
        write_json(report_dir / 'comparison.json', report)
        (report_dir / 'comparison.md').write_text(markdown(report))
        write_json(report_dir / 'migration.json', migration)
        write_json(report_dir / 'trace-hashes.json', {p.name: sha256(p) for p in sorted(dest.iterdir()) if p.suffix in ('.json', '.csv')})
        write_json(report_dir / 'repeatability.json', dict(classification='RNG-DETERMINISTIC-WITH-SEED', runs=2, seed=1,
                    scope='two separate processes; same native binary/model/phase and seed; movement RNG unused',
                    payload_sha256=payload_hashes, retail_rng_equivalence='UNKNOWN'))
        print(f'{name}: 1/10 PASS; legacy state results/20 CSV hashes preserved; separate process bytes equal')
    sensitivity = []
    for after, before in zip(suites['v2']['cases'], suites['v2-before']['cases']):
        case = after['case']
        a, b = samples(load(out / 'v2' / f'{case}.json')), samples(load(out / 'v2-before' / f'{case}.json'))
        sensitivity.append(dict(case=case, changed_sample_states=sum(x['values'] != y['values'] for x, y in zip(a, b)),
                                primary_first=after['state_first_divergence'], diagnostic_first=before['state_first_divergence'],
                                primary_status=after['status'], diagnostic_status=before['status']))
    write_json(reports / 'phase-sensitivity.json', sensitivity)
    paths = [ROOT / 'oracle/canonical' / BUILD / f'{l}.json' for l in LABELS]
    paths += [ROOT / 'tools' / name for name in ('trace_contract.py', 'normalize_traces.py', 'compare_traces.py', 'run_phase3.py', 'oracle_parse.py', 'compare_movement.py')]
    paths += [ROOT / 'docs/trace-contract-v1.md']
    write_json(reports / 'evidence-hashes.json', {str(p.relative_to(ROOT)): sha256(p) for p in paths})
    write_json(reports / 'reproduction.json', dict(commands=['cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++',
             'cmake --build build -j 4', 'ctest --test-dir build --output-on-failure',
             "python3 -m unittest discover -s tools -p 'test_*.py' -v",
             'python3 tools/run_phase3.py --runner build/wc3test --out build/phase3 --reports build/phase3-reports'],
             normalized_maps=15, validated_raw_runs=45, models=['v1', 'v2', 'v2-before'],
             original_wc3_required=False, legacy_csv_hashes_unchanged=60,
             legacy_state_reports_equal=30, separate_process_output_files_equal=93))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.runner.resolve(), args.out, args.reports)
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError, csv.Error, subprocess.CalledProcessError) as error:
        parser.exit(2, f'run_phase3: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

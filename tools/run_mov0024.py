#!/usr/bin/env python3
"""Reproduce MOV-0024 evidence and its frozen prediction verdicts; never refit."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from compare_traces import compare, verify_reference_provenance
from normalize_generated import normalize
from predict_mov0024 import LABELS, describe
from run_mov0013 import FIXTURES, regenerate, run_model
from trace_contract import ROOT, digest, load, payload, sha256, write_json

PREDICTIONS = ROOT / 'results/mov-0024/H0-predictions.json'
REVIEWED = ROOT / 'results/mov-0024/reviewed.json'


def predictions(name):
    base = load(ROOT / f'results/mov-0024/{name}-predictions.json')
    base['cases'].update(load(ROOT / f'results/mov-0024/f-valid-{name}-predictions.json')['cases'])
    return base


def candidate(label, reference):
    prediction = predictions('C96')['cases'][label]
    path = ROOT / prediction['trace']
    if sha256(path) != prediction['sha256'] or sha256(ROOT / prediction['scenario']) != prediction['scenario_sha256']:
        raise ValueError(f'{label}: candidate prediction changed')
    trace = load(path)
    return dict(comparison=signature(compare(reference, trace)), description=describe(trace))


def intervention(label, reference):
    from analyze_mov0018 import samples
    # Frozen starts are part of the preregistration. Check raw observations, not C++.
    starts = {'a': [(-500, 0), (500, 0)], 'b': [(-500, 0), (0, -500)],
              'c': [(-500, 0), (0, 0), (0, 0)], 'd': [(-500, 0), (0, 0), (0, 0)],
              'e': [(0, 500), (0, -500), (500, 0)],
              'f': [(-500, 0), (500, 0), (-32, 96)]}[label[-1]]
    units = samples(reference)
    initial = all(abs(units[f'u{i}'][0][1]-x) <= .001 and abs(units[f'u{i}'][0][2]-y) <= .001
                  for i, (x, y) in enumerate(starts))
    occupied = True
    if label[-1] in 'cd':
        occupied = all(abs(r[1]) <= .001 and abs(r[2]) <= .001 and r[4] == (851986 if label[-1] == 'c' else 0)
                       for r in units['u1'][1:]) and all(r[4] == 0 for r in units['u2'])
    if label.endswith('-f'):
        occupied = all(abs(units['u0'][i][1] + 30.222656) <= .001 and abs(units['u0'][i][2] - .012695) <= .001
                       and units['u0'][i][4] == (0 if i == 97 else 851986) for i in (88, 89, 90, 97))
    return dict(initial_positions=initial, occupant_state=occupied, status='PASS' if initial and occupied else 'INCONCLUSIVE')


def signature(comparison):
    """Pin the complete observed comparison, including first/per-unit divergences."""
    return {key: comparison[key] for key in (
        'status', 'properties', 'action_properties', 'event_properties',
        'structural_differences', 'first_divergence', 'unobserved_properties')}


def assess(comparison, expected):
    return signature(comparison) == expected


def verify_download(root, result, legacy=False):
    """Independently regrade downloaded CI artifacts, including negative verdicts."""
    if legacy and 'mov0024_required' not in result:
        return None
    if result.get('mov0024_required') is not True or result.get('mov0024', {}).get('status') != 'PASS':
        raise ValueError('required MOV-0024 gate missing, disabled or failing')
    report = load(root / 'reports/mov0024.json')
    if report['status'] != 'PASS' or [c['map_revision'] for c in report['cases']] != list(LABELS):
        raise ValueError('MOV-0024 report incomplete or failing')
    frozen_predictions, reviewed = predictions('H0'), load(REVIEWED)
    cpp = {}
    with tempfile.TemporaryDirectory() as temp:
        for row in report['cases']:
            label = row['map_revision']
            fixture = root / f'mov-0024/references/{label}.json'
            if fixture.read_bytes() != (FIXTURES / f'{label}.json').read_bytes():
                raise ValueError(f'{label}: downloaded WC3 fixture differs')
            reference = load(fixture)
            verify_reference_provenance(reference)
            actual = load(root / f'mov-0024/traces/{label}/MOV-0024.json')
            prediction = frozen_predictions['cases'][label]
            frozen_path = ROOT / prediction['trace']
            if sha256(frozen_path) != prediction['sha256'] or sha256(ROOT / prediction['scenario']) != prediction['scenario_sha256']:
                raise ValueError(f'{label}: frozen inputs changed')
            if reference['provenance']['scenario'] != actual['provenance']['scenario']:
                raise ValueError(f'{label}: downloaded scenario identity differs')
            frozen = load(frozen_path)
            if actual['identity']['model']['name'] != 'footman-v4' or digest(payload(actual)) != digest(payload(frozen)):
                raise ValueError(f'{label}: downloaded model no longer reproduces prediction')
            comparison = compare(reference, actual)
            expected = reviewed['cases'][label]
            reproduction = normalize(label, Path(temp))
            if (row['comparison'] != comparison or not assess(comparison, expected['comparison'])
                    or row['reproduction'] != reproduction or reproduction['status'] != 'PASS'
                    or row['wc3'] != describe(reference) or row['wc3'] != expected['wc3_description']
                    or row['cpp'] != describe(actual) or row['compatibility'] != comparison['status']
                    or row['rating'] != expected['rating'] or row['prediction_reproduced'] is not True
                    or row['candidate'] != candidate(label, reference) or row['candidate'] != expected['candidate']
                    or row['intervention'] != intervention(label, reference) or row['intervention'] != expected['intervention']
                    or row['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded grading does not reproduce')
            cpp[label] = digest(payload(actual))
    return dict(status='PASS', cases=6, cpp_payload_sha256=cpp)


def run(runner, codegen, out, reports):
    frozen_predictions, reviewed = predictions('H0'), load(REVIEWED)
    reports.mkdir(parents=True, exist_ok=True)
    cases = []
    for label in LABELS:
        prediction = frozen_predictions['cases'][label]
        scenario = prediction['scenario']
        frozen_path = ROOT / prediction['trace']
        if sha256(ROOT / scenario) != prediction['scenario_sha256'] or sha256(frozen_path) != prediction['sha256']:
            raise ValueError(f'{label}: preregistered scenario/prediction changed')
        regenerate(codegen, label, scenario)
        reproduction = normalize(label, out / 'references')
        fixture = out / 'references' / f'{label}.json'
        if fixture.read_bytes() != (FIXTURES / f'{label}.json').read_bytes():
            raise ValueError(f'{label}: retained fixture does not reproduce')
        reference, frozen = load(fixture), load(frozen_path)
        verify_reference_provenance(reference)
        dest = out / 'traces' / label
        run_model(runner, scenario, dest)
        with tempfile.TemporaryDirectory() as temp:
            run_model(runner, scenario, temp)
            if any(p.read_bytes() != (Path(temp) / p.name).read_bytes() for p in dest.iterdir()):
                raise ValueError(f'{label}: repeated C++ process differs')
        actual = load(dest / 'MOV-0024.json')
        if reference['provenance']['scenario'] != actual['provenance']['scenario']:
            raise ValueError(f'{label}: oracle/model scenario identity differs')
        if digest(payload(actual)) != digest(payload(frozen)):
            raise ValueError(f'{label}: model no longer reproduces frozen prediction')
        comparison = compare(reference, actual)
        frozen_comparison = compare(reference, frozen)
        expected = reviewed['cases'][label]
        ok = (reproduction['status'] == 'PASS' and assess(comparison, expected['comparison'])
              and assess(frozen_comparison, expected['comparison'])
              and describe(reference) == expected['wc3_description']
              and candidate(label, reference) == expected['candidate']
              and intervention(label, reference) == expected['intervention'])
        cases.append(dict(map_revision=label, status='PASS' if ok else 'FAIL',
                          compatibility=comparison['status'], rating=expected['rating'],
                          comparison=comparison, reproduction=reproduction,
                          prediction_reproduced=True, candidate=candidate(label, reference), intervention=intervention(label, reference), wc3=describe(reference), cpp=describe(actual)))
    status = 'PASS' if len(cases) == 6 and all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    write_json(reports / 'mov0024.json', dict(status=status,
               gate='retained evidence and frozen prediction verdicts; FAIL compatibility remains explicit', cases=cases))
    lines = ['# MOV-0024 regression', '', f'Evidence regression: **{status}**.', '',
             '| Variant | Canonical compatibility | Rating | First divergence |', '|---|---|---|---|']
    for c in cases:
        lines.append(f"| {c['map_revision']} | {c['compatibility']} | {c['rating']} | {c['comparison']['first_divergence']} |")
    (reports / 'mov0024.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print('MOV-0024 evidence regression ' + status + ': ' + '; '.join(
        f"{c['map_revision']} compatibility {c['compatibility']} ({c['rating']})" for c in cases))
    return int(status != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ext = '.exe' if os.name == 'nt' else ''
    parser.add_argument('--runner', type=Path, default=ROOT / f'build/wc3test{ext}')
    parser.add_argument('--codegen', type=Path, default=ROOT / f'build/oracle_codegen{ext}')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    args = parser.parse_args()
    try:
        return run(args.runner, args.codegen, args.out, args.reports)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_mov0024: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

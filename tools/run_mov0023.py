#!/usr/bin/env python3
"""Reproduce MOV-0023 evidence and its frozen prediction verdicts; never refit."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from compare_traces import compare, verify_reference_provenance
from normalize_generated import normalize
from predict_mov0023 import LABELS, describe
from run_mov0013 import FIXTURES, regenerate, run_model
from trace_contract import ROOT, digest, load, payload, sha256, write_json

PREDICTIONS = ROOT / 'results/mov-0023/predictions.json'
REVIEWED = ROOT / 'results/mov-0023/reviewed.json'


def signature(comparison):
    """Pin the complete observed comparison, including first/per-unit divergences."""
    return {key: comparison[key] for key in (
        'status', 'properties', 'action_properties', 'event_properties',
        'structural_differences', 'first_divergence', 'unobserved_properties')}


def assess(comparison, expected):
    return signature(comparison) == expected


def verify_download(root, result, legacy=False):
    """Independently regrade downloaded CI artifacts, including negative verdicts."""
    if legacy and 'mov0023_required' not in result:
        return None
    if result.get('mov0023_required') is not True or result.get('mov0023', {}).get('status') != 'PASS':
        raise ValueError('required MOV-0023 gate missing, disabled or failing')
    report = load(root / 'reports/mov0023.json')
    if report['status'] != 'PASS' or [c['map_revision'] for c in report['cases']] != list(LABELS):
        raise ValueError('MOV-0023 report incomplete or failing')
    predictions, reviewed = load(PREDICTIONS), load(REVIEWED)
    cpp = {}
    with tempfile.TemporaryDirectory() as temp:
        for row in report['cases']:
            label = row['map_revision']
            fixture = root / f'mov-0023/references/{label}.json'
            if fixture.read_bytes() != (FIXTURES / f'{label}.json').read_bytes():
                raise ValueError(f'{label}: downloaded WC3 fixture differs')
            reference = load(fixture)
            verify_reference_provenance(reference)
            actual = load(root / f'mov-0023/traces/{label}/MOV-0023.json')
            prediction = predictions['cases'][label]
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
                    or row['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded grading does not reproduce')
            cpp[label] = digest(payload(actual))
    return dict(status='PASS', cases=4, cpp_payload_sha256=cpp)


def run(runner, codegen, out, reports):
    predictions, reviewed = load(PREDICTIONS), load(REVIEWED)
    reports.mkdir(parents=True, exist_ok=True)
    cases = []
    for label in LABELS:
        prediction = predictions['cases'][label]
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
        actual = load(dest / 'MOV-0023.json')
        if reference['provenance']['scenario'] != actual['provenance']['scenario']:
            raise ValueError(f'{label}: oracle/model scenario identity differs')
        if digest(payload(actual)) != digest(payload(frozen)):
            raise ValueError(f'{label}: model no longer reproduces frozen prediction')
        comparison = compare(reference, actual)
        frozen_comparison = compare(reference, frozen)
        expected = reviewed['cases'][label]
        ok = (reproduction['status'] == 'PASS' and assess(comparison, expected['comparison'])
              and assess(frozen_comparison, expected['comparison'])
              and describe(reference) == expected['wc3_description'])
        cases.append(dict(map_revision=label, status='PASS' if ok else 'FAIL',
                          compatibility=comparison['status'], rating=expected['rating'],
                          comparison=comparison, reproduction=reproduction,
                          prediction_reproduced=True, wc3=describe(reference), cpp=describe(actual)))
    status = 'PASS' if len(cases) == 4 and all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    write_json(reports / 'mov0023.json', dict(status=status,
               gate='retained evidence and frozen prediction verdicts; FAIL compatibility remains explicit', cases=cases))
    lines = ['# MOV-0023 regression', '', f'Evidence regression: **{status}**.', '',
             '| Variant | Canonical compatibility | Rating | First divergence |', '|---|---|---|---|']
    for c in cases:
        lines.append(f"| {c['map_revision']} | {c['compatibility']} | {c['rating']} | {c['comparison']['first_divergence']} |")
    (reports / 'mov0023.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print('MOV-0023 evidence regression ' + status + ': ' + '; '.join(
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
        parser.exit(2, f'run_mov0023: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

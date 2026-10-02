#!/usr/bin/env python3
"""Regrade a retained unattended evidence bundle offline; no WC3 or VM required."""
import argparse
import os
from pathlib import Path
import subprocess

from compare_traces import compare
from generate_oracle import generate
from normalize_generated import normalize
from trace_contract import ROOT, BUILD, load, sha256, write_json

BUNDLES = ROOT / 'results/phase-7/captures'
REVISIONS = ('MOV-0002-g3', 'MOV-0004-g3', 'MOV-0006-g3', 'MOV-0010-g3')


def regrade(bundle, runner, codegen, out):
    report = load(bundle / 'report.json')
    label = report['reproduction']['map_revision']
    scenario = report['reproduction']['scenario']
    journal = load(bundle / 'diagnostics/journal.json')
    if (report['status'] != 'PASS' or report['capture'] != 'VALIDATED' or report['canonical_promotion'] is not False
            or journal['status'] != 'PASS' or journal['intervention_count'] != 0
            or any(p['status'] != 'stopped' for p in journal['owned_processes'])):
        raise ValueError('bundle lacks successful unattended capture/cleanup evidence')
    manifest = load(bundle / f'oracle/captures/{BUILD}/{label}/manifest.json')
    owned = journal['owned_processes']
    games = [p for p in owned if p['role'].startswith('game-')]
    if (len(owned) != len(manifest['runs']) + 1 or len(games) != len(manifest['runs'])
            or len({(p['pid'], p['start']) for p in owned}) != len(owned)
            or [p['role'] for p in games] != [f'game-{r["run"]}' for r in manifest['runs']]
            or [p['pid'] for p in games] != [r['game_pid'] for r in manifest['runs']]):
        raise ValueError('fresh-process launch/cleanup receipts differ from raw-run manifest')
    files, _ = generate(codegen, [bundle / scenario['path']], label)
    case = bundle / f'oracle/generated/maps/{label}.j'
    if files[label + '.j'] != case.read_bytes():
        raise ValueError('case does not reproduce from exact scenario bytes')
    reproduced = normalize(label, out / 'candidate', bundle)
    reference = out / 'candidate' / f'{label}.json'
    retained = bundle / report['candidate']
    if reproduced != report['reproduction'] or reproduced['status'] != 'PASS' or reference.read_bytes() != retained.read_bytes():
        raise ValueError('candidate/reproduction does not reproduce from raw evidence')
    actual = out / 'cpp'
    result = subprocess.run([str(runner.resolve()), '--model', 'v4', '--seed', '1', '--scenario', scenario['path'],
                             '--out', str(actual.resolve())], cwd=bundle, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr)
    comparison = compare(load(reference), load(actual / f'{Path(scenario["path"]).stem}.json'), bundle)
    status = 'PASS' if comparison['status'] == 'PASS' else 'FAIL'
    result = dict(status=status, map_revision=label, reproduction=reproduced, comparison=comparison,
                  retained_report_sha256=sha256(bundle / 'report.json'), retained_candidate_sha256=sha256(retained))
    write_json(out / 'regrade.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / ('wc3test.exe' if os.name == 'nt' else 'wc3test'))
    parser.add_argument('--codegen', type=Path, default=ROOT / 'build' / ('oracle_codegen.exe' if os.name == 'nt' else 'oracle_codegen'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists(): raise ValueError('output exists; use a new directory')
        result = regrade(args.bundle.resolve(), args.runner, args.codegen, args.out)
        print(f'{result["map_revision"]}: {result["status"]}')
        return int(result['status'] != 'PASS')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, f'regrade_capture: {error}\n')


if __name__ == '__main__': raise SystemExit(main())

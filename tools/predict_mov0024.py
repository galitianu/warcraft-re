#!/usr/bin/env python3
"""Freeze unchanged-model MOV-0024 predictions; reads no WC3 capture."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from analyze_mov0018 import samples, targets, describe_unit
from trace_contract import ROOT, load, sha256, write_json

LABELS = tuple(f'MOV-0024-{v}' for v in 'abcdef')


def describe(trace):
    """Describe every pair, without selecting a privileged blocker from three units."""
    units, goals = samples(trace), targets(trace)
    result = {}
    for name, rows in units.items():
        pairs = {other: describe_unit(rows, other_rows, goals.get(name))
                 for other, other_rows in units.items() if other != name}
        common = next(iter(pairs.values()))
        result[name] = {k: v for k, v in common.items()
                        if k not in ('passes_other_on', 'closest_approach')}
        result[name]['pairs'] = {other: {k: value[k] for k in ('passes_other_on', 'closest_approach') if k in value}
                                for other, value in pairs.items()}
    # A later-issued move starts an observation window after its ACTION callback.
    # For initial orders this leaves the frozen a-e descriptions unchanged.
    for name, value in result.items():
        actions = [r for r in trace['records'] if r['kind'] == 'ACTION' and r.get('unit') == name and r.get('command') == 'move']
        if actions and actions[0]['callback'] > 0:
            value['arrival_callback'] = next((r[0] for r in units[name] if r[0] > actions[0]['callback'] and r[4] == 0), None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--name', required=True, choices=['H0', 'C96'])
    parser.add_argument('--supplement-f', action='store_true')
    parser.add_argument('--manifest-prefix', default=None)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    cases = {}
    for label in (('MOV-0024-f',) if args.supplement_f else LABELS):
        scenario = Path(f'scenarios/MOV-0024/{label}.yaml')
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(args.runner.resolve()), '--model', 'v4', '--scenario', str(scenario),
                            '--out', temp], cwd=ROOT, check=True, capture_output=True)
            source = Path(temp) / 'MOV-0024.json'
            trace = load(source)
            destination = args.out / f'{label}.json'
            shutil.copyfile(source, destination)
            shutil.copyfile(Path(temp) / 'identity.json', args.out / f'{label}-identity.json')
            cases[label] = dict(scenario=str(scenario), scenario_sha256=sha256(ROOT / scenario),
                                trace=str(destination.relative_to(ROOT)), sha256=sha256(destination),
                                description=describe(trace), build=trace['identity']['build'])
            print(label, {u: (d.get('arrival_callback'), d.get('waits')) for u, d in cases[label]['description'].items()})
    write_json(args.out.parent / ((args.manifest_prefix if args.manifest_prefix is not None else ('f-' if args.supplement_f else '')) + args.name + '-predictions.json'), dict(model=args.name,
               runner_sha256=sha256(args.runner), method='tools/predict_mov0024.py', cases=cases))


if __name__ == '__main__':
    main()

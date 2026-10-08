#!/usr/bin/env python3
"""Freeze unchanged-model MOV-0023 predictions; reads no WC3 capture."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from analyze_mov0018 import samples, targets, describe_unit
from trace_contract import ROOT, load, sha256, write_json

LABELS = tuple(f'MOV-0023-{v}' for v in 'abcd')


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
        result[name]['pairs'] = {other: {k: value[k] for k in ('passes_other_on', 'closest_approach')}
                                for other, value in pairs.items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    cases = {}
    for label in LABELS:
        scenario = Path(f'scenarios/MOV-0023/{label}.yaml')
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(args.runner.resolve()), '--model', 'v4', '--scenario', str(scenario),
                            '--out', temp], cwd=ROOT, check=True, capture_output=True)
            source = Path(temp) / 'MOV-0023.json'
            trace = load(source)
            destination = args.out / f'{label}.json'
            shutil.copyfile(source, destination)
            shutil.copyfile(Path(temp) / 'identity.json', args.out / f'{label}-identity.json')
            cases[label] = dict(scenario=str(scenario), scenario_sha256=sha256(ROOT / scenario),
                                trace=str(destination.relative_to(ROOT)), sha256=sha256(destination),
                                description=describe(trace), build=trace['identity']['build'])
            print(label, {u: (d['arrival_callback'], d['waits']) for u, d in cases[label]['description'].items()})
    write_json(args.out.parent / 'predictions.json', dict(model='unchanged footman-v4',
               runner_sha256=sha256(args.runner), method='tools/predict_mov0023.py', cases=cases))


if __name__ == '__main__':
    main()

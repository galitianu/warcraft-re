#!/usr/bin/env python3
"""Freeze MOV-0026 unchanged-model predictions and describe observed stop transitions."""
import argparse
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from analyze_mov0018 import samples
from predict_mov0024 import describe
from trace_contract import ROOT, load, sha256, write_json

LABELS = tuple(f'MOV-0026-{v}' for v in 'abcd')
STOPS = dict(zip(LABELS, (90, 96, 80, 96)))
TOLERANCE = .001


def transition(trace, label):
    """Samples bracket the ACTION; relocation timing within that 20 ms is unobserved."""
    units = samples(trace)
    k = STOPS[label]
    before, after = units['u0'][k], units['u0'][k+1]
    window = units['u0'][k-2:k+1]
    delta = [after[i] - before[i] for i in (1, 2)]
    still = all(abs(row[i] - before[i]) <= TOLERANCE for row in window for i in (1, 2))
    ordered = all(row[4] == 851986 for row in window)
    shift = 16 if label.endswith('-d') else 0
    starts = [(-500+shift, shift), (500+shift, shift)]
    initial = all(abs(units[f'u{n}'][0][i+1] - value) <= TOLERANCE
                  for n, start in enumerate(starts) for i, value in enumerate(start))
    stationary_expected = not label.endswith('-c')
    setup = initial and ordered and still == stationary_expected
    # Centers have coordinate 16 modulo 32. Use the shortest distance, including negatives.
    grid_error = [abs((after[i] - 16) - 32 * round((after[i] - 16) / 32)) for i in (1, 2)]
    in_place = all(abs(d) <= TOLERANCE for d in delta)
    grid = all(d <= TOLERANCE for d in grid_error)
    idle = after[4] == 0
    stable = all(abs(row[i] - after[i]) <= TOLERANCE and row[4] == 0
                 for row in units['u0'][k+1:] for i in (1, 2))
    predictions = dict(stop_in_place=in_place and idle,
                       blocked_grid=(grid and not in_place if stationary_expected else in_place) and idle,
                       unconditional_grid=grid and idle)
    return dict(callback=k, pre=list(before), post=list(after), delta_xy=delta,
                displacement=math.hypot(*delta), grid_center_error=grid_error,
                initial_positions_match=initial, pre_stop_stationary=still,
                pre_stop_move_order=ordered, setup='PASS' if setup else 'INCONCLUSIVE',
                post_stop_idle=idle, stopped_position_stable=stable,
                hypotheses={name: ('SURVIVES' if passed else 'REFUTED') if setup else 'INCONCLUSIVE'
                            for name, passed in predictions.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    cases = {}
    for label in LABELS:
        scenario = Path(f'scenarios/MOV-0026/{label}.yaml')
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([str(args.runner.resolve()), '--model', 'v4', '--scenario', str(scenario),
                            '--out', temp], cwd=ROOT, check=True, capture_output=True)
            source = Path(temp) / 'MOV-0026.json'
            trace = load(source)
            destination = args.out / f'{label}.json'
            shutil.copyfile(source, destination)
            shutil.copyfile(Path(temp) / 'identity.json', args.out / f'{label}-identity.json')
            cases[label] = dict(scenario=str(scenario), scenario_sha256=sha256(ROOT / scenario),
                                trace=str(destination.relative_to(ROOT)), sha256=sha256(destination),
                                description=describe(trace), transition=transition(trace, label),
                                build=trace['identity']['build'])
            print(label, cases[label]['transition'])
    write_json(args.out.parent / 'predictions.json', dict(model='footman-v4 unchanged',
               runner_sha256=sha256(args.runner), method='tools/predict_mov0026.py', cases=cases))


if __name__ == '__main__':
    main()

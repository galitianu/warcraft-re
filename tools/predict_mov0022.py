#!/usr/bin/env python3
"""MOV-0022 (docs/mov-0022.md): pre-register the retail pathing mechanism on new layouts.

Writes the variant scenarios and predictions.json. Each variant's prediction is the
footman-v4 trace itself (stored under predicted/ with its digest), plus its P3
description. Reads no MOV-0022 capture.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from predict_mov0019 import summary, targets_of
from predict_mov0020 import waiting
from trace_contract import ROOT, load, sha256, write_json

EXT = '.exe' if os.name == 'nt' else ''
# label -> (purpose, units (x, y, facing, move speed or None), orders (unit, target) in issue order)
VARIANTS = {
    'MOV-0022-a': ('head-on, the eastward unit faster (300 against 270)',
                   [(0, 0, 0, 300), (1000, 0, 180, None)], [(0, (1000, 0)), (1, (0, 0))]),
    'MOV-0022-b': ('a with the speeds swapped: the westward unit faster',
                   [(0, 0, 0, None), (1000, 0, 180, 300)], [(0, (1000, 0)), (1, (0, 0))]),
    'MOV-0022-c': ('a with the orders issued in the other order',
                   [(0, 0, 0, 300), (1000, 0, 180, None)], [(1, (0, 0)), (0, (1000, 0))]),
    'MOV-0022-d': ('MOV-0019-i with a slower crossing unit (200)',
                   [(0, 0, 0, None), (500, -380, 90, 200)], [(0, (1000, 0)), (1, (500, 620))]),
    'MOV-0022-e': ('a diagonal past an idle unit on the line',
                   [(0, 0, 45, None), (500, 500, 0, None)], [(0, (1000, 1000))]),
    'MOV-0022-f': ('a fast unit overtaking a slow one on its line (400 and 150)',
                   [(0, 0, 0, 400), (200, 0, 0, 150)], [(0, (1200, 0)), (1, (1000, 0))]),
}


def variant_text(label):
    purpose, units, orders = VARIANTS[label]
    lines = [f'# MOV-0022: {purpose}', '# Semantics: docs/scenario-v1.md.', 'schema: wc3-scenario', 'version: 1',
             'experiment: MOV-0022', f'map_revision: {label}', 'units:']
    for i, (x, y, facing, speed) in enumerate(units):
        lines += [f'  - name: u{i}', '    type: hfoo', f'    position: [{x}, {y}]', f'    facing: {facing}']
        if speed is not None:
            lines.append(f'    move_speed: {speed}')
    lines += ['observe:', '  period: 0.02', '  callbacks: 600', '  properties: [x, "y", facing, order]', 'actions:']
    for unit, (x, y) in orders:
        lines += ['  - at: 0', f'    unit: u{unit}', '    order: move', f'    target: [{x}, {y}]']
    return '\n'.join(lines + ['...']) + '\n'


def samples(trace):
    units = {}
    for r in trace['records']:
        if r['kind'] == 'SAMPLE':
            v = r['values']
            units.setdefault(r['unit'], []).append(
                (r['callback'], float(v['x']), float(v['y']), float(v['facing']), int(v['order'])))
    return units


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3test{EXT}')
    parser.add_argument('--out', type=Path, required=True, help='results directory')
    parser.add_argument('--scenarios', type=Path, required=True, help='write the scenarios here (never overwrites)')
    args = parser.parse_args()
    args.scenarios.mkdir(parents=True, exist_ok=True)
    (args.out / 'predicted').mkdir(parents=True, exist_ok=True)
    variants = {}
    for label in VARIANTS:
        path = args.scenarios / f'{label}.yaml'
        text = variant_text(label)
        if path.exists() and path.read_text() != text:
            raise SystemExit(f'{path} exists with different bytes; refusing to overwrite')
        path.write_text(text, newline='\n')
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([str(args.runner), '--model', 'v4', '--scenario', str(path.resolve().relative_to(ROOT)),
                            '--out', tmp], cwd=ROOT, check=True, capture_output=True)
            predicted = args.out / 'predicted' / f'{label}.json'
            write_json(predicted, load(Path(tmp) / 'MOV-0022.json'), compact_records=True)
        model = summary(samples(load(predicted)), targets_of(path))
        variants[label] = dict(question=VARIANTS[label][0], trace=str(predicted.resolve().relative_to(ROOT)),
                               sha256=sha256(predicted), model=model, model_waits=waiting(model))
        print(label, model)
    write_json(args.out / 'predictions.json',
               dict(method='tools/predict_mov0022.py', model='footman-v4 with the retail pathing mechanism',
                    variants=variants))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

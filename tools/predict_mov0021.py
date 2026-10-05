#!/usr/bin/env python3
"""MOV-0021 (docs/mov-0021.md): pre-register who waits head-on with a lateral offset.

In the offset head-ons (MOV-0019-j, MOV-0020-b, d) the eastward unit waits, but in the
unoffset MOV-0018-b the westward one waits longest. Three hypotheses name the unit that
waits in each variant:

- heading: the unit whose heading is the smaller angle anticlockwise from east;
- rotation: the outcome turns with the layout, so the image of j's eastward unit waits;
- line: the unit on the lower travel line (lower y; lower x for north-south travel).

Writes the variant scenarios and predictions.json: each hypothesis's waiting unit and
the current footman-v4 model's P3 description of every variant. Reads no MOV-0021 capture.

Historical: the model runs used tools/wc3pathing and the fitted heuristic pathing, both
removed when the retail mechanism replaced them; predictions.json is the record.
"""
import argparse
import json
import os
from pathlib import Path

from predict_mov0019 import KEYS, run_sets, scenario_text, summary, targets_of
from predict_mov0020 import LONG_WAIT_CALLBACKS, waiting
from trace_contract import ROOT, write_json

EXT = '.exe' if os.name == 'nt' else ''
# label -> (purpose, units (x, y, facing) -> target in creation and order of issue,
#           the unit each hypothesis names). u0 is always the image of j's eastward unit.
VARIANTS = {
    'MOV-0021-a': ('MOV-0019-j mirrored: the westward unit 32 south',
                   [((0, 0, 0), (1000, 0)), ((1000, -32, 180), (0, -32))],
                   dict(heading='u0', rotation='u0', line='u1')),
    'MOV-0021-b': ('MOV-0019-j turned 90 degrees anticlockwise: north and south',
                   [((0, 0, 90), (0, 1000)), ((-32, 1000, 270), (-32, 0))],
                   dict(heading='u0', rotation='u0', line='u1')),
    'MOV-0021-c': ('MOV-0019-j turned 90 degrees clockwise: south and north',
                   [((0, 0, 270), (0, -1000)), ((32, -1000, 90), (32, 0))],
                   dict(heading='u1', rotation='u0', line='u0')),
    'MOV-0021-d': ('b mirrored: the southward unit 32 east',
                   [((0, 0, 90), (0, 1000)), ((32, 1000, 270), (32, 0))],
                   dict(heading='u0', rotation='u0', line='u0')),
    'MOV-0021-e': ('MOV-0019-j without partial routes: no target covered at its order',
                   [((0, 0, 0), (1000, 0)), ((1100, 32, 180), (100, 32))],
                   dict(heading='u0', rotation='u0', line='u0')),
    'MOV-0021-f': ('e mirrored: the westward unit 32 south',
                   [((0, 0, 0), (1000, 0)), ((1100, -32, 180), (100, -32))],
                   dict(heading='u0', rotation='u0', line='u1')),
}


def variant_text(label):
    purpose, units, _ = VARIANTS[label]
    return scenario_text(label, purpose, [start for start, _ in units], list(enumerate(t for _, t in units)),
                         experiment='MOV-0021')


def hypotheses(label):
    return dict(VARIANTS[label][2])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3pathing{EXT}')
    parser.add_argument('--out', type=Path, required=True, help='predictions.json')
    parser.add_argument('--scenarios', type=Path, required=True, help='write the scenarios here (never overwrites)')
    args = parser.parse_args()
    args.scenarios.mkdir(parents=True, exist_ok=True)
    adopted = dict(line_clearance=4, waypoint_radius=16, block_radius=62, block_lookahead=32,
                   block_lateral=40, recheck_updates=5)
    variants = {}
    for label in VARIANTS:
        path = args.scenarios / f'{label}.yaml'
        text = variant_text(label)
        if path.exists() and path.read_text() != text:
            raise SystemExit(f'{path} exists with different bytes; refusing to overwrite')
        path.write_text(text, newline='\n')
        units = next(run_sets(args.runner, path, [adopted]))
        model = json.loads(json.dumps(summary(units, targets_of(path))))
        variants[label] = dict(question=VARIANTS[label][0], hypotheses=hypotheses(label),
                               model=model, model_waits=waiting(model))
        print(label, variants[label]['hypotheses'], 'model waits:', variants[label]['model_waits'])
    write_json(args.out, dict(method='tools/predict_mov0021.py',
                              model='footman-v4 at the MOV-0020 post-hoc give-way refit (give_way_updates 20)',
                              parameters={k: adopted[k] for k in KEYS}, long_wait_callbacks=LONG_WAIT_CALLBACKS,
                              variants=variants))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

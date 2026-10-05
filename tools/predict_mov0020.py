#!/usr/bin/env python3
"""MOV-0020 (docs/mov-0020.md): pre-register who gives way when the units' roles swap.

In every MOV-0018/0019 crossing, u0 (created and ordered first, travelling east) is the
unit that waits. Three hypotheses name the unit that waits in each variant:

- index: the lower-index unit (u0);
- order: the unit ordered first;
- role: the unit travelling east, the role that waited in every earlier capture.

Writes the variant scenarios and predictions.json: each hypothesis's waiting unit and
the current footman-v4 model's P3 description of every variant. Reads no MOV-0020 capture.

Historical: the model runs used tools/wc3pathing and the fitted heuristic pathing, both
removed when the retail mechanism replaced them; predictions.json is the record.
"""
import argparse
import json
import os
from pathlib import Path

from predict_mov0019 import KEYS, run_sets, scenario_text, summary, targets_of
from trace_contract import ROOT, write_json

EXT = '.exe' if os.name == 'nt' else ''
# Roles: (x, y, facing) start and move target.
EAST = ((0, 0, 0), (1000, 0))
CROSS_I = ((500, -540, 90), (500, 460))   # MOV-0019-i's u1
CROSS_G = ((500, -440, 90), (500, 560))   # MOV-0019-g's u1
CROSS_C = ((500, -500, 90), (500, 500))   # MOV-0018-c's u1
WEST = ((1000, 32, 180), (0, 32))         # MOV-0019-j's u1
# label -> (purpose, roles in creation order (u0, u1), role names, order issue order by unit index)
VARIANTS = {
    'MOV-0020-a': ('MOV-0019-i with the units swapped: u0 crosses north, u1 travels east', (CROSS_I, EAST), ('cross', 'east'), (0, 1)),
    'MOV-0020-b': ('MOV-0019-j with the units swapped: u0 travels west, u1 east', (WEST, EAST), ('west', 'east'), (0, 1)),
    'MOV-0020-c': ('MOV-0019-i with u1 ordered first', (EAST, CROSS_I), ('east', 'cross'), (1, 0)),
    'MOV-0020-d': ('MOV-0019-j with u1 ordered first', (EAST, WEST), ('east', 'west'), (1, 0)),
    'MOV-0020-e': ('MOV-0018-c with the units swapped: u0 crosses north, u1 travels east', (CROSS_C, EAST), ('cross', 'east'), (0, 1)),
    'MOV-0020-f': ('MOV-0019-g with the units swapped: u0 crosses north, u1 travels east', (CROSS_G, EAST), ('cross', 'east'), (0, 1)),
}
# A wait of at least 5 updates (7 callbacks): earlier captures held 10-20 updates while
# giving way, and 1-2 updates while replanning.
LONG_WAIT_CALLBACKS = 7


def variant_text(label):
    purpose, roles, _, order = VARIANTS[label]
    return scenario_text(label, purpose, [start for start, _ in roles], [(u, roles[u][1]) for u in order],
                         experiment='MOV-0020')


def hypotheses(label):
    _, _, names, order = VARIANTS[label]
    return dict(index='u0', order=f'u{order[0]}', role=f'u{names.index("east")}')


def waiting(description):
    """The units with a wait of at least LONG_WAIT_CALLBACKS callbacks."""
    return sorted(u for u, d in description.items()
                  if any(last - first >= LONG_WAIT_CALLBACKS for first, last in d.get('waits', [])))


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
        variants[label] = dict(question=VARIANTS[label][0], roles=dict(zip(('u0', 'u1'), VARIANTS[label][2])),
                               ordered_first=f'u{VARIANTS[label][3][0]}', hypotheses=hypotheses(label),
                               model=model, model_waits=waiting(model))
        print(label, variants[label]['hypotheses'], 'model waits:', variants[label]['model_waits'])
    write_json(args.out, dict(method='tools/predict_mov0020.py', model='footman-v4 at the MOV-0019 post-hoc refit',
                              parameters={k: adopted[k] for k in KEYS}, long_wait_callbacks=LONG_WAIT_CALLBACKS,
                              variants=variants))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""MOV-0019 (docs/mov-0019.md): fit the unit-pathing candidates and predict new layouts.

1. Runs every parameter set of a grid (tools/wc3pathing) on the four MOV-0018
   scenarios and keeps the sets whose P3 description equals WC3's in every variant:
   side, waits (first and last callback), arrival callback and final position within
   1 unit. These are the candidates the MOV-0018 captures cannot tell apart.
2. Runs each candidate on the MOV-0019 variants and records, per variant, every
   distinct predicted description and which candidates predict it.

Writes the variant scenarios and predictions.json. Nothing here reads a MOV-0019 capture.
"""
import argparse
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile

from analyze_mov0018 import describe_unit
from trace_contract import ROOT, load, write_json

EXT = '.exe' if os.name == 'nt' else ''
# The grid around the adopted values (4, 16, 62, 32, 40, 5). line_clearance and
# waypoint_radius stay fixed: MOV-0018 bounds them geometrically (docs/mov-0018.md).
GRID = dict(block_radius=range(50, 75), block_lookahead=range(16, 50, 2),
            block_lateral=range(34, 47), recheck_updates=range(2, 9))
FIXED = dict(line_clearance=4, waypoint_radius=16)
ADOPTED = dict(block_radius=62, block_lookahead=32, block_lateral=40, recheck_updates=5)
KEYS = ('line_clearance', 'waypoint_radius', 'block_radius', 'block_lookahead', 'block_lateral', 'recheck_updates')


def scenario_text(label, purpose, units, orders):
    """A v1 scenario in the committed MOV-0018 form; units are (x, y, facing)."""
    lines = [f'# MOV-0019: {purpose}', '# Semantics: docs/scenario-v1.md.', 'schema: wc3-scenario', 'version: 1',
             'experiment: MOV-0019', f'map_revision: {label}', 'units:']
    for i, (x, y, facing) in enumerate(units):
        lines += [f'  - name: u{i}', '    type: hfoo', f'    position: [{x}, {y}]', f'    facing: {facing}']
    lines += ['observe:', '  period: 0.02', '  callbacks: 600', '  properties: [x, "y", facing, order]', 'actions:']
    for unit, (x, y) in orders:
        lines += ['  - at: 0', f'    unit: u{unit}', '    order: move', f'    target: [{x}, {y}]']
    return '\n'.join(lines + ['...']) + '\n'


def run_sets(runner, scenario, sets, chunk=400):
    """Per parameter set: {unit: [(callback, x, y, facing, order)]}, in order."""
    for first in range(0, len(sets), chunk):
        yield from run_chunk(runner, scenario, sets[first:first + chunk])


def run_chunk(runner, scenario, sets):
    lines = ''.join(' '.join(str(s[k]) for k in KEYS) + '\n' for s in sets)
    out = subprocess.run([str(runner), str(scenario)], input=lines, capture_output=True, text=True,
                         check=True, timeout=3600).stdout
    runs = []
    for line in out.splitlines():
        if line.startswith('# set'):
            runs.append({})
        elif not line.startswith('callback'):
            cb, _, unit, x, y, facing, order = line.split(',')
            runs[-1].setdefault(unit, []).append((int(cb), float(x), float(y), float(facing), int(order)))
    if len(runs) != len(sets):
        raise ValueError(f'{scenario}: {len(runs)} runs for {len(sets)} parameter sets')
    return runs


def summary(units, targets):
    """The P3 description per unit: side, waits, arrival and final position (0.1 units)."""
    out = {}
    for name, rows in units.items():
        d = describe_unit(rows, units['u1' if name == 'u0' else 'u0'], targets.get(name))
        out[name] = dict(final=[round(d['final']['x'], 1), round(d['final']['y'], 1), d['final']['order']])
        if d['ordered']:
            out[name].update(side=d['passes_other_on'], arrival=d['arrival_callback'],
                             waits=[[w['first'], w['last']] for w in d['waits']],
                             deviation=round(d['largest_sideways_deviation']['units'], 1))
    return out


def matches(wc3, cpp):
    for name, ref in wc3.items():
        act = cpp[name]
        if abs(ref['final'][0] - act['final'][0]) > 1 or abs(ref['final'][1] - act['final'][1]) > 1 \
                or ref['final'][2] != act['final'][2]:
            return False
        if 'side' in ref and (ref['side'], ref['arrival'], ref['waits']) != (act['side'], act['arrival'], act['waits']):
            return False
    return True


def wc3_summary(label):
    trace = load(ROOT / 'oracle/canonical-generated/wc3-1.29.2-9231-x86' / f'{label}.json')
    units = {}
    for r in trace['records']:
        if r['kind'] == 'SAMPLE':
            v = r['values']
            units.setdefault(r['unit'], []).append(
                (r['callback'], float(v['x']), float(v['y']), float(v['facing']), int(v['order'])))
    goals = {r['unit']: (float(r['target']['x']), float(r['target']['y']))
             for r in trace['records'] if r['kind'] == 'ACTION'}
    return summary(units, goals)


def candidates(runner):
    sets = [dict(FIXED, **dict(zip(GRID, values))) for values in itertools.product(*GRID.values())]
    keep = [True] * len(sets)
    # The dynamic variants first: they reject most sets.
    for label in ('MOV-0018-c', 'MOV-0018-b', 'MOV-0018-a', 'MOV-0018-d'):
        scenario = ROOT / 'scenarios/MOV-0018' / f'{label}.yaml'
        reference, goals = wc3_summary(label), targets_of(scenario)
        live = [i for i, k in enumerate(keep) if k]
        for i, units in zip(live, run_sets(runner, scenario, [sets[i] for i in live])):
            keep[i] = matches(reference, summary(units, goals))
    return [s for s, k in zip(sets, keep) if k], len(sets)


def targets_of(scenario):
    """Move targets from a v1 scenario written by scenario_text or committed for MOV-0018."""
    text = Path(scenario).read_text().split('actions:')[1]
    found = {}
    for block in text.split('  - at:')[1:]:
        unit = block.split('unit: ')[1].split('\n')[0]
        x, y = block.split('target: [')[1].split(']')[0].split(',')
        found[unit] = (float(x), float(y))
    return found


# Layouts explored before choosing the variants (printed with --explore). u0 always
# starts at the origin facing its target; units are (x, y, facing).
EXPLORED = {
    **{f'blocker y={y}': ((0, 0, 0), (500, y, 180), [(0, (1000, 0))]) for y in (-40, -24, -8, 8, 40)},
    'tie west': ((1000, 0, 180), (500, 0, 0), [(0, (0, 0))]),
    'tie north': ((0, 0, 90), (0, 500, 270), [(0, (0, 1000))]),
    **{f'cross start y={-500 + d}': ((0, 0, 0), (500, -500 + d, 90), [(0, (1000, 0)), (1, (500, 500 + d))])
       for d in range(-120, 121, 20)},
    **{f'head-on k={k}': ((0, 0, 0), (1000, k, 180), [(0, (1000, 0)), (1, (0, k))]) for k in (16, 32, 48, 64)},
}
# The MOV-0019 variants (docs/mov-0019.md#design): label -> (question, explored layout).
VARIANTS = {
    'MOV-0019-a': ('footprint: idle blocker at (500, -40), one cell row below u0\'s line', 'blocker y=-40'),
    'MOV-0019-b': ('footprint: idle blocker at (500, -24), cell row -1', 'blocker y=-24'),
    'MOV-0019-c': ('footprint: idle blocker at (500, -8), the same cell as b', 'blocker y=-8'),
    'MOV-0019-d': ('footprint: idle blocker at (500, 40), cell row 1', 'blocker y=40'),
    'MOV-0019-e': ('tie order: centred idle blocker, u0 travelling west', 'tie west'),
    'MOV-0019-f': ('tie order: centred idle blocker, u0 travelling north', 'tie north'),
    'MOV-0019-g': ('wait corridor: crossing, u1 (500, -440) -> (500, 560)', 'cross start y=-440'),
    'MOV-0019-h': ('wait corridor: crossing, u1 (500, -480) -> (500, 520)', 'cross start y=-480'),
    'MOV-0019-i': ('wait corridor: crossing, u1 (500, -540) -> (500, 460)', 'cross start y=-540'),
    'MOV-0019-j': ('wait corridor: offset head-on, u1 (1000, 32) -> (0, 32)', 'head-on k=32'),
}


def variant_text(label):
    purpose, layout = VARIANTS[label]
    u0, u1, orders = EXPLORED[layout]
    return scenario_text(label, purpose, [u0, u1], orders)


def outcomes(runner, sets, layouts):
    """Per layout: the distinct predicted descriptions and, per candidate, its outcome index."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in layouts.items():
            path = Path(tmp) / 'scenario.yaml'
            path.write_text(text)
            goals = targets_of(path)
            keys = [json.dumps(summary(units, goals), sort_keys=True) for units in run_sets(runner, path, sets)]
            distinct = sorted(set(keys), key=lambda k: -keys.count(k))
            out[name] = dict(outcomes=[json.loads(k) for k in distinct],
                             candidate_outcome=[distinct.index(k) for k in keys])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3pathing{EXT}')
    parser.add_argument('--out', type=Path, required=True, help='predictions.json')
    parser.add_argument('--scenarios', type=Path, help='write the variant scenarios here (never overwrites)')
    parser.add_argument('--explore', action='store_true', help='also print outcome counts for every explored layout')
    args = parser.parse_args()
    sets, tried = candidates(args.runner)
    adopted = [i for i, s in enumerate(sets) if all(s[k] == ADOPTED[k] for k in ADOPTED)]
    if len(adopted) != 1:
        raise SystemExit('the adopted parameters no longer reproduce MOV-0018')
    if args.explore:
        explored = outcomes(args.runner, sets, {n: scenario_text('MOV-0019-x', n, [u0, u1], o)
                                                for n, (u0, u1, o) in EXPLORED.items()})
        for name, row in explored.items():
            counts = [row['candidate_outcome'].count(i) for i in range(len(row['outcomes']))]
            print(f'{name}: outcomes {counts}, adopted -> {row["candidate_outcome"][adopted[0]]}')
    texts = {label: variant_text(label) for label in VARIANTS}
    if args.scenarios:
        args.scenarios.mkdir(parents=True, exist_ok=True)
        for label, text in texts.items():
            path = args.scenarios / f'{label}.yaml'
            if path.exists() and path.read_text() != text:
                raise SystemExit(f'{path} exists with different bytes; refusing to overwrite')
            path.write_text(text, newline='\n')
    predicted = outcomes(args.runner, sets, texts)
    write_json(args.out, dict(
        method='tools/predict_mov0019.py; candidates reproduce every MOV-0018 capture at P3 level',
        grid={k: [min(v), max(v)] for k, v in GRID.items()}, fixed=FIXED, adopted=ADOPTED, adopted_index=adopted[0],
        grid_sets=tried, candidates=[[s[k] for k in GRID] for s in sets], candidate_keys=list(GRID),
        variants={label: dict(question=VARIANTS[label][0], adopted_outcome=row['candidate_outcome'][adopted[0]], **row)
                  for label, row in predicted.items()}))
    for label, row in predicted.items():
        counts = [row['candidate_outcome'].count(i) for i in range(len(row['outcomes']))]
        print(f'{label}: outcomes {counts}, adopted -> {row["candidate_outcome"][adopted[0]]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

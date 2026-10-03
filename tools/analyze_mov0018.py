#!/usr/bin/env python3
"""MOV-0018 (docs/mov-0018.md): describe two-Footman collision traces and plot both paths.

Reads canonical traces (WC3 fixtures and/or C++ traces of the same scenarios) and
reports, per unit: the side it passes the other unit on, its largest sideways
deviation from the straight start-target line, any wait while ordered to move,
its arrival callback, and its final position, facing and order. Each variant gets
an SVG plot (standard library only). Nothing here grades a model; it describes.
"""
import argparse
import json
import math
from pathlib import Path

from trace_contract import load, write_json

COLORS = {('wc3', 'u0'): '#1f5fbf', ('wc3', 'u1'): '#c0392b', ('cpp', 'u0'): '#7fa8e8', ('cpp', 'u1'): '#e8958a'}


def samples(trace):
    units = {}
    for r in trace['records']:
        if r['kind'] == 'SAMPLE':
            v = r['values']
            units.setdefault(r['unit'], []).append(
                (r['callback'], float(v['x']), float(v['y']), float(v['facing']), int(v['order'])))
    return units


def targets(trace):
    """The move target of each unit (the scenario's single move action)."""
    found = {}
    for r in trace['records']:
        if r['kind'] == 'ACTION' and r['command'] == 'move':
            found[r['unit']] = (float(r['target']['x']), float(r['target']['y']))
    return found


def describe_unit(rows, other, target):
    start = rows[0]
    out = dict(start=[start[1], start[2]], final=dict(callback=rows[-1][0], x=rows[-1][1], y=rows[-1][2],
                                                      facing=rows[-1][3], order=rows[-1][4]))
    moved = max(math.hypot(r[1] - start[1], r[2] - start[2]) for r in rows)
    out['max_displacement'] = round(moved, 6)
    if target is None:
        out.update(ordered=False)
        return out
    dx, dy = target[0] - start[1], target[1] - start[2]
    length = math.hypot(dx, dy)
    # Signed perpendicular offset: positive is left of the start -> target direction.
    lateral = [((r[1] - start[1]) * -dy + (r[2] - start[2]) * dx) / length for r in rows]
    peak = max(range(len(rows)), key=lambda i: abs(lateral[i]))
    # Side relative to the other unit at the moment of closest approach.
    close = min(range(len(rows)), key=lambda i: math.hypot(rows[i][1] - other[i][1], rows[i][2] - other[i][2]))
    rel = ((other[close][1] - rows[close][1]) * -dy + (other[close][2] - rows[close][2]) * dx) / length
    gap = math.hypot(rows[close][1] - other[close][1], rows[close][2] - other[close][2])
    arrival = next((r[0] for r in rows[1:] if r[4] == 0), None)
    # Waits: two or more consecutive callbacks ordered to move without any displacement.
    waits, run = [], None
    for prev, cur in zip(rows, rows[1:]):
        still = cur[4] != 0 and prev[4] != 0 and (cur[1], cur[2]) == (prev[1], prev[2])
        if still:
            run = run or [prev[0], cur[0]]
            run[1] = cur[0]
        elif run:
            waits.append(run)
            run = None
    if run:
        waits.append(run)
    out.update(ordered=True, target=list(target), arrival_callback=arrival,
               largest_sideways_deviation=dict(callback=rows[peak][0], units=round(lateral[peak], 6)),
               # Within 16 units the bodies overlap: the unit went through the other.
               passes_other_on='through' if gap < 16 else 'right' if rel > 0 else 'left',
               closest_approach=dict(callback=rows[close][0], distance=round(gap, 6)),
               waits=[dict(first=a, last=b, callbacks=b - a) for a, b in waits if b - a >= 2])
    return out


def describe(trace):
    units, goal = samples(trace), targets(trace)
    return {name: describe_unit(rows, units['u1' if name == 'u0' else 'u0'], goal.get(name))
            for name, rows in units.items()}


def svg(title, traces, path):
    points = [(r[1], r[2]) for _, t in traces for rows in samples(t).values() for r in rows]
    x0, x1 = min(p[0] for p in points) - 40, max(p[0] for p in points) + 40
    y0, y1 = min(p[1] for p in points) - 40, max(p[1] for p in points) + 40
    width = 900
    scale = width / (x1 - x0)
    height = max(200, int((y1 - y0) * scale))
    sx = lambda x: (x - x0) * scale
    sy = lambda y: height - (y - y0) * scale
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + 40}" '
             f'viewBox="0 0 {width} {height + 40}" font-family="sans-serif" font-size="12">',
             f'<rect width="100%" height="100%" fill="white"/>',
             f'<text x="8" y="{height + 28}">{title} (x {x0:.0f}..{x1:.0f}, y {y0:.0f}..{y1:.0f}; equal axes; '
             'dots every 0.2 s; dashed circle = 16-unit radius at closest approach)</text>']
    for engine, trace in traces:
        units = samples(trace)
        for name, rows in units.items():
            color = COLORS[(engine, name)]
            line = ' '.join(f'{sx(r[1]):.2f},{sy(r[2]):.2f}' for r in rows)
            dash = '' if engine == 'wc3' else ' stroke-dasharray="6 3"'
            parts.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
            for r in rows[::10]:
                parts.append(f'<circle cx="{sx(r[1]):.2f}" cy="{sy(r[2]):.2f}" r="2" fill="{color}"/>')
            parts.append(f'<text x="{sx(rows[-1][1]) + 4:.1f}" y="{sy(rows[-1][2]) - 4:.1f}" fill="{color}">'
                         f'{engine} {name}</text>')
        other = units['u0'], units['u1']
        close = min(range(len(other[0])), key=lambda i: math.hypot(other[0][i][1] - other[1][i][1], other[0][i][2] - other[1][i][2]))
        for rows in other:
            parts.append(f'<circle cx="{sx(rows[close][1]):.2f}" cy="{sy(rows[close][2]):.2f}" r="{16 * scale:.2f}" '
                         f'fill="none" stroke="{COLORS[(engine, "u0" if rows is other[0] else "u1")]}" stroke-dasharray="2 2"/>')
    parts.append('</svg>')
    Path(path).write_text('\n'.join(parts) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--wc3', type=Path, action='append', required=True, help='canonical WC3 fixture (one per variant)')
    parser.add_argument('--cpp', type=Path, action='append', default=[], help='C++ trace, in the same variant order')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.cpp and len(args.cpp) != len(args.wc3):
        parser.error('give one --cpp per --wc3, or none')
    args.out.mkdir(parents=True, exist_ok=True)
    report = {}
    for i, path in enumerate(args.wc3):
        reference = load(path)
        label = reference['scenario']['map_revision']
        entry = dict(wc3=describe(reference))
        traces = [('wc3', reference)]
        if args.cpp:
            actual = load(args.cpp[i])
            entry['cpp'] = describe(actual)
            traces.append(('cpp', actual))
        svg(label, traces, args.out / f'{label}.svg')
        report[label] = entry
    write_json(args.out / 'description.json', report)
    print(json.dumps({k: {e: {u: (d.get('passes_other_on'), d.get('arrival_callback'), d['final']['x'], d['final']['y'])
                              for u, d in v.items()} for e, v in entry.items()} for k, entry in report.items()}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

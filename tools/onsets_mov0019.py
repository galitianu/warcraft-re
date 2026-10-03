#!/usr/bin/env python3
"""MOV-0019 (docs/mov-0019.md#results): where each WC3 wait began, from the fixtures alone.

For every wait in the dynamic two-Footman captures (MOV-0018-b/c, MOV-0019-g..j) it
finds the movement update at which the unit stopped and resumed. Updates fall at
0.01 + 0.03k s (footman-v4 cadence, MOV-0013), and samples are taken after a due
update, so a unit that stops at update k is still from callback ceil(t_k / 0.02), and one
that resumes at update k has moved by the first callback after t_k.
At the stop update and the one before it, it reports the other unit's position in the
waiting unit's frame (along its direction of travel and to its left), and the other
unit's velocity in that frame over the 0.02 s before the update. Positions between
callbacks are interpolated linearly; units move at constant velocity there.
"""
import argparse
import math
from pathlib import Path

from analyze_mov0018 import samples
from trace_contract import ROOT, load, write_json

FIXTURES = ROOT / 'oracle/canonical-generated/wc3-1.29.2-9231-x86'
LABELS = ('MOV-0018-b', 'MOV-0018-c', 'MOV-0019-g', 'MOV-0019-h', 'MOV-0019-i', 'MOV-0019-j')
PERIOD, UPDATE, PHASE = 0.02, 0.03, 0.01


def update_in(lo, hi, closed_low=False):
    """The single update in (lo, hi], or [lo, hi) when closed_low (windows are 0.02 s,
    updates 0.03 s apart)."""
    eps = 1e-9
    for k in range(math.floor((lo - PHASE) / UPDATE) - 1, math.ceil((hi - PHASE) / UPDATE) + 2):
        t = PHASE + UPDATE * k
        if (lo - eps <= t < hi - eps) if closed_low else (lo + eps < t <= hi + eps):
            return k
    raise ValueError(f'no update between {lo} and {hi}')


def at(rows, t):
    i = min(int(t / PERIOD), len(rows) - 2)
    w = t / PERIOD - i
    return tuple(rows[i][c] + (rows[i + 1][c] - rows[i][c]) * w for c in (1, 2))


def stops(rows):
    """[(stop update, resume update)] for every run of identical positions while ordered."""
    out, n = [], 1
    while n < len(rows) - 1:
        if rows[n][4] and (rows[n][1], rows[n][2]) == (rows[n + 1][1], rows[n + 1][2]):
            last = n + 1
            while last + 1 < len(rows) and (rows[last + 1][1], rows[last + 1][2]) == (rows[n][1], rows[n][2]):
                last += 1
            if last - n >= 1 and rows[last][4]:
                out.append((update_in(PERIOD * (n - 1), PERIOD * n), update_in(PERIOD * last, PERIOD * (last + 1), closed_low=True)))
            n = last + 1
        else:
            n += 1
    return out


def frame(rows, other, k):
    """The other unit relative to this one at update k, in this unit's frame of travel."""
    t = PHASE + UPDATE * k
    p, q = at(rows, t), at(other, t)
    before = at(rows, t - PERIOD)
    d = (p[0] - before[0], p[1] - before[1])
    if math.hypot(*d) < 1e-6:
        raise ValueError(f'unit not moving before update {k}')
    d = (d[0] / math.hypot(*d), d[1] / math.hypot(*d))
    q0 = at(other, t - PERIOD)
    v = ((q[0] - q0[0]) / PERIOD, (q[1] - q0[1]) / PERIOD)
    r = (q[0] - p[0], q[1] - p[1])
    return dict(update=k, t=round(t, 2), along=round(r[0] * d[0] + r[1] * d[1], 1),
                left=round(-r[0] * d[1] + r[1] * d[0], 1), distance=round(math.hypot(*r), 1),
                other_velocity_along=round(v[0] * d[0] + v[1] * d[1], 1),
                other_velocity_left=round(-v[0] * d[1] + v[1] * d[0], 1),
                other_moving=math.hypot(*v) > 1)


def onsets():
    report = {}
    for label in LABELS:
        units = samples(load(FIXTURES / f'{label}.json'))
        report[label] = {}
        for name, rows in units.items():
            other = units['u1' if name == 'u0' else 'u0']
            report[label][name] = [dict(stop=stop, resume=resume, held_updates=resume - stop,
                                        at_stop=frame(rows, other, stop), update_before=frame(rows, other, stop - 1))
                                   for stop, resume in stops(rows)]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = onsets()
    write_json(args.out, dict(method=__doc__.strip().splitlines()[0], cases=report))
    for label, units in report.items():
        for name, waits in units.items():
            for w in waits:
                s, b = w['at_stop'], w['update_before']
                print(f"{label} {name}: stop k{w['stop']} resume k{w['resume']} ({w['held_updates']} updates); "
                      f"other at stop along {s['along']} left {s['left']} v ({s['other_velocity_along']}, "
                      f"{s['other_velocity_left']}); before along {b['along']} left {b['left']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

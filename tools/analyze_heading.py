#!/usr/bin/env python3
"""Issue #6 arithmetic on retained WC3 fixtures: reported-facing braking and the
unmodelled east/west heading noise. Reads only committed canonical references.
Writes JSON and Markdown; every number is derived here, none is fed to the model.
"""
import argparse
import math
from pathlib import Path

from compare_traces import samples
from trace_contract import BUILD, ROOT, load, write_json

FIXTURES = ROOT / 'oracle/canonical' / BUILD
MAX_V = math.degrees(0.2)               # facing velocity cap, degrees per update
ACOS_ULP = math.degrees(math.sqrt(2 * 2.0 ** -24))  # acos(1 - 2^-24), degrees


def braking(error):
    """Candidate end-phase step for a positive error in degrees."""
    return error * (error / MAX_V) ** 0.25


def invert_braking(step):
    return math.copysign((abs(step) * MAX_V ** 0.25) ** 0.8, step)


def signed(angle):
    return (angle + 180) % 360 - 180


def facing_series(label, start, end):
    rows = [r for r in samples(load(FIXTURES / f'{label}.json')) if r['unit'] == 'u0']
    values = [float(r['values']['facing']) for r in rows[start:end + 1]]
    series = [values[0]]
    for v in values[1:]:
        if v != series[-1]: series.append(v)
    return series


def braking_checks():
    """Approach to a settled facing: does err*(err/0.2 rad)^0.25 predict each step?"""
    checks = []
    for label, start, end, why in (('MOV-0002-r2', 183, 250, 'after arrival'),
                                   ('MOV-0010', 50, 250, 'after stop'),
                                   ('MOV-0006', 63, 75, 'end of 90 degree turn')):
        series = facing_series(label, start, end)
        target = series[-1]
        for before, after in zip(series, series[1:]):
            error = signed(target - before)
            observed = signed(after - before)
            snapped = after == target
            checks.append(dict(case=label, phase=why, facing_before=before, target=target,
                               error_degrees=round(error, 6), observed_step=round(observed, 6),
                               predicted_step=None if snapped else round(braking(abs(error)), 6),
                               snapped=snapped))
    return checks


def p001_batches():
    """Per 30 ms batch of JASS-0001-p001 (1 ms callbacks, 9-decimal readings)."""
    trace = load(FIXTURES / 'JASS-0001-p001.json')
    state = {}
    for record in trace['records']:
        if record['kind'] == 'EVENT' and record['name'] == 'CLOCKS':
            v = record['values']
            # 9-decimal readings lie within 1e-8 of the 1/4096 grid.
            state[record['callback']] = (round(float(v['x_9']) * 4096), round(float(v['y_9']) * 4096),
                                         float(v['facing_9']))
    rows, previous_facing = [], 0.0
    for k in range(16):
        start, end = state[11 + 30 * k], state[41 + 30 * k]
        x, y = start[0] / 4096, start[1] / 4096
        dx, dy = (end[0] - start[0]) / 4096, (end[1] - start[1]) / 4096
        travel = math.degrees(math.atan2(dy, dx))
        facing = signed(start[2])
        hidden = previous_facing + invert_braking(facing - previous_facing)
        target_direction = math.degrees(math.atan2(-y, 1000 - x))
        rows.append(dict(batch=k + 1, x_4096=start[0], y_4096=start[1], frac_x64=(start[0] / 64) % 1,
                         batch_dx_4096=end[0] - start[0], batch_dy_4096=end[1] - start[1],
                         travel_degrees=round(travel, 6), reported_facing=round(facing, 6),
                         target_direction=round(target_direction, 6),
                         inferred_hidden_heading=round(hidden, 6),
                         hidden_acos_ulps=round((hidden / ACOS_ULP) ** 2, 2),
                         travel_acos_ulps=round((travel / ACOS_ULP) ** 2, 1)))
        previous_facing = facing
    return rows


def markdown(checks, batches):
    lines = ['# Heading arithmetic on retained WC3 references', '',
             f'Fixtures `{BUILD}`; reproduce with `python3 tools/analyze_heading.py`.', '',
             '## Reported-facing braking: step = err × (err / 0.2 rad)^¼', '',
             'Target is the settled facing. Snapped rows reached it exactly in one update.', '',
             '| Case | Phase | Error ° | Observed step ° | Predicted step ° |', '|---|---|---|---|---|']
    for c in checks:
        predicted = 'snap' if c['snapped'] else f"{c['predicted_step']:.6f}"
        lines.append(f"| {c['case']} | {c['phase']} | {c['error_degrees']:.6f} | {c['observed_step']:.6f} | {predicted} |")
    lines += ['', '## JASS-0001-p001 east travel batches', '',
              'Positions in 1/4096 units. Travel is the batch displacement direction; the hidden',
              'heading inverts the braking law from consecutive reported facings. Ulps are',
              '(angle / acos(1 − 2⁻²⁴))², the float32 cosine deficit that `acos` would need.', '',
              '| Batch | X | Y | frac(64x) | dX | dY | Travel ° | Facing ° | Hidden ° | Hidden ulps | Travel ulps | Difference |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for b in batches:
        lines.append(f"| {b['batch']} | {b['x_4096']} | {b['y_4096']} | {b['frac_x64']:.3f} | {b['batch_dx_4096']} | {b['batch_dy_4096']} | "
                     f"{b['travel_degrees']:.5f} | {b['reported_facing']:.6f} | {b['inferred_hidden_heading']:.6f} | "
                     f"{b['hidden_acos_ulps']:.2f} | {b['travel_acos_ulps']:.1f} | {b['hidden_acos_ulps'] - b['travel_acos_ulps']:.1f} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'results/footman-v3')
    args = parser.parse_args()
    checks, batches = braking_checks(), p001_batches()
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / 'heading-analysis.json', dict(reference_build=BUILD, braking=checks, p001_batches=batches))
    (args.out / 'heading-analysis.md').write_text(markdown(checks, batches))
    worst = max(abs(c['observed_step'] - c['predicted_step']) for c in checks if not c['snapped'])
    print(f'braking: {len(checks)} steps, worst |observed - predicted| {worst:.6f} degrees')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare footman-v4 with the 1 ms state captures (JASS-0001-p001, MOV-0012).

Each callback of these captures prints the Footman's X, Y and facing with nine
decimals (R2SW_9) and the elapsed/remaining time of one-shot timers. For every
retained run this prints the model state in the frame a callback observes the
way WC3 does, and compares strings:

* positions/facing: tools/wc3states, the C++ footman-v4 state after each 1 ms step;
* timers: the library clock rule also used by tools/wc3test (Cases.cpp): the
  periodic sampler's scheduled time advances by add(time, period) from 0.5 s, and
  TimerGetElapsed = sub(timeout, sub(add(0.5, timeout), scheduled)).

Callback k reads frame (k - 1) // 5 (5 ms frames; callback 0 reads frame 0).
Callbacks 15, 20, 25, 30 and 35 are an unexplained exception: every capture shows
them reading frame k / 5, one frame earlier than the rule. They are compared
with the rule and reported as mismatches, never shifted silently.
Returns 0 if every compared string is identical, 1 if any differs, 2 on error.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from oracle_parse import Invalid, parse
from trace_contract import BUILD, ROOT, load
from wc3_float import add, bits, r2sw, sub

# label: start (x, y), facing degrees, target (x, y); see oracle/jass/<label>.j.
SCENARIOS = {
    'JASS-0001-p001': ((0, 0), 0, (1000, 0)),
    'MOV-0012-a': ((0, 0), 0, (1000, 0)),  # CreateUnit placed the unit at (0, 0), see a-r2.
    'MOV-0012-a-r2': ((0.001953125, 0), 0, (1000, 0)),
    'MOV-0012-b': ((0.001953125, 0), 0, (1000.001953125, 0)),
    'MOV-0012-c': ((0.005859375, 0), 0, (1000, 0)),
    'MOV-0012-d': ((0, 256), 0, (1000, 256)),
    'MOV-0012-e': ((0, 0), 30, (866.025391, 500)),
    'MOV-0012-f': ((0, 0), 180, (-1000, 0)),
    'MOV-0012-g': ((0, 0), 0, (200, 0)),
}
# Same move sampled every 10/20/25/50 ms; callback k reads frame k * period / 5 ms after its update.
TIMING_VARIANTS = ['JASS-0001-p010', 'JASS-0001-p020', 'JASS-0001-p025', 'JASS-0001-p050']
FRAME_STEPS = 5
CLOCK_START = 0x3f000000  # 0.5 s, World.h HeadingModel::clock_start


def model_states(runner, scenario, steps):
    (x, y), facing, (tx, ty) = scenario
    out = subprocess.run([str(runner), repr(x), repr(y), repr(facing), repr(tx), repr(ty), str(steps)],
                         check=True, capture_output=True, text=True).stdout
    return [tuple(int(v, 16) for v in line.split()[1:]) for line in out.splitlines()]


def observed_frame(callback):
    return 0 if callback == 0 else (callback - 1) // FRAME_STEPS


def timer_text(key, scheduled):
    """Model the library's TimerGetElapsed/TimerGetRemaining fields (c<timeout>[_remaining][_9])."""
    name, _, rest = key.partition('_')
    timeout = bits(float(name[1:]))
    remaining = sub(add(CLOCK_START, timeout), scheduled)
    value = remaining if rest.startswith('remaining') else sub(timeout, remaining)
    return r2sw(value, 9 if key.endswith('_9') else 6)


def compare_run(capture, states):
    counts, first = {}, {}

    def check(key, callback, expected, got):
        total = counts.setdefault(key, [0, 0])
        total[0] += 1
        if expected != got:
            total[1] += 1
            first.setdefault(key, []).append(dict(callback=callback, reference=expected, actual=got))
    period = bits(float(capture['requested_period']))
    scheduled, by_callback = CLOCK_START, {}
    for event in capture['_events']:
        if event['kind'] == 'EVENT' and event['name'] in ('STATE', 'CLOCKS'):
            by_callback[event['callback']] = dict(p.split('=', 1) for p in event['detail'].split('|'))
    for tick in capture['_ticks']:
        k = int(tick['callback'])
        if k:
            scheduled = add(scheduled, period)
        check('t', k, tick['t'], timer_text('c1000', scheduled))
        fields = by_callback.get(k)
        if fields is None:
            continue
        x, y, facing = states[FRAME_STEPS * observed_frame(k) + FRAME_STEPS - 1]
        for key, value in fields.items():
            if key.startswith('c'):
                check('timers', k, value, timer_text(key, scheduled))
            else:
                check(key[:-2], k, value, r2sw({'x_9': x, 'y_9': y, 'facing_9': facing}[key], 9))
    return counts, first


def compare_all(runner, captures_root):
    report = {}
    for label, scenario in SCENARIOS.items():
        runs = sorted((Path(captures_root) / label).glob('run-*.txt'))
        if not runs:
            raise Invalid(f'{label}: no retained runs')
        captures = [parse(path) for path in runs]
        steps = FRAME_STEPS * (observed_frame(max(c['callbacks'] for c in captures)) + 1)
        states = model_states(runner, scenario, steps)
        for path, capture in zip(runs, captures):
            counts, first = compare_run(capture, states)
            report[f'{label}/{path.name}'] = dict(
                payload_sha256=capture['payload_sha256'], compared={k: v[0] for k, v in counts.items()},
                different={k: v[1] for k, v in counts.items()}, mismatches=first)
    # The other JASS-0001 timing variants: canonical R2SW_6 samples of the same move.
    for label in TIMING_VARIANTS:
        trace = load(Path(captures_root).parents[1] / 'canonical' / BUILD / f'{label}.json')
        period = bits(float(trace['scenario']['requested_period']))
        step_ms = round(float(trace['scenario']['requested_period']) * 1000)
        states = model_states(runner, SCENARIOS['JASS-0001-p001'],
                              step_ms * trace['scenario']['callbacks'] + FRAME_STEPS)
        counts, first = {}, {}
        scheduled = CLOCK_START
        for record in trace['records']:
            k = record.get('callback')
            if record['kind'] == 'TICK':
                if k:
                    scheduled = add(scheduled, period)
                pairs = [('t', record['time']['reported'], timer_text('c1000', scheduled))]
            elif record['kind'] == 'SAMPLE':
                state = states[FRAME_STEPS * (k * step_ms // FRAME_STEPS) + FRAME_STEPS - 1]
                pairs = [(key, record['values'][key], r2sw(value, 6)) for key, value in zip(('x', 'y', 'facing'), state)]
            else:
                continue
            for key, expected, got in pairs:
                total = counts.setdefault(key, [0, 0])
                total[0] += 1
                if expected != got:
                    total[1] += 1
                    first.setdefault(key, []).append(dict(callback=k, reference=expected, actual=got))
        report[label] = dict(compared={k: v[0] for k, v in counts.items()},
                             different={k: v[1] for k, v in counts.items()}, mismatches=first)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, required=True, help='built tools/wc3states')
    parser.add_argument('--captures', type=Path, default=ROOT / 'oracle/captures' / BUILD)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    try:
        report = compare_all(args.runner, args.captures)
    except (OSError, Invalid, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f'invalid input: {error}', file=sys.stderr)
        return 2
    for run, row in report.items():
        first = row['mismatches']
        summary = ', '.join(f"{k} {n - row['different'][k]}/{n}" for k, n in row['compared'].items())
        where = {k: [m['callback'] for m in v] for k, v in first.items()}
        print(f"{run} {'IDENTICAL' if not first else 'DIFFERENT'}: {summary}"
              + (f'; mismatched callbacks {where}' if first else ''))
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return 0 if not any(row['mismatches'] for row in report.values()) else 1


if __name__ == '__main__':
    sys.exit(main())

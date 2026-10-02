#!/usr/bin/env python3
"""MOV-0014 predictions (docs/mov-0014.md), written before capture.

For each scenario this runs footman-v4 (wc3test, rule H0) and its 1 ms state
sequence (wc3states). It then lists, for every frame-selection hypothesis, the
callbacks that would read the next 5 ms frame where that changes the printed X/Y.
For every library-clock hypothesis it prints all TICK strings. The same code reads
the retained MOV-0013 fixtures as a check: every hypothesis kept here must
reproduce them. No capture of the predicted maps is read.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

from trace_contract import BUILD, ROOT, load, write_json
from wc3_float import add, bits, r2sw, sub

EXT = '.exe' if os.name == 'nt' else ''
SETUP = 0x3f000000  # 0.5 s, World.h HeadingModel::clock_start
TIMEOUT = bits(1000.0)
PREDICTED = [f'scenarios/MOV-0014/MOV-0014-{v}.yaml' for v in 'abc']
CHECKED = {f'MOV-0013-{v}': f'scenarios/MOV-0013/MOV-0013-{v}.yaml' for v in 'abcd'}
FRAME_RULES = ('H0', 'H1', 'Lu', 'Ls')
CLOCK_RULES = ('M0', 'M1', 'Q16', 'Q17', 'Q18', 'Qrel')
# Every retained schedule starts at the 0.5 s bootstrap (JASS-0001, MOV-0001..0012).
RETAINED_SCHEDULES = {'0.001': 1000, '0.01': 500, '0.02': 600, '0.025': 200, '0.05': 100}


def exact(b):
    return Fraction(struct.unpack('<f', struct.pack('<I', b))[0])


def ulp(b):
    return Fraction(2) ** (((b >> 23) & 255) - 150)


def floor_float(x):
    """float32 bits of the largest float <= x (x > 0)."""
    b = bits(float(x))
    return b - 1 if exact(b) > x else b


def schedule(start_text, period_text, callbacks):
    s = SETUP if Fraction(start_text) == 0 else add(SETUP, bits(float(start_text)))
    out = [s]
    for _ in range(callbacks):
        out.append(add(out[-1], bits(float(period_text))))
    return out


def frame_clocks(count):
    c = [SETUP]
    for _ in range(count):
        c.append(add(c[-1], bits(0.005)))
    return c


def clock(rule, s):
    """TICK text: TimerGetElapsed of the 1000 s timer started with the sampler."""
    if rule == 'M0':  # pre-registered in MOV-0013; footman-v4's runner
        expiry = add(s[0], TIMEOUT)
        return [r2sw(sub(TIMEOUT, sub(expiry, now)), 6) for now in s]
    if rule == 'M1':
        start = exact(s[0])
    else:
        e = {'Q16': 16, 'Q17': 17, 'Q18': 18, 'Qrel': 17 if exact(s[0]) < 1 else 16}[rule]
        q = Fraction(1, 2 ** e)
        start = exact(s[0]) - exact(s[0]) % q
    # Remaining time exact, rounded down to float32; elapsed = sub(1000, remaining).
    return [r2sw(sub(TIMEOUT, floor_float(start + exact(TIMEOUT) - exact(now))), 6) for now in s]


def reads_next(rule, k, lag, now):
    """Does callback k read the frame after H0's, whose clock is lag seconds later?"""
    if rule == 'H0':
        return False
    if rule == 'H1':  # MOV-0013: the sampler's own boundary callbacks 15-35
        return k in (15, 20, 25, 30, 35) and lag < Fraction(1, 2 ** 16)
    units = lag / ulp(now) if rule == 'Lu' else lag * 2 ** 24
    return 3 <= units <= 7


def scenario_fields(path):
    text = (ROOT / path).read_text()
    get = lambda key, default=None: (re.search(rf'^  {key}: (\S+)$', text, re.M) or [None, default])[1]
    return get('start', '0'), get('period'), int(get('callbacks'))


def model(runner, path, out):
    result = subprocess.run([str(runner), '--scenario', path, '--model', 'v4', '--seed', '1', '--out', str(out)],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr)
    return load(next(Path(out).glob('MOV-*.json')))


def states(states_runner, trace, steps):
    first = next(r for r in trace['records'] if r['kind'] == 'SAMPLE')['values']
    action = next(r for r in trace['records'] if r['kind'] == 'ACTION')
    out = subprocess.run([str(states_runner), first['x'], first['y'], first['facing'], action['target']['x'],
                          action['target']['y'], str(steps), str(action['time']['state_us'] // 1000)],
                         capture_output=True, text=True, check=True, timeout=60).stdout
    return [tuple(int(v, 16) for v in line.split()[1:]) for line in out.splitlines()]


def analyse(runner, states_runner, path):
    start, period, callbacks = scenario_fields(path)
    s = schedule(start, period, callbacks)
    with tempfile.TemporaryDirectory() as temp:
        trace = model(runner, path, temp)
    events = [r for r in trace['records'] if r['kind'] == 'EVENT']
    ticks = [r for r in trace['records'] if r['kind'] == 'TICK']
    # Bind this schedule to the C++ runner's. footman-v4 reported M0 when these
    # predictions were written and Q17 once MOV-0014 confirmed it; neither feeds them.
    runner_clock = 'Q17' if '2^-17' in trace['identity']['build']['parameters']['library_clock'] else 'M0'
    if clock(runner_clock, s) != [r2sw(bits(float(t['time']['reported'])), 6) for t in ticks]:
        raise ValueError(f'{path}: predictor schedule differs from wc3test')
    frames = [e['time']['state_us'] // 5000 for e in events]
    c = frame_clocks(max(frames) + 2)
    sequence = states(states_runner, trace, (max(frames) + 2) * 5)
    xy = lambda n: tuple(r2sw(v, 9) for v in sequence[5 * n][:2])
    rules = {rule: dict(reads_next=[], visible_xy=[]) for rule in FRAME_RULES}
    lags = {}
    for k, n in enumerate(frames):
        if not (exact(c[n]) <= exact(s[k]) < exact(c[n + 1])):
            raise ValueError(f'{path}: callback {k} is not after frame {n} under H0')
        lag = exact(c[n + 1]) - exact(s[k])
        if k % 5 == 0 and k <= 100:
            lags[k] = dict(ulps=float(lag / ulp(s[k])), units_2_24=float(lag * 2 ** 24))
        for rule in FRAME_RULES:
            if reads_next(rule, k, lag, s[k]):
                rules[rule]['reads_next'].append(k)
                if xy(n + 1) != xy(n):
                    rules[rule]['visible_xy'].append(k)
    onset = next(r['callback'] for r in trace['records'] if r['kind'] == 'SAMPLE' and float(r['values']['x']) != 0)
    m0 = clock('M0', s)
    clocks = {}
    for rule in CLOCK_RULES:
        text = clock(rule, s)
        clocks[rule] = dict(sha256=hashlib.sha256(json.dumps(text).encode()).hexdigest(),
                            differs_from_m0=[k for k, (a, b) in enumerate(zip(text, m0)) if a != b],
                            first=text[:3])
    return dict(scenario=path, start=start, callback0_frame=frames[0], onset_callback=onset,
                boundary_lags=lags, frame=rules, clock=clocks), (s, frames, sequence)


def retained_schedules():
    """Callbacks each rule moves off H0 in every retained (start 0) schedule."""
    out = {}
    for period, callbacks in RETAINED_SCHEDULES.items():
        s = schedule('0', period, callbacks)
        c = frame_clocks(round(callbacks * float(period) / 0.005) + 2)
        n, moved = 0, {rule: [] for rule in FRAME_RULES}
        for k, now in enumerate(s):
            while exact(c[n + 1]) <= exact(now):
                n += 1
            for rule in FRAME_RULES:
                if reads_next(rule, k, exact(c[n + 1]) - exact(now), now):
                    moved[rule].append(k)
        out[period] = moved
    return out


def observed(fixture, s, frames, sequence):
    """Callbacks whose WC3 STATE X/Y equal the next frame's, and any matching neither."""
    events = [r for r in fixture['records'] if r['kind'] == 'EVENT']
    nxt, neither = [], []
    for k, (e, n) in enumerate(zip(events, frames)):
        got = (e['values']['x_9'], e['values']['y_9'])
        text = lambda f: tuple(r2sw(v, 9) for v in sequence[5 * f][:2])
        if got == text(n):
            continue
        (nxt if got == text(n + 1) else neither).append(k)
    ticks = [r['time']['reported'] for r in fixture['records'] if r['kind'] == 'TICK']
    return nxt, neither, ticks


def grade(args):
    """Apply the pre-registered decision rules (docs/mov-0014.md) to the captures."""
    with tempfile.TemporaryDirectory() as temp:
        regenerated = Path(temp) / 'predictions.json'
        subprocess.run([sys.executable, __file__, '--runner', str(args.runner), '--states', str(args.states),
                        '--out', str(regenerated)], check=True, capture_output=True, timeout=600)
        committed = ROOT / 'results/mov-0014/predictions.json'
        if regenerated.read_bytes() != committed.read_bytes():
            raise SystemExit('predictions differ from the committed pre-registration')
    predictions = load(committed)['predictions']
    maps = {}
    for path in PREDICTED:
        label = Path(path).stem
        p = predictions[label]
        _, (s, frames, sequence) = analyse(args.runner, args.states, path)
        fixture = load(ROOT / 'oracle/canonical-generated' / BUILD / f'{label}.json')
        nxt, neither, ticks = observed(fixture, s, frames, sequence)
        tick_sha = hashlib.sha256(json.dumps(ticks).encode()).hexdigest()
        aux = [r2sw(sub(bits(10.0), sub(add(SETUP, bits(10.0)), now)), 9) for now in s]
        events = [r for r in fixture['records'] if r['kind'] == 'EVENT']
        samples = [r for r in fixture['records'] if r['kind'] == 'SAMPLE']
        onset = next(r['callback'] for r in samples if float(r['values']['x']) != 0)
        maps[label] = dict(observed_next_xy=nxt, observed_neither=neither, observed_onset_callback=onset,
                           tick_sha256=tick_sha,
                           aux_clock_mismatches=[k for k, (e, a) in enumerate(zip(events, aux)) if e['values']['c10_9'] != a],
                           frame={r: p['frame'][r]['visible_xy'] == nxt and not neither for r in FRAME_RULES},
                           clock={r: p['clock'][r]['sha256'] == tick_sha for r in CLOCK_RULES},
                           clock_mismatches={r: sum(a != b for a, b in zip(clock(r, s), ticks)) for r in CLOCK_RULES})
    frame = [r for r in FRAME_RULES if all(m['frame'][r] for m in maps.values())]
    clocks = [r for r in CLOCK_RULES if all(m['clock'][r] for m in maps.values())]
    write_json(args.grade, dict(experiment='MOV-0014', reference_build=BUILD,
                                predictions_sha256=hashlib.sha256(committed.read_bytes()).hexdigest(),
                                maps=maps, frame_rules_surviving=frame, clock_rules_surviving=clocks))
    print('surviving frame rules:', frame, 'clock rules:', clocks)
    for label, m in maps.items():
        print(label, 'next-frame X/Y at', m['observed_next_xy'], 'neither', m['observed_neither'],
              'onset', m['observed_onset_callback'], 'aux mismatches', len(m['aux_clock_mismatches']),
              'clock mismatches', m['clock_mismatches'])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3test{EXT}')
    parser.add_argument('--states', type=Path, default=ROOT / 'build' / f'wc3states{EXT}')
    parser.add_argument('--out', type=Path, default=ROOT / 'results/mov-0014/predictions.json')
    parser.add_argument('--grade', type=Path, help='after capture: regenerate the predictions, require the '
                        'committed bytes, and grade the MOV-0014 fixtures into this file')
    args = parser.parse_args()
    if args.grade:
        return grade(args)
    check = {}
    for label, path in CHECKED.items():
        prediction, (s, frames, sequence) = analyse(args.runner, args.states, path)
        fixture = load(ROOT / 'oracle/canonical-generated' / BUILD / f'{label}.json')
        nxt, neither, ticks = observed(fixture, s, frames, sequence)
        check[label] = dict(observed_next_xy=nxt, observed_neither=neither,
                            frame={r: prediction['frame'][r]['visible_xy'] == nxt for r in FRAME_RULES},
                            clock={r: sum(a != b for a, b in zip(clock(r, s), ticks)) for r in CLOCK_RULES})
    predictions = {}
    for path in PREDICTED:
        prediction, _ = analyse(args.runner, args.states, path)
        predictions[Path(path).stem] = prediction
    kept_frame = [r for r in FRAME_RULES if all(c['frame'][r] for c in check.values())]
    kept_clock = [r for r in CLOCK_RULES if all(c['clock'][r] == 0 for c in check.values())]
    write_json(args.out, dict(experiment='MOV-0014', reference_build=BUILD, tools=dict(
        runner='wc3test --model v4 (rule H0)', states='wc3states', arithmetic='tools/wc3_float.py'),
        retained_check=dict(maps=check, frame_rules_consistent=kept_frame, clock_rules_consistent=kept_clock,
                            schedules_reads_next=retained_schedules(),
                            schedules_note='1 ms: every retained 1 ms run reads the next frame at 15-35 '
                                           '(docs/footman-v4-results.md); 10-50 ms runs follow H0 X/Y'),
        predictions=predictions))
    print('consistent with MOV-0013:', kept_frame, kept_clock)
    for label, p in predictions.items():
        print(label, 'onset', p['onset_callback'], {r: v['visible_xy'] for r, v in p['frame'].items()},
              {r: len(v['differs_from_m0']) for r, v in p['clock'].items()})


if __name__ == '__main__':
    main()

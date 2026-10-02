#!/usr/bin/env python3
"""MOV-0015 predictions (docs/mov-0015.md), written before capture.

For each scenario this runs footman-v4 (wc3test, rules H0 and FH) and its 1 ms
state sequence (wc3states). For every frame rule it lists the callbacks that would
read the next 5 ms frame where that changes the printed X/Y; for every facing rule
it prints the facing at every callback. The same code grades the retained MOV-0013
and MOV-0014 fixtures and the JASS-0001 10-50 ms facings, and lists what each rule
changes in every retained schedule. No capture of the predicted maps is read.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import compare_states
from predict_mov0014 import (EXT, RETAINED_SCHEDULES, SETUP, clock, exact, frame_clocks, model, scenario_fields,
                             schedule, states)
from trace_contract import BUILD, ROOT, SCENARIOS, load, write_json
from wc3_float import add, bits, r2sw, sub

PREDICTED = [f'scenarios/MOV-0015/MOV-0015-{v}.yaml' for v in 'abcd']
CHECKED = {**{f'MOV-0013-{v}': f'scenarios/MOV-0013/MOV-0013-{v}.yaml' for v in 'abcd'},
           **{f'MOV-0014-{v}': f'scenarios/MOV-0014/MOV-0014-{v}.yaml' for v in 'abc'}}
FRAME_RULES = ('H0', 'T7', 'Tsub')
FACING_RULES = ('FH', 'FU')
UNIT = Fraction(1, 2 ** 24)
EARLY = bits(7 * 2.0 ** -24)  # Tsub: the frame time less 7 x 2^-24 s, in float32
UPDATE_EVERY = 6  # footman-v4 updates at frames 2 + 6j (0.51 s + 30 ms j)
FACING_SAMPLES = ['JASS-0001-p010', 'JASS-0001-p020', 'JASS-0001-p025', 'JASS-0001-p050']


def update_clock(count):
    """FU's 30 ms unit-update event: u(0) = 0.51 s, u(j + 1) = add(u(j), 0.03)."""
    u = [bits(0.51)]
    for _ in range(count):
        u.append(add(u[-1], bits(0.03)))
    return u


def is_update(n):
    return n % UPDATE_EVERY == 2


def reads_next(rule, now, after):
    """Does a callback at now (H0 frame n, c(n) <= now < c(n + 1) = after) read frame n + 1?"""
    if rule == 'H0':
        return False
    if rule == 'T7':  # less than 8 x 2^-24 s before the frame, exactly
        return exact(after) - exact(now) < 8 * UNIT
    return exact(now) >= exact(sub(after, EARLY))  # Tsub


def pre_update(rule, now, n, u):
    """Does a callback whose H0 frame n is an update frame print the facing from before it?"""
    return rule == 'FU' and is_update(n) and exact(now) < exact(u[(n - 2) // UPDATE_EVERY])


def analyse(runner, states_runner, path):
    start, period, callbacks = scenario_fields(path)
    s = schedule(start, period, callbacks)
    with tempfile.TemporaryDirectory() as temp:
        trace = model(runner, path, temp)
    events = [r for r in trace['records'] if r['kind'] == 'EVENT']
    ticks = [r for r in trace['records'] if r['kind'] == 'TICK']
    if clock('Q17', s) != [r2sw(bits(float(t['time']['reported'])), 6) for t in ticks]:
        raise ValueError(f'{path}: predictor schedule differs from wc3test')
    frames = [e['time']['state_us'] // 5000 for e in events]
    c = frame_clocks(max(frames) + 2)
    u = update_clock(max(frames) // UPDATE_EVERY + 2)
    sequence = states(states_runner, trace, (max(frames) + 2) * 5)
    xy = lambda n: tuple(r2sw(v, 9) for v in sequence[5 * n][:2])
    facing = lambda n: r2sw(sequence[5 * n][2], 9)
    changes = [n for n in range(1, max(frames) + 2) if facing(n) != facing(n - 1)]
    if any(not is_update(n) for n in changes):
        raise ValueError(f'{path}: facing changes off the update grid at {changes}')
    rules = {rule: dict(reads_next=[], visible_xy=[]) for rule in FRAME_RULES}
    facings = {rule: [] for rule in FACING_RULES}
    boundary = {}
    for k, n in enumerate(frames):
        if not (exact(c[n]) <= exact(s[k]) < exact(c[n + 1])):
            raise ValueError(f'{path}: callback {k} is not after frame {n} under H0')
        if tuple(bits(float(events[k]['values'][f])) for f in ('x_9', 'y_9', 'facing_9')) != sequence[5 * n]:
            raise ValueError(f'{path}: wc3test callback {k} is not H0/FH')
        lag = (exact(c[n + 1]) - exact(s[k])) / UNIT
        if lag < 16 and xy(n + 1) != xy(n):
            boundary[k] = dict(lag_2_24=int(lag), update_frame=is_update(n + 1), next_frame=n + 1)
        for rule in FRAME_RULES:
            if reads_next(rule, s[k], c[n + 1]):
                rules[rule]['reads_next'].append(k)
                if xy(n + 1) != xy(n):
                    rules[rule]['visible_xy'].append(k)
        for rule in FACING_RULES:
            facings[rule].append(facing(n - 1) if pre_update(rule, s[k], n, u) else facing(n))
    onset = next(r['callback'] for r in trace['records'] if r['kind'] == 'SAMPLE' and float(r['values']['x']) != 0)
    facing_rules = {rule: dict(sha256=hashlib.sha256(json.dumps(text).encode()).hexdigest(),
                               differs_from_fh={k: [a, b] for k, (a, b) in enumerate(zip(facings['FH'], text))
                                                if a != b})
                    for rule, text in facings.items()}
    return dict(scenario=path, start=start, callback0_frame=frames[0], onset_callback=onset,
                boundary_callbacks=boundary, frame=rules, facing=facing_rules), (s, frames, sequence, facings)


def observed(fixture, frames, sequence, facings):
    """WC3 callbacks whose X/Y equal the next frame's or neither, and the facing mismatches per rule."""
    events = [r for r in fixture['records'] if r['kind'] == 'EVENT']
    text = lambda f: tuple(r2sw(v, 9) for v in sequence[5 * f][:2])
    nxt, neither = [], []
    for k, (e, n) in enumerate(zip(events, frames)):
        got = (e['values']['x_9'], e['values']['y_9'])
        if got != text(n):
            (nxt if got == text(n + 1) else neither).append(k)
    facing = {rule: {k: e['values']['facing_9'] for k, (e, f) in enumerate(zip(events, predicted))
                     if e['values']['facing_9'] != f}
              for rule, predicted in facings.items()}
    return nxt, neither, facing


def retained_schedules():
    """Callbacks each rule changes in every retained (bootstrap start) schedule."""
    out = {}
    for period, callbacks in RETAINED_SCHEDULES.items():
        s = schedule('0', period, callbacks)
        c = frame_clocks(round(callbacks * float(period) / 0.005) + 2)
        u = update_clock(len(c) // UPDATE_EVERY + 1)
        n, moved = 0, {rule: [] for rule in FRAME_RULES + ('FU',)}
        for k, now in enumerate(s):
            while exact(c[n + 1]) <= exact(now):
                n += 1
            for rule in FRAME_RULES:
                if reads_next(rule, now, c[n + 1]):
                    moved[rule].append(k)
            if pre_update('FU', now, n, u):
                moved['FU'].append(k)
        out[period] = moved
    return out


def facing_samples(states_runner):
    """Each facing rule against the canonical JASS-0001 10-50 ms SAMPLE facings (R2SW_6)."""
    out = {}
    for label in FACING_SAMPLES:
        trace = load(ROOT / 'oracle/canonical' / BUILD / f'{label}.json')
        period, callbacks = trace['scenario']['requested_period'], trace['scenario']['callbacks']
        step_ms = round(float(period) * 1000)
        sequence = compare_states.model_states(states_runner, compare_states.SCENARIOS['JASS-0001-p001'],
                                               step_ms * callbacks + 5)
        s = schedule('0', period, callbacks)
        u = update_clock(step_ms * callbacks // 30 + 2)
        mismatches = {rule: [] for rule in FACING_RULES}
        for record in trace['records']:
            if record['kind'] != 'SAMPLE':
                continue
            k = record['callback']
            n = k * step_ms // 5  # compare_states: callback k reads frame k * period / 5 ms after its update
            for rule in FACING_RULES:
                f = n - 1 if pre_update(rule, s[k], n, u) else n
                if r2sw(sequence[5 * f + 4][2], 6) != record['values']['facing']:
                    mismatches[rule].append(k)
        out[label] = mismatches
    return out


def v1_cases(runner):
    """FU-changed callbacks of the MOV-0001-0010 suites where footman-v4's sampled facing moves.

    Those suites matched WC3 exactly with FH. At such a callback FU would print the
    previous sample's facing instead; elsewhere it prints the same value.
    """
    changed = retained_schedules()
    out = {}
    with tempfile.TemporaryDirectory() as temp:
        subprocess.run([str(runner), *SCENARIOS, '--out', temp, '--model', 'v4', '--seed', '1'], cwd=ROOT,
                       check=True, capture_output=True, timeout=60)
        for path in sorted(Path(temp).glob('MOV-*.json')):
            trace = load(path)
            facing = {}
            for r in trace['records']:
                if r['kind'] == 'SAMPLE':
                    facing.setdefault(r['callback'], {})[r['source']] = r['values']['facing']
            fu = changed[trace['scenario']['requested_period'].rstrip('0')]['FU']
            out[path.stem] = [k for k in fu if k in facing and facing[k] != facing.get(k - 1)]
    return out


def grade(args):
    """Apply the pre-registered decision rules (docs/mov-0015.md) to the captures."""
    with tempfile.TemporaryDirectory() as temp:
        regenerated = Path(temp) / 'predictions.json'
        subprocess.run([sys.executable, __file__, '--runner', str(args.runner), '--states', str(args.states),
                        '--out', str(regenerated)], check=True, capture_output=True, timeout=600)
        committed = ROOT / 'results/mov-0015/predictions.json'
        if regenerated.read_bytes() != committed.read_bytes():
            raise SystemExit('predictions differ from the committed pre-registration')
    predictions = load(committed)['predictions']
    maps = {}
    for path in PREDICTED:
        label = Path(path).stem
        p = predictions[label]
        _, (s, frames, sequence, facings) = analyse(args.runner, args.states, path)
        fixture = load(ROOT / 'oracle/canonical-generated' / BUILD / f'{label}.json')
        nxt, neither, facing = observed(fixture, frames, sequence, facings)
        ticks = [r['time']['reported'] for r in fixture['records'] if r['kind'] == 'TICK']
        aux = [r2sw(sub(bits(10.0), sub(add(SETUP, bits(10.0)), now)), 9) for now in s]
        events = [r for r in fixture['records'] if r['kind'] == 'EVENT']
        samples = [r for r in fixture['records'] if r['kind'] == 'SAMPLE']
        maps[label] = dict(observed_next_xy=nxt, observed_neither=neither, facing_mismatches=facing,
                           observed_onset_callback=next(r['callback'] for r in samples if float(r['values']['x']) != 0),
                           aux_clock_mismatches=[k for k, (e, a) in enumerate(zip(events, aux)) if e['values']['c10_9'] != a],
                           q17_clock_mismatches=[k for k, (a, b) in enumerate(zip(clock('Q17', s), ticks)) if a != b],
                           frame={r: p['frame'][r]['visible_xy'] == nxt and not neither for r in FRAME_RULES},
                           facing={r: not facing[r] for r in FACING_RULES})
    frame = [r for r in FRAME_RULES if all(m['frame'][r] for m in maps.values())]
    facing = [r for r in FACING_RULES if all(m['facing'][r] for m in maps.values())]
    write_json(args.grade, dict(experiment='MOV-0015', reference_build=BUILD,
                                predictions_sha256=hashlib.sha256(committed.read_bytes()).hexdigest(),
                                maps=maps, frame_rules_surviving=frame, facing_rules_surviving=facing))
    print('surviving frame rules:', frame, 'facing rules:', facing)
    for label, m in maps.items():
        print(label, 'next-frame X/Y at', m['observed_next_xy'], 'neither', m['observed_neither'],
              'onset', m['observed_onset_callback'], 'facing mismatches',
              {r: sorted(v) for r, v in m['facing_mismatches'].items()},
              'aux/Q17 mismatches', len(m['aux_clock_mismatches']), len(m['q17_clock_mismatches']))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3test{EXT}')
    parser.add_argument('--states', type=Path, default=ROOT / 'build' / f'wc3states{EXT}')
    parser.add_argument('--out', type=Path, default=ROOT / 'results/mov-0015/predictions.json')
    parser.add_argument('--grade', type=Path, help='after capture: regenerate the predictions, require the '
                        'committed bytes, and grade the MOV-0015 fixtures into this file')
    args = parser.parse_args()
    if args.grade:
        return grade(args)
    check = {}
    for label, path in CHECKED.items():
        prediction, (s, frames, sequence, facings) = analyse(args.runner, args.states, path)
        fixture = load(ROOT / 'oracle/canonical-generated' / BUILD / f'{label}.json')
        nxt, neither, facing = observed(fixture, frames, sequence, facings)
        check[label] = dict(observed_next_xy=nxt, observed_neither=neither,
                            frame={r: prediction['frame'][r]['visible_xy'] == nxt for r in FRAME_RULES},
                            facing_mismatches=facing)
    samples = facing_samples(args.states)
    v1 = v1_cases(args.runner)
    predictions = {}
    for path in PREDICTED:
        prediction, _ = analyse(args.runner, args.states, path)
        predictions[Path(path).stem] = prediction
    kept_frame = [r for r in FRAME_RULES if all(c['frame'][r] for c in check.values())]
    kept_facing = [r for r in FACING_RULES if not any(c['facing_mismatches'][r] for c in check.values())
                   and not any(m[r] for m in samples.values()) and not (r == 'FU' and any(v1.values()))]
    write_json(args.out, dict(experiment='MOV-0015', reference_build=BUILD, tools=dict(
        runner='wc3test --model v4 (rules H0, FH; clock Q17)', states='wc3states', arithmetic='tools/wc3_float.py'),
        retained_check=dict(maps=check, facing_samples=samples, v1_fu_visible=v1, frame_rules_consistent=kept_frame,
                            facing_rules_consistent=kept_facing, schedules_changed=retained_schedules(),
                            schedules_note='1 ms: every retained 1 ms run reads the next frame at 15-35 '
                                           '(docs/footman-v4-results.md); 10-50 ms runs follow H0 X/Y'),
        predictions=predictions))
    print('consistent with retained data:', kept_frame, kept_facing)
    for label, p in predictions.items():
        print(label, 'onset', p['onset_callback'], {r: v['visible_xy'] for r, v in p['frame'].items()},
              {r: sorted(map(int, v['differs_from_fh'])) for r, v in p['facing'].items()})


if __name__ == '__main__':
    main()

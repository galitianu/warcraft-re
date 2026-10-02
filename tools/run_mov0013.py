#!/usr/bin/env python3
"""MOV-0013 to MOV-0015 (docs/mov-0013.md to docs/mov-0015.md): v2 scenarios through WC3 and C++.

For each registered revision of an experiment this regenerates the case JASS from the
scenario (byte-identical to the retained case and generation record), validates
and normalizes the three retained WC3 runs, checks the committed fixture bytes
and runs tools/wc3test on
the scenario twice (separate processes, identical bytes). It then grades the
trace with the unchanged comparator and tolerances. It also compares exact text:
every C++ float printed as WC3's R2SW_6 (TICK, SAMPLE) or R2SW_9 (STATE). Where
the text differs, it reports which 5 ms frame of the footman-v4 state sequence
WC3 actually read (tools/wc3states).

The C++ runner implements the pre-registered frame rule H0 and, since MOV-0014,
the pre-registered Q17 library clock. The differences below were reviewed after
capture, and the gate requires exactly them. Any other
difference, or a missing one, fails. Exit 0 PASS, 1 FAIL, 2 invalid input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from compare_traces import compare, verify_reference_provenance
from generate_oracle import generate
from normalize_generated import normalize
from trace_contract import BUILD, EXPERIMENT_SHAPES, ROOT, load, sha256, write_json
from wc3_float import bits, r2sw

FIXTURES = ROOT / 'oracle/canonical-generated' / BUILD
CASES = ROOT / 'oracle/generated/maps'
FRAME_US = 5000
ULP_1000 = 6.103515625e-05  # one float32 ulp of the 1000 s library clock
# Reviewed observations (docs/mov-0013.md#results to docs/mov-0015.md#results). State:
# callbacks whose X/Y read frame H0 + 1, so text and canonical X/Y differ there.
# Facing/state_clock: callbacks whose facing or STATE c10_9 alone differ.
# Clock: TICKs clock_ulps (default -1) from the runner's library clock, pinned by
# count and the SHA-256 of the JSON callback list. Q17 removed MOV-0013-b/c's
# 875/624 (MOV-0014). Canonical: the unchanged comparator's status.
KNOWN = {
    'MOV-0013-a': dict(canonical='FAIL', state=[15, 20, 25, 30, 35], clock=(0, None)),
    'MOV-0013-b': dict(canonical='PASS', state=[], clock=(0, None)),
    'MOV-0013-c': dict(canonical='FAIL', state=[25, 30, 35], clock=(0, None)),
    'MOV-0013-d': dict(canonical='PASS', state=[], clock=(0, None)),
    'MOV-0014-a': dict(canonical='FAIL', state=[30, 35, 40, 45, 50, 55, 60], clock=(0, None)),
    'MOV-0014-b': dict(canonical='FAIL', state=[15], clock=(0, None)),
    'MOV-0014-c': dict(canonical='FAIL', state=[15], clock=(0, None)),
    # MOV-0015-a's sampler starts one ulp above the runner's add(0.5, start); see docs/mov-0015.md.
    'MOV-0015-a': dict(canonical='FAIL', state=[15, 20, 25, 30, 35, 40, 45], facing=[10],
                       state_clock=list(range(7, 376, 16)), clock_ulps=1,
                       clock=(1, 'ba9aee356b0ee01031b3af718012a11dd402ce710be4619f0b0236908c118d77')),
    'MOV-0015-b': dict(canonical='FAIL', state=[40, 45, 50], clock=(0, None)),
    'MOV-0015-c': dict(canonical='FAIL', state=[906], facing=[781, 811, 841, 871, 901], clock=(0, None)),
    'MOV-0015-d': dict(canonical='FAIL', state=[28], clock=(0, None)),
}
EXPERIMENTS = {'MOV-0013': 'sampler start phase', 'MOV-0014': 'sampler callback index or float32 lag',
               'MOV-0015': 'early-frame threshold and update-event facing clock'}

def text(value, decimals):
    return r2sw(bits(float(value)), decimals)


def exact(reference, actual):
    """Mismatched callbacks per property; R2SW of each C++ float against WC3's text."""
    result, compared = {}, {}

    def check(key, callback, expected, got):
        compared[key] = compared.get(key, 0) + 1
        if expected != got:
            result.setdefault(key, []).append(dict(callback=callback, reference=expected, actual=got))
    by_kind = lambda trace, kind: [r for r in trace['records'] if r['kind'] == kind]
    for kind in ('TICK', 'SAMPLE', 'EVENT'):
        refs, acts = by_kind(reference, kind), by_kind(actual, kind)
        if len(refs) != len(acts):
            raise ValueError(f'{kind} count {len(refs)} vs {len(acts)}')
        for ref, act in zip(refs, acts):
            if ref['callback'] != act['callback']:
                raise ValueError(f'{kind} order differs at callback {ref["callback"]}')
            cb = ref['callback']
            if kind == 'TICK':
                check('t', cb, ref['time']['reported'], text(act['time']['reported'], 6))
            elif kind == 'SAMPLE':
                for key in ('x', 'y', 'facing'):
                    check(key, cb, ref['values'][key], text(act['values'][key], 6))
                check('order', cb, ref['values']['order'], act['values']['order'])
            else:
                for key, value in ref['values'].items():
                    check(f'{ref["name"]}.{key}', cb, value, text(act['values'][key], 9))
    return compared, result


def states(runner, actual, steps):
    """footman-v4 state after every 1 ms step, with the move order at the C++ order step."""
    first = next(r for r in actual['records'] if r['kind'] == 'SAMPLE')
    action = next(r for r in actual['records'] if r['kind'] == 'ACTION')
    v, t = first['values'], action['target']
    out = subprocess.run([str(runner), v['x'], v['y'], v['facing'], t['x'], t['y'], str(steps),
                          str(action['time']['state_us'] // 1000)],
                         capture_output=True, text=True, check=True, timeout=60).stdout
    return [tuple(int(value, 16) for value in line.split()[1:]) for line in out.splitlines()]


def frames_read(reference, actual, runner):
    """Callbacks whose STATE differs from C++: the frames whose X/Y/facing WC3 printed."""
    events = {r['callback']: r for r in reference['records'] if r['kind'] == 'EVENT'}
    model = {r['callback']: r for r in actual['records'] if r['kind'] == 'EVENT'}
    last = max(r['time']['state_us'] for r in actual['records'] if r['kind'] == 'EVENT') // 1000
    sequence = states(runner, actual, last + 3 * FRAME_US // 1000)
    report = []
    for cb, ref in events.items():
        act = model[cb]
        if all(ref['values'][k] == text(act['values'][k], 9) for k in ('x_9', 'y_9', 'facing_9')):
            continue
        frame = act['time']['state_us'] // FRAME_US
        def matches(f, keys):
            x, y, facing = sequence[5 * f]
            got = dict(x_9=x, y_9=y, facing_9=facing)
            return all(r2sw(got[k], 9) == ref['values'][k] for k in keys)
        near = range(max(0, frame - 2), frame + 3)
        report.append(dict(callback=cb, cpp_frame=frame,
                           wc3_frames=[f for f in near if matches(f, ('x_9', 'y_9', 'facing_9'))],
                           xy_frames=[f for f in near if matches(f, ('x_9', 'y_9'))],
                           facing_frames=[f for f in near if matches(f, ('facing_9',))]))
    return report


def run_model(runner, scenario, dest):
    result = subprocess.run([str(Path(runner).resolve()), '--scenario', scenario, '--model', 'v4',
                             '--seed', '1', '--out', str(Path(dest).resolve())],
                            cwd=ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr)


def assess(label, canonical, exact_diffs, frames):
    """Observed differences against the reviewed list; any other difference fails."""
    known = KNOWN[label]
    state = sorted({d['callback'] for key, rows in exact_diffs.items() if key != 't' for d in rows})
    where = lambda *keys: sorted({d['callback'] for key in keys for d in exact_diffs.get(key, [])})
    xy = where('x', 'y', 'STATE.x_9', 'STATE.y_9')
    facing, state_clock = where('facing', 'STATE.facing_9'), where('STATE.c10_9')
    shifted = [f['callback'] for f in frames if f['xy_frames'] == [f['cpp_frame'] + 1]]
    clock = exact_diffs.get('t', [])
    callbacks = [d['callback'] for d in clock]
    count, digest = known['clock']
    ulps = known.get('clock_ulps', -1)
    clock_ok = len(clock) == count and (not clock or (
        hashlib.sha256(json.dumps(callbacks).encode()).hexdigest() == digest and all(
            round((float(d['reference']) - float(d['actual'])) / ULP_1000) == ulps for d in clock)))
    reviewed = dict(canonical=known['canonical'], state=known['state'], facing=known.get('facing', []),
                    state_clock=known.get('state_clock', []), clock_count=count, clock_sha256=digest)
    ok = (canonical == known['canonical'] and xy == shifted == known['state'] and facing == reviewed['facing']
          and state_clock == reviewed['state_clock'] and state == sorted(set(xy + facing + state_clock)) and clock_ok)
    return dict(status='PASS' if ok else 'FAIL', canonical=canonical, state_callbacks=state,
                frame_plus_one=shifted, facing_callbacks=facing, state_clock_callbacks=state_clock,
                clock_callbacks=callbacks, clock_ulps=ulps if clock else 0, reviewed=reviewed)

def regenerate(codegen, label, scenario):
    """The same scenario through the generator: the retained case and record, byte for byte."""
    files, generation = generate(codegen, [ROOT / scenario])
    if list(files) != [f'{label}.j'] or files[f'{label}.j'] != (CASES / f'{label}.j').read_bytes():
        raise ValueError(f'{label}: generated JASS differs from the retained case')
    generation['inputs'][0]['scenario']['path'] = scenario
    if generation != load(CASES / f'{label}-generation.json'):
        raise ValueError(f'{label}: generation record differs from the retained record')
    return generation['inputs'][0]['case']['sha256']


def labels(experiment):
    return [label for label, shape in EXPERIMENT_SHAPES.items() if shape['experiment'] == experiment]


def run(runner, states_runner, codegen, out, reports, check=True, experiment='MOV-0013'):
    reports.mkdir(parents=True, exist_ok=True)
    cases = []
    for label in labels(experiment):
        shape = EXPERIMENT_SHAPES[label]
        case_sha256 = regenerate(codegen, label, shape['scenario'])
        normalized = normalize(label, out / 'references')
        fixture = out / 'references' / f'{label}.json'
        if check and fixture.read_bytes() != (FIXTURES / f'{label}.json').read_bytes():
            raise ValueError(f'{label}: regenerated fixture differs from retained bytes')
        dest = out / 'traces' / label
        run_model(runner, shape['scenario'], dest)
        with tempfile.TemporaryDirectory() as temp:
            run_model(runner, shape['scenario'], temp)
            for path in sorted(dest.iterdir()):
                if path.read_bytes() != (Path(temp) / path.name).read_bytes():
                    raise ValueError(f'{label}: separate process output differs: {path.name}')
        reference, trace_path = load(fixture), dest / f"{shape['experiment']}.json"
        verify_reference_provenance(reference)
        actual = load(trace_path)
        if reference['provenance']['scenario'] != actual['provenance']['scenario']:
            raise ValueError(f'{label}: WC3 and C++ ran different scenario bytes')
        comparison = compare(reference, actual)
        comparison.update(reference_sha256=sha256(fixture), actual_sha256=sha256(trace_path))
        compared, differences = exact(reference, actual)
        frames = frames_read(reference, actual, states_runner)
        assessment = assess(label, comparison['status'], differences, frames)
        cases.append(dict(map_revision=label, scenario=reference['provenance']['scenario'], case_sha256=case_sha256,
                          status='PASS' if normalized['status'] == assessment['status'] == 'PASS' else 'FAIL',
                          reproduction=normalized, comparison=comparison,
                          exact=dict(compared=compared, different={k: len(v) for k, v in differences.items()},
                                     mismatches=differences),
                          frames_read=frames, assessment=assessment))
    status = 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    name = experiment.lower()
    write_json(reports / f'{name}.json', dict(status=status, reference_build=BUILD, cases=cases))
    lines = [f'# {experiment} {EXPERIMENTS[experiment]}', '', f'Gate: **{status}** (observed differences equal the reviewed list).', '',
             'C++ footman-v4 runs the same v2 scenario bytes with frame rule H0 and the Q17 clock. Canonical comparison',
             'uses the unchanged tolerances; exact text prints every C++ float as WC3 R2SW_6/R2SW_9.', '',
             '| Revision | Fresh WC3 runs | Control | Canonical | Exact text differences | WC3 read frame H0 + 1 at |',
             '|---|---|---|---|---|---|']
    for c in cases:
        diffs = ', '.join(f'{k} {n}' for k, n in sorted(c['exact']['different'].items())) or 'none'
        control = c['reproduction']['control_revision'] or '—'
        lines.append(f"| {c['map_revision']} | 3 payload-identical | {control} | {c['comparison']['status']} | "
                     f"{diffs} | {c['assessment']['frame_plus_one'] or 'none'} |")
    (reports / f'{name}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(f'{experiment} {status}: ' + '; '.join(
        f"{c['map_revision']} canonical {c['comparison']['status']}, frame+1 at {c['assessment']['frame_plus_one'] or 'none'}"
        for c in cases))
    return int(status != 'PASS')


def main():
    ext = '.exe' if os.name == 'nt' else ''
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / f'wc3test{ext}')
    parser.add_argument('--states', type=Path, default=ROOT / 'build' / f'wc3states{ext}')
    parser.add_argument('--codegen', type=Path, default=ROOT / 'build' / f'oracle_codegen{ext}')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--experiment', choices=EXPERIMENTS, action='append', help='default: every experiment')
    parser.add_argument('--write-fixtures', action='store_true', help='first normalization only; never overwrites')
    args = parser.parse_args()
    try:
        code = 0
        for experiment in args.experiment or EXPERIMENTS:
            out = args.out / experiment.lower()
            if args.write_fixtures:
                for label in labels(experiment):
                    if (FIXTURES / f'{label}.json').exists():
                        raise ValueError(f'{label}: retained fixture exists; refusing to overwrite')
            code |= run(args.runner, args.states, args.codegen, out, args.reports,
                        check=not args.write_fixtures, experiment=experiment)
            if args.write_fixtures:
                for label in labels(experiment):
                    (FIXTURES / f'{label}.json').write_bytes((out / 'references' / f'{label}.json').read_bytes())
        return code
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_mov0013: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

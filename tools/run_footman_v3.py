#!/usr/bin/env python3
"""Issue #6 evidence: footman-v3 against the committed WC3 fixtures, with v2 before.

Returns 0 when every comparison completed (FAIL verdicts are valid results) and 2
for invalid input, unreproduced v2 baseline or differing repeated output.
"""
import argparse
import math
from pathlib import Path
import subprocess
import tempfile

from compare_movement import format_first
from compare_traces import actions, compare_suite, markdown, samples
from trace_contract import BUILD, ROOT, SCENARIOS, load, sha256, write_json

PROPERTIES = ('x', 'y', 'facing', 'order', 't')


def label(n):
    return 'MOV-0002-r2' if n == 2 else f'MOV-{n:04d}'


def u0(trace):
    return [r for r in samples(trace) if r['unit'] == 'u0']


def behaviour(trace):
    """Observable summary of u0; every value is read from the trace, none is fitted."""
    rows = u0(trace)
    commands = actions(trace)
    events = []
    for action in commands:
        start = action['callback']
        before = rows[start]['values']
        moved = next((r for r in rows[start + 1:] if (r['values']['x'], r['values']['y']) != (before['x'], before['y'])), None)
        event = dict(command=action['command'], callback=start)
        if action['command'] == 'move':
            event['onset_callback'] = moved and moved['callback']
            if moved:
                dx = float(moved['values']['x']) - float(before['x'])
                dy = float(moved['values']['y']) - float(before['y'])
                event['first_travel_degrees'] = round(math.degrees(math.atan2(dy, dx)) % 360, 6)
                event['facing_at_onset'] = moved['values']['facing']
        else:
            event['displaced_after_stop'] = moved is not None
        later = commands[commands.index(action) + 1].get('callback') if action is not commands[-1] else None
        idle = next((r['callback'] for r in rows[start + 1:] if r['values']['order'] == '0'
                     and (later is None or r['callback'] <= later)), None)
        event['idle_callback'] = idle
        events.append(event)
    final = rows[-1]['values']
    last_change = max((r['callback'] for prev, r in zip(rows, rows[1:]) if r['values']['facing'] != prev['values']['facing']), default=None)
    return dict(commands=events, final_x=final['x'], final_y=final['y'], final_facing=final['facing'],
                last_facing_change_callback=last_change)


def run_model(runner, dest, model, phase):
    subprocess.run([str(runner), *SCENARIOS, '--out', str(Path(dest).resolve()), '--model', model,
                    '--phase', phase, '--seed', '1'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def property_summary(case):
    out = {}
    for prop in PROPERTIES:
        stat = case['properties'][prop]
        first = stat['first_divergence']
        out[prop] = dict(status=stat['status'], failures=stat['failures'], samples=stat['samples'],
                         first_callback=first and first['callback'], first_unit=first and first['unit'],
                         max_abs_delta=stat['max_abs_delta'], final_delta_by_unit=stat['final_delta_by_unit'])
    return out


def before_after_markdown(rows):
    lines = ['# footman-v2 → footman-v3 before/after', '',
             'Same committed WC3 fixtures and fixed tolerances; failures / samples, first failing callback,',
             'maximum absolute error. Primary after-due-update observation for both models.', '',
             '| Case | Verdict v2 → v3 | ' + ' | '.join(f'{p} v2 → v3' for p in PROPERTIES[:4]) + ' |',
             '|---|---|' + '---|' * 4]
    for row in rows:
        cells = []
        for prop in PROPERTIES[:4]:
            a, b = row['v2']['properties'][prop], row['v3']['properties'][prop]
            fmt = lambda s: f"{s['failures']}/{s['samples']} @{s['first_callback'] if s['first_callback'] is not None else '—'} max {s['max_abs_delta']:.6g}"
            cells.append(f'{fmt(a)} → {fmt(b)}')
        lines.append(f"| {row['case']} | {row['v2']['status']} → {row['v3']['status']} | " + ' | '.join(cells) + ' |')
    lines += ['', 'First overall divergence:', '']
    for row in rows:
        lines.append(f"- {row['case']}: v2 {format_first(row['v2']['first_divergence'])}; v3 {format_first(row['v3']['first_divergence'])}")
    return '\n'.join(lines) + '\n'


def behaviour_markdown(rows):
    lines = ['# Observable movement behaviour: WC3, footman-v2, footman-v3', '',
             'Onset is the first callback whose u0 position differs from the command callback;',
             'direction is atan2 of that first displacement. Idle is the first order-0 sample after the command.', '',
             '| Case | Command @cb | Onset WC3 / v2 / v3 | First travel ° WC3 / v2 / v3 | Idle WC3 / v2 / v3 |', '|---|---|---|---|---|']
    def get(entry, key):
        value = entry.get(key)
        return '—' if value is None else str(value)
    for row in rows:
        for i, ref in enumerate(row['wc3']['commands']):
            v2, v3 = row['v2']['commands'][i], row['v3']['commands'][i]
            if ref['command'] == 'move':
                onset = ' / '.join(get(e, 'onset_callback') for e in (ref, v2, v3))
                travel = ' / '.join(get(e, 'first_travel_degrees') for e in (ref, v2, v3))
            else:
                onset = 'displaced: ' + ' / '.join(str(e['displaced_after_stop']) for e in (ref, v2, v3))
                travel = '—'
            idle = ' / '.join(get(e, 'idle_callback') for e in (ref, v2, v3))
            lines.append(f"| {row['case']} | {ref['command']} @{ref['callback']} | {onset} | {travel} | {idle} |")
    lines += ['', '| Case | Final X WC3 / v2 / v3 | Final Y WC3 / v2 / v3 | Final facing WC3 / v2 / v3 | Last facing change WC3 / v2 / v3 |', '|---|---|---|---|---|']
    for row in rows:
        cells = [' / '.join(str(row[m][key]) for m in ('wc3', 'v2', 'v3'))
                 for key in ('final_x', 'final_y', 'final_facing', 'last_facing_change_callback')]
        lines.append(f"| {row['case']} | " + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n'


def run(runner, out, reports):
    references = ROOT / 'oracle/canonical' / BUILD
    reports.mkdir(parents=True, exist_ok=True)
    suites = {}
    for name, model, phase in (('v2', 'v2', 'after'), ('v3', 'v3', 'after'), ('v3-before', 'v3', 'before')):
        dest = out / name
        run_model(runner, dest, model, phase)
        suites[name] = compare_suite(references, dest)
        with tempfile.TemporaryDirectory() as temp:
            run_model(runner, Path(temp), model, phase)
            for path in sorted(dest.iterdir()):
                if path.read_bytes() != (Path(temp) / path.name).read_bytes():
                    raise ValueError(f'{name}: separate process output differs: {path.name}')
        if name != 'v2':
            report_dir = reports / name
            report_dir.mkdir(parents=True, exist_ok=True)
            write_json(report_dir / 'comparison.json', suites[name])
            (report_dir / 'comparison.md').write_text(markdown(suites[name]))
            write_json(report_dir / 'trace-hashes.json', {p.name: sha256(p) for p in sorted(dest.iterdir())})
    # The baseline must still be the retained footman-v2 behaviour, byte for byte.
    retained = load(ROOT / 'results/phase-2/v2/trace-hashes.json')
    for csv_name, digest in retained.items():
        if csv_name.endswith('.csv') and sha256(out / 'v2' / csv_name) != digest:
            raise ValueError(f'v2 baseline differs from retained Phase 2 output: {csv_name}')
    before_after, behaviours = [], []
    for n in range(1, 11):
        v2, v3 = suites['v2']['cases'][n - 1], suites['v3']['cases'][n - 1]
        before_after.append(dict(case=v3['case'],
                                 v2=dict(status=v2['status'], first_divergence=v2['first_divergence'], properties=property_summary(v2)),
                                 v3=dict(status=v3['status'], first_divergence=v3['first_divergence'], properties=property_summary(v3)),
                                 v3_before_update_diagnostic=dict(status=suites['v3-before']['cases'][n - 1]['status'],
                                                                  first_divergence=suites['v3-before']['cases'][n - 1]['state_first_divergence'])))
        behaviours.append(dict(case=v3['case'], wc3=behaviour(load(references / f'{label(n)}.json')),
                               v2=behaviour(load(out / 'v2' / f'MOV-{n:04d}.json')),
                               v3=behaviour(load(out / 'v3' / f'MOV-{n:04d}.json'))))
    write_json(reports / 'before-after.json', before_after)
    (reports / 'before-after.md').write_text(before_after_markdown(before_after))
    write_json(reports / 'behaviour.json', behaviours)
    (reports / 'behaviour.md').write_text(behaviour_markdown(behaviours))
    write_json(reports / 'repeatability.json', dict(classification='RNG-DETERMINISTIC-WITH-SEED', runs=2, seed=1,
               scope='two separate processes per model/phase; same native binary; all JSON/CSV/identity bytes equal; movement RNG unused',
               suites=['v2', 'v3', 'v3-before'], retail_rng_equivalence='UNKNOWN'))
    paths = [references / f'{label(n)}.json' for n in range(1, 11)]
    paths += [ROOT / 'tools' / name for name in ('trace_contract.py', 'compare_traces.py', 'run_footman_v3.py')]
    paths += [ROOT / 'docs' / name for name in ('footman-v3-model.md', 'trace-contract-v1.md')]
    write_json(reports / 'evidence-hashes.json', {str(p.relative_to(ROOT)): sha256(p) for p in paths})
    for name in ('v3', 'v3-before'):
        passed = sum(c['status'] == 'PASS' for c in suites[name]['cases'])
        print(f'{name}: {passed}/10 PASS; separate process bytes equal')
    print('v2 baseline: retained Phase 2 CSV hashes reproduced')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.runner.resolve(), args.out, args.reports)
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'run_footman_v3: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

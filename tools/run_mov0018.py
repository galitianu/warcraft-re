#!/usr/bin/env python3
"""MOV-0018 to MOV-0021 (docs/mov-0018.md, mov-0019.md, mov-0020.md, mov-0021.md): two Footmen
through WC3 and C++ footman-v4.

For each variant this regenerates the case JASS from the committed scenario
(byte-identical to the retained case and generation record), validates and
normalizes the three retained WC3 runs, checks the committed fixture bytes and runs
tools/wc3test twice (separate processes, identical bytes). It grades the trace with
the unchanged comparator and tolerances, then checks two things:

- P3 acceptance (what a player sees): each moving unit passes the other on the same
  side, arrives within ARRIVAL_CALLBACKS of WC3, waits when WC3 waits, and ends at
  the same position (within FINAL_UNITS) with the same order. A variant may list
  reviewed open differences (unit -> failing checks, with their rating); the failing
  checks must equal that list exactly.
- Reviewed differences: the comparator's failing properties, their failure counts
  and an upper bound on their largest difference equal the reviewed list below.

Any other difference, or a missing one, fails. Exit 0 PASS, 1 FAIL, 2 invalid input.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from analyze_mov0018 import describe
from compare_traces import compare, verify_reference_provenance
from run_mov0013 import FIXTURES, labels, regenerate, run_model
from normalize_generated import normalize
from trace_contract import BUILD, EXPERIMENT_SHAPES, load, sha256, write_json

EXPERIMENT = 'MOV-0018'
EXPERIMENTS = ('MOV-0018', 'MOV-0019', 'MOV-0020', 'MOV-0021')
ARRIVAL_CALLBACKS = 2   # Issue #24: arrival within 1-2 frames.
FINAL_UNITS = 1.0       # Well below P2 (several game units); the reviewed finals agree within 0.004.
WAIT_CALLBACKS = 2      # A wait may start or end this many callbacks away from WC3's.
# Reviewed after the model was fitted (docs/mov-0018.md#remaining-differences):
# failing comparator property -> (failures, bound on the largest absolute difference),
# and open P3-check failures: unit -> {check: rating}.
KNOWN = {
    'MOV-0018-a': dict(canonical='PASS', failing={}),
    'MOV-0018-b': dict(canonical='FAIL', failing={'x': (511, .032), 'y': (101, .014), 'facing': (127, 1.81)}),
    'MOV-0018-c': dict(canonical='FAIL', failing={'facing': (32, .119)}),
    'MOV-0018-d': dict(canonical='PASS', failing={}),
    # MOV-0019 to MOV-0021 after the post-hoc give-way refit; ratings in docs/mov-0020.md#results
    # and docs/mov-0021.md#results.
    'MOV-0019-a': dict(canonical='PASS', failing={}),
    'MOV-0019-b': dict(canonical='FAIL', failing={'x': (592, 0.652), 'y': (592, 8.61), 'facing': (590, 10.6)}),
    'MOV-0019-c': dict(canonical='FAIL', failing={'x': (592, 0.652), 'y': (592, 8.61), 'facing': (590, 10.6)}),
    'MOV-0019-d': dict(canonical='FAIL', failing={'x': (592, 0.375), 'y': (592, 9.96), 'facing': (590, 4.55)}, open={'u0': {'final': 'P2'}}),
    'MOV-0019-e': dict(canonical='FAIL', failing={'x': (594, 0.35), 'y': (595, 3.29), 'facing': (591, 11.3)}),
    'MOV-0019-f': dict(canonical='PASS', failing={}),
    'MOV-0019-g': dict(canonical='FAIL', failing={'x': (16, 8.1), 'facing': (25, 0.156)}),
    'MOV-0019-h': dict(canonical='FAIL', failing={'x': (25, 16.2), 'y': (25, 0.033), 'facing': (36, 0.51)}, open={'u0': {'waits': 'P2'}}),
    'MOV-0019-i': dict(canonical='FAIL', failing={'x': (513, 6.02), 'y': (514, 5.88), 'facing': (552, 36.3)}, open={'u0': {'side': 'P2'}, 'u1': {'final': 'P2'}}),
    'MOV-0019-j': dict(canonical='FAIL', failing={'x': (1028, 162), 'y': (1027, 46.3), 'facing': (1028, 57.9), 'order': (34, 852000)}, open={'u0': {'arrival': 'P3', 'waits': 'P3'}, 'u1': {'final': 'P3', 'arrival': 'P3'}}),
    'MOV-0020-a': dict(canonical='FAIL', failing={'x': (505, 6.39), 'y': (505, 0.516), 'facing': (534, 0.797)}, open={'u1': {'side': 'P2'}}),
    'MOV-0020-b': dict(canonical='FAIL', failing={'x': (1026, 122), 'y': (1026, 35.0), 'facing': (1026, 68.8), 'order': (30, 852000)}, open={'u0': {'final': 'P3', 'arrival': 'P3'}, 'u1': {'arrival': 'P3', 'waits': 'P3'}}),
    'MOV-0020-c': dict(canonical='FAIL', failing={'x': (505, 6.39), 'y': (505, 0.516), 'facing': (534, 0.797)}, open={'u0': {'side': 'P2'}}),
    'MOV-0020-d': dict(canonical='FAIL', failing={'x': (1027, 101), 'y': (1027, 42.2), 'facing': (1028, 66.7), 'order': (28, 852000)}, open={'u0': {'final': 'P3', 'arrival': 'P3', 'waits': 'P3'}, 'u1': {'final': 'P3', 'arrival': 'P3', 'waits': 'P3'}}),
    'MOV-0020-e': dict(canonical='FAIL', failing={'facing': (32, 0.119)}),
    'MOV-0020-f': dict(canonical='FAIL', failing={'x': (16, 8.1), 'facing': (25, 0.156)}),
    'MOV-0021-a': dict(canonical='FAIL', failing={'x': (1025, 51.6), 'y': (1025, 34.1), 'facing': (1028, 54.2), 'order': (11, 852000)}, open={'u0': {'arrival': 'P3', 'final': 'P2', 'waits': 'P3'}, 'u1': {'final': 'P2', 'waits': 'P2'}}),
    'MOV-0021-b': dict(canonical='FAIL', failing={'x': (620, 11.0), 'y': (1028, 40.5), 'facing': (935, 34.4), 'order': (8, 852000)}, open={'u0': {'final': 'P2'}, 'u1': {'arrival': 'P2', 'waits': 'P2'}}),
    'MOV-0021-c': dict(canonical='FAIL', failing={'x': (627, 37.2), 'y': (630, 40.5), 'facing': (953, 57.3), 'order': (13, 852000)}, open={'u0': {'arrival': 'P2', 'final': 'P2', 'waits': 'P2'}, 'u1': {'arrival': 'P2', 'waits': 'P2'}}),
    'MOV-0021-d': dict(canonical='FAIL', failing={'x': (1025, 32.9), 'y': (1028, 40.5), 'facing': (949, 53.9), 'order': (14, 852000)}, open={'u0': {'arrival': 'P2', 'final': 'P2', 'waits': 'P2'}, 'u1': {'arrival': 'P2', 'waits': 'P2'}}),
    'MOV-0021-e': dict(canonical='FAIL', failing={'x': (1010, 111), 'y': (1010, 33.2), 'facing': (1008, 46.5), 'order': (37, 852000)}, open={'u0': {'arrival': 'P3', 'final': 'P2', 'waits': 'P3'}, 'u1': {'arrival': 'P3', 'final': 'P2', 'waits': 'P3'}}),
    'MOV-0021-f': dict(canonical='FAIL', failing={'x': (1010, 31.1), 'y': (1010, 45.2), 'facing': (1008, 31.7), 'order': (13, 852000)}, open={'u0': {'arrival': 'P2', 'final': 'P2', 'waits': 'P2'}, 'u1': {'arrival': 'P2', 'final': 'P2', 'waits': 'P2'}}),
}


def acceptance(reference, actual):
    """P3 checks per unit: side, arrival, waits, final position and order."""
    wc3, cpp = describe(reference), describe(actual)
    checks = {}
    for unit, ref in wc3.items():
        act = cpp[unit]
        row = dict(final=abs(ref['final']['x'] - act['final']['x']) <= FINAL_UNITS
                   and abs(ref['final']['y'] - act['final']['y']) <= FINAL_UNITS
                   and ref['final']['order'] == act['final']['order'])
        if ref['ordered']:
            row['side'] = ref['passes_other_on'] == act['passes_other_on']
            row['arrival'] = (ref['arrival_callback'] is not None and act['arrival_callback'] is not None
                              and abs(ref['arrival_callback'] - act['arrival_callback']) <= ARRIVAL_CALLBACKS)
            row['waits'] = len(ref['waits']) == len(act['waits']) and all(
                abs(r['first'] - a['first']) <= WAIT_CALLBACKS and abs(r['last'] - a['last']) <= WAIT_CALLBACKS
                for r, a in zip(ref['waits'], act['waits']))
        checks[unit] = row
    return dict(status='PASS' if all(all(row.values()) for row in checks.values()) else 'FAIL',
                checks=checks, wc3=wc3, cpp=cpp)


def assess(label, comparison):
    """Comparator outcome against the reviewed list; any other difference fails."""
    known = KNOWN[label]
    props = {**comparison['properties'], **comparison['action_properties']}
    observed = {p: (s['failures'], s['max_abs_delta']) for p, s in props.items() if s['failures'] or p in known['failing']}
    ok = (comparison['status'] == known['canonical'] and not comparison['structural_differences']
          and set(observed) == set(known['failing'])
          and all(observed[p][0] == n and observed[p][1] <= bound for p, (n, bound) in known['failing'].items()))
    return dict(status='PASS' if ok else 'FAIL', canonical=comparison['status'],
                observed={p: dict(failures=n, max_abs_delta=d) for p, (n, d) in observed.items()},
                reviewed={p: dict(failures=n, max_abs_delta_bound=b) for p, (n, b) in known['failing'].items()},
                first_divergence=comparison['first_divergence'])


def review(label, accepted):
    """The P3 checks that fail, against the reviewed open differences."""
    failing = {u: sorted(c for c, ok in row.items() if not ok) for u, row in accepted['checks'].items()}
    failing = {u: c for u, c in failing.items() if c}
    open_ = KNOWN[label].get('open', {})
    return dict(failing=failing, open=open_,
                reviewed='PASS' if failing == {u: sorted(c) for u, c in open_.items()} else 'FAIL')


def grade(label, reference, actual):
    comparison = compare(reference, actual)
    accepted = acceptance(reference, actual)
    accepted.update(review(label, accepted))
    return comparison, assess(label, comparison), accepted


def gate_key(experiment):
    return experiment.lower().replace('-', '')  # MOV-0018 -> mov0018


def run(runner, codegen, out, reports, check=True, experiment=EXPERIMENT):
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
        trace_path = dest / f'{experiment}.json'
        reference, actual = load(fixture), load(trace_path)
        verify_reference_provenance(reference)
        if reference['provenance']['scenario'] != actual['provenance']['scenario']:
            raise ValueError(f'{label}: WC3 and C++ ran different scenario bytes')
        comparison, assessment, accepted = grade(label, reference, actual)
        comparison.update(reference_sha256=sha256(fixture), actual_sha256=sha256(trace_path))
        cases.append(dict(map_revision=label, scenario=reference['provenance']['scenario'], case_sha256=case_sha256,
                          status='PASS' if normalized['status'] == assessment['status'] == accepted['reviewed'] == 'PASS'
                          else 'FAIL',
                          reproduction=normalized, comparison=comparison, assessment=assessment, acceptance=accepted))
    status = 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    key = gate_key(experiment)
    write_json(reports / f'{key}.json', dict(status=status, reference_build=BUILD, cases=cases))
    lines = [f'# {experiment} two Footmen with unit pathing', '',
             f'Gate: **{status}** (P3 failures and comparator differences equal the reviewed lists).', '',
             'C++ footman-v4 with unit pathing runs the same v1 scenario bytes. Canonical comparison uses the',
             'unchanged tolerances.', '',
             '| Variant | Canonical | Failing properties (failures, largest difference) | Side | Arrival WC3 / C++ '
             '| P3 acceptance | Open differences (rating) |',
             '|---|---|---|---|---|---|---|']
    for c in cases:
        a = c['acceptance']
        failing = ', '.join(f"{p} {v['failures']} ({v['max_abs_delta']:.6g})"
                            for p, v in c['assessment']['observed'].items() if v['failures']) or 'none'
        side = ', '.join(f"{u} {d['passes_other_on']}" for u, d in a['wc3'].items() if d['ordered'])
        arrival = ', '.join(f"{u} {d['arrival_callback']}/{a['cpp'][u]['arrival_callback']}"
                            for u, d in a['wc3'].items() if d['ordered'])
        open_ = '; '.join(f"{u} {', '.join(f'{k} {r}' for k, r in checks.items())}"
                          for u, checks in a['open'].items()) or '—'
        lines.append(f"| {c['map_revision']} | {c['comparison']['status']} | {failing} | {side} | {arrival} "
                     f"| {a['status']} | {open_} |")
    (reports / f'{key}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(f'{experiment} {status}: ' + '; '.join(
        f"{c['map_revision']} canonical {c['comparison']['status']}, acceptance {c['acceptance']['status']}"
        f"{' (open differences reviewed)' if c['acceptance']['open'] else ''}, reviewed {c['assessment']['status']}"
        for c in cases))
    return int(status != 'PASS')


def main():
    ext = '.exe' if os.name == 'nt' else ''
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=root / 'build' / f'wc3test{ext}')
    parser.add_argument('--codegen', type=Path, default=root / 'build' / f'oracle_codegen{ext}')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--experiment', choices=EXPERIMENTS, default=EXPERIMENT)
    args = parser.parse_args()
    try:
        return run(args.runner, args.codegen, args.out, args.reports, experiment=args.experiment)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_mov0018: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

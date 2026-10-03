#!/usr/bin/env python3
"""MOV-0018 (docs/mov-0018.md): two colliding Footmen through WC3 and C++ footman-v4.

For each variant this regenerates the case JASS from the committed scenario
(byte-identical to the retained case and generation record), validates and
normalizes the three retained WC3 runs, checks the committed fixture bytes and runs
tools/wc3test twice (separate processes, identical bytes). It grades the trace with
the unchanged comparator and tolerances, then checks two things:

- P3 acceptance (what a player sees): each moving unit passes the other on the same
  side, arrives within ARRIVAL_CALLBACKS of WC3, waits when WC3 waits, and ends at
  the same position (within FINAL_UNITS) with the same order.
- Reviewed differences: the comparator's failing properties, their failure counts
  and an upper bound on their largest difference equal the reviewed list below.
  These remaining differences are rated P1 in docs/mov-0018.md#remaining-differences.

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
ARRIVAL_CALLBACKS = 2   # Issue #24: arrival within 1-2 frames.
FINAL_UNITS = 1.0       # Well below P2 (several game units); the reviewed finals agree within 0.004.
WAIT_CALLBACKS = 2      # A wait may start or end this many callbacks away from WC3's.
# Reviewed after the model was fitted (docs/mov-0018.md#remaining-differences):
# failing comparator property -> (failures, bound on the largest absolute difference).
KNOWN = {
    'MOV-0018-a': dict(canonical='PASS', failing={}),
    'MOV-0018-b': dict(canonical='FAIL', failing={'x': (511, .032), 'y': (101, .014), 'facing': (127, 1.81)}),
    'MOV-0018-c': dict(canonical='FAIL', failing={'facing': (32, .119)}),
    'MOV-0018-d': dict(canonical='PASS', failing={}),
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


def grade(label, reference, actual):
    comparison = compare(reference, actual)
    return comparison, assess(label, comparison), acceptance(reference, actual)


def run(runner, codegen, out, reports, check=True):
    reports.mkdir(parents=True, exist_ok=True)
    cases = []
    for label in labels(EXPERIMENT):
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
        trace_path = dest / f'{EXPERIMENT}.json'
        reference, actual = load(fixture), load(trace_path)
        verify_reference_provenance(reference)
        if reference['provenance']['scenario'] != actual['provenance']['scenario']:
            raise ValueError(f'{label}: WC3 and C++ ran different scenario bytes')
        comparison, assessment, accepted = grade(label, reference, actual)
        comparison.update(reference_sha256=sha256(fixture), actual_sha256=sha256(trace_path))
        cases.append(dict(map_revision=label, scenario=reference['provenance']['scenario'], case_sha256=case_sha256,
                          status='PASS' if normalized['status'] == assessment['status'] == accepted['status'] == 'PASS'
                          else 'FAIL',
                          reproduction=normalized, comparison=comparison, assessment=assessment, acceptance=accepted))
    status = 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    write_json(reports / 'mov0018.json', dict(status=status, reference_build=BUILD, cases=cases))
    lines = [f'# {EXPERIMENT} two colliding Footmen', '',
             f'Gate: **{status}** (P3 acceptance holds; comparator differences equal the reviewed P1 list).', '',
             'C++ footman-v4 with unit pathing runs the same v1 scenario bytes. Canonical comparison uses the',
             'unchanged tolerances.', '',
             '| Variant | Canonical | Failing properties (failures, largest difference) | Side | Arrival WC3 / C++ | P3 acceptance |',
             '|---|---|---|---|---|---|']
    for c in cases:
        a = c['acceptance']
        failing = ', '.join(f"{p} {v['failures']} ({v['max_abs_delta']:.6g})"
                            for p, v in c['assessment']['observed'].items() if v['failures']) or 'none'
        side = ', '.join(f"{u} {d['passes_other_on']}" for u, d in a['wc3'].items() if d['ordered'])
        arrival = ', '.join(f"{u} {d['arrival_callback']}/{a['cpp'][u]['arrival_callback']}"
                            for u, d in a['wc3'].items() if d['ordered'])
        lines.append(f"| {c['map_revision']} | {c['comparison']['status']} | {failing} | {side} | {arrival} | {a['status']} |")
    (reports / 'mov0018.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(f'{EXPERIMENT} {status}: ' + '; '.join(
        f"{c['map_revision']} canonical {c['comparison']['status']}, acceptance {c['acceptance']['status']}, "
        f"reviewed {c['assessment']['status']}" for c in cases))
    return int(status != 'PASS')


def main():
    ext = '.exe' if os.name == 'nt' else ''
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, default=root / 'build' / f'wc3test{ext}')
    parser.add_argument('--codegen', type=Path, default=root / 'build' / f'oracle_codegen{ext}')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    args = parser.parse_args()
    try:
        return run(args.runner, args.codegen, args.out, args.reports)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_mov0018: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

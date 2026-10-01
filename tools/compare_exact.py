#!/usr/bin/env python3
"""Exact comparison: print each C++ float as WC3's R2SW_6 and compare the strings.

compare_traces.py grades numerically within the declared tolerances. This
stricter check asks whether the C++ trace would have produced the same capture
text: SAMPLE x/y/facing, current order, and the callback clock when the model
predicts one (footman-v4). Returns 0 if every compared value is identical, 1 if
any differs, 2 on invalid input.
"""
import argparse
import json
import sys
from pathlib import Path

from trace_contract import BUILD, ROOT, load, validate
from wc3_float import bits, r2sw

CASES = [f'MOV-{n:04d}' for n in range(1, 11)]


def text(value):
    return r2sw(bits(float(value)), 6)


def compare(reference, actual):
    validate(reference); validate(actual)
    if reference['scenario'] != actual['scenario']:
        raise ValueError('incompatible experiment/map revision')
    counts = {key: [0, 0] for key in ('x', 'y', 'facing', 'order', 't')}
    first = {}

    def check(key, ref, expected, got):
        counts[key][0] += 1
        if expected != got:
            counts[key][1] += 1
            first.setdefault(key, dict(callback=ref['callback'], unit=ref.get('unit'),
                                       reference=expected, actual=got))
    def of(trace, kind):
        return [r for r in trace['records'] if r['kind'] == kind]
    for kind in ('TICK', 'SAMPLE'):
        refs, acts = of(reference, kind), of(actual, kind)
        if len(refs) != len(acts):
            raise ValueError(f'{kind} count {len(refs)} vs {len(acts)}')
        for ref, act in zip(refs, acts):
            if (ref['callback'], ref.get('unit')) != (act['callback'], act.get('unit')):
                raise ValueError(f"{kind} order differs at callback {ref['callback']}")
            if kind == 'TICK' and act['time']['reported'] is not None:
                check('t', ref, ref['time']['reported'], text(act['time']['reported']))
            if kind == 'SAMPLE':
                for key in ('x', 'y', 'facing'):
                    check(key, ref, ref['values'][key], text(act['values'][key]))
                check('order', ref, ref['values']['order'], act['values']['order'])
    return counts, first


def compare_all(reference_root, actual_root):
    report = {}
    for case in CASES:
        label = 'MOV-0002-r2' if case == 'MOV-0002' else case
        counts, first = compare(load(Path(reference_root) / f'{label}.json'), load(Path(actual_root) / f'{case}.json'))
        report[case] = dict(compared={k: v[0] for k, v in counts.items()},
                            different={k: v[1] for k, v in counts.items()}, first=first)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--reference', type=Path, default=ROOT / 'oracle/canonical' / BUILD)
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    try:
        report = compare_all(args.reference, args.actual)
    except (OSError, ValueError, KeyError) as error:
        print(f'invalid input: {error}', file=sys.stderr)
        return 2
    for case, row in report.items():
        summary = ', '.join(f"{k} {n - row['different'][k]}/{n}" for k, n in row['compared'].items())
        print(f"{case} {'IDENTICAL' if not row['first'] else 'DIFFERENT'}: {summary}"
              + (f"; first {row['first']}" if row['first'] else ''))
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return 0 if not any(row['first'] for row in report.values()) else 1


if __name__ == '__main__':
    sys.exit(main())

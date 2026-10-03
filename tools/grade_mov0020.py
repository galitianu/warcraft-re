#!/usr/bin/env python3
"""MOV-0020 (docs/mov-0020.md#decision-rules-before-capture): grade the predictions.

Reads only the committed predictions.json and the WC3 fixtures. Rule 1: in each
variant the WC3 waiting units are those with a wait of at least LONG_WAIT_CALLBACKS;
a hypothesis survives if it names exactly that one unit in every variant. Rule 2: in
b and d, both units' WC3 and model positions agree within 1 unit up to callback 80;
the model positions are rerun only when --model-traces names the pre-capture C++
traces. Writes grading.json.
"""
import argparse
import json
from pathlib import Path

from analyze_mov0018 import samples
from predict_mov0019 import summary
from predict_mov0020 import LONG_WAIT_CALLBACKS, waiting
from trace_contract import ROOT, load, write_json

FIXTURES = ROOT / 'oracle/canonical-generated/wc3-1.29.2-9231-x86'
PARTIAL_VARIANTS, PARTIAL_CALLBACKS, PARTIAL_UNITS = ('MOV-0020-b', 'MOV-0020-d'), 80, 1.0


def describe(trace):
    goals = {r['unit']: (float(r['target']['x']), float(r['target']['y']))
             for r in trace['records'] if r['kind'] == 'ACTION'}
    return json.loads(json.dumps(summary(samples(trace), goals)))


def grade(predictions, model_traces=None):
    variants, alive = {}, {name: True for name in ('index', 'order', 'role')}
    for label, row in predictions['variants'].items():
        observed = describe(load(FIXTURES / f'{label}.json'))
        waits = waiting(observed)
        named = {name: [unit] == waits for name, unit in row['hypotheses'].items()}
        for name, ok in named.items():
            alive[name] = alive[name] and ok
        variants[label] = dict(question=row['question'], roles=row['roles'], ordered_first=row['ordered_first'],
                               wc3=observed, wc3_waits=waits, hypotheses=row['hypotheses'], supported=named,
                               model_waits=row['model_waits'], model_matches_waits=row['model_waits'] == waits)
    partial = None
    if model_traces:
        partial = {}
        for label in PARTIAL_VARIANTS:
            wc3, cpp = samples(load(FIXTURES / f'{label}.json')), samples(load(model_traces / label / 'MOV-0020.json'))
            worst = max(max(abs(a[1] - b[1]), abs(a[2] - b[2]))
                        for unit in wc3 for a, b in zip(wc3[unit][:PARTIAL_CALLBACKS + 1], cpp[unit][:PARTIAL_CALLBACKS + 1]))
            partial[label] = dict(largest_xy_difference=round(worst, 6), status='PASS' if worst <= PARTIAL_UNITS else 'FAIL')
    survivors = [name for name, ok in alive.items() if ok]
    return dict(long_wait_callbacks=LONG_WAIT_CALLBACKS, variants=variants, surviving=survivors, partial_routes=partial,
                status='ONE-SURVIVES' if len(survivors) == 1 else 'NONE-SURVIVES' if not survivors else 'UNRESOLVED')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--predictions', type=Path, default=ROOT / 'results/mov-0020/predictions.json')
    parser.add_argument('--model-traces', type=Path, help='pre-capture C++ traces: DIR/<label>/MOV-0020.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = grade(load(args.predictions), args.model_traces)
    write_json(args.out, result)
    for label, v in result['variants'].items():
        print(f"{label}: WC3 waiting {v['wc3_waits']}; hypotheses {v['hypotheses']}; model {v['model_waits']}")
    print(f"surviving: {result['surviving']}; partial routes: {result['partial_routes']}")
    return int(result['status'] != 'ONE-SURVIVES')


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""MOV-0021 (docs/mov-0021.md#decision-rules-before-capture): grade the predictions.

Reads only the committed predictions.json and the WC3 fixtures. Rule 1: in each
variant the WC3 waiting units are those with a wait of at least LONG_WAIT_CALLBACKS;
a hypothesis survives if it names exactly that one unit in every variant. Rule 2: e's
waiting unit is compared with j's (the eastward unit). Writes grading.json.
"""
import argparse
from pathlib import Path

from grade_mov0020 import FIXTURES, describe
from predict_mov0020 import LONG_WAIT_CALLBACKS, waiting
from trace_contract import ROOT, load, write_json

STRAIGHT = 'MOV-0021-e'  # j without partial routes; u0 travels east as j's waiting unit did


def grade(predictions):
    variants, alive = {}, {name: True for name in ('heading', 'rotation', 'line')}
    for label, row in predictions['variants'].items():
        observed = describe(load(FIXTURES / f'{label}.json'))
        waits = waiting(observed)
        named = {name: [unit] == waits for name, unit in row['hypotheses'].items()}
        for name, ok in named.items():
            alive[name] = alive[name] and ok
        variants[label] = dict(question=row['question'], wc3=observed, wc3_waits=waits, hypotheses=row['hypotheses'],
                               supported=named, model_waits=row['model_waits'],
                               model_matches_waits=row['model_waits'] == waits)
    survivors = [name for name, ok in alive.items() if ok]
    partial = variants[STRAIGHT]['wc3_waits'] == ['u0']
    return dict(long_wait_callbacks=LONG_WAIT_CALLBACKS, variants=variants, surviving=survivors,
                straight_matches_j=partial,
                status='ONE-SURVIVES' if len(survivors) == 1 else 'NONE-SURVIVES' if not survivors else 'UNRESOLVED')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--predictions', type=Path, default=ROOT / 'results/mov-0021/predictions.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = grade(load(args.predictions))
    write_json(args.out, result)
    for label, v in result['variants'].items():
        print(f"{label}: WC3 waiting {v['wc3_waits']}; hypotheses {v['hypotheses']}; model {v['model_waits']}")
    print(f"surviving: {result['surviving']}; e matches j: {result['straight_matches_j']}")
    return int(result['status'] != 'ONE-SURVIVES')


if __name__ == '__main__':
    raise SystemExit(main())

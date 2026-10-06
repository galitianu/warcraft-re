#!/usr/bin/env python3
"""MOV-0019 (docs/mov-0019.md#decision-rules-before-capture): grade the predictions.

Reads only the committed predictions.json and the WC3 fixtures. For each variant it
finds which pre-registered outcomes match WC3 at P3 level: the same side, waits
(first and last callback) and arrival callback, final position within 1 unit and the
same final order. It reports the footprint and tie results and the candidates that
survive every variant. Writes grading.json; exit 0 when the adopted set survives.
"""
import argparse
from pathlib import Path

from predict_mov0019 import matches, wc3_summary
from trace_contract import ROOT, load, write_json

# docs/mov-0019.md: which way each tie rule sends u0 (e travels west, f north).
TIE_RULES = {'model (diagonal-late walk, clockwise from east)': dict(e='south', f='east'),
             "traveller's right": dict(e='north', f='east'), "traveller's left": dict(e='south', f='west')}


def direction(variant, side):
    """Compass side of the blocker u0 took: e travels west, f north."""
    if side == 'through':
        return 'through'
    return {('e', 'left'): 'south', ('e', 'right'): 'north',
            ('f', 'left'): 'west', ('f', 'right'): 'east'}[(variant, side)]


def grade(predictions):
    variants, survivors = {}, set(range(len(predictions['candidates'])))
    for label, row in predictions['variants'].items():
        observed = wc3_summary(label)
        matching = [i for i, outcome in enumerate(row['outcomes']) if matches(observed, outcome)]
        survivors &= {c for c, o in enumerate(row['candidate_outcome']) if o in matching}
        variants[label] = dict(question=row['question'], wc3=observed, matching_outcomes=matching,
                               adopted_outcome=row['adopted_outcome'],
                               adopted_matches=row['adopted_outcome'] in matching)
    footprint = {label: variants[label]['adopted_matches'] for label in ('MOV-0019-a', 'MOV-0019-b', 'MOV-0019-c', 'MOV-0019-d')}
    sides = {v: direction(v, variants[f'MOV-0019-{v}']['wc3']['u0']['side']) for v in 'ef'}
    keys = predictions['candidate_keys']
    alive = [dict(zip(keys, predictions['candidates'][i])) for i in sorted(survivors)]
    adopted = predictions['adopted_index'] in survivors
    return dict(variants=variants, footprint=dict(confirmed=all(footprint.values()), by_variant=footprint,
                                                  c_equals_b=variants['MOV-0019-c']['wc3']['u0'] == variants['MOV-0019-b']['wc3']['u0']),
                tie=dict(observed=sides, rules={name: rule == sides for name, rule in TIE_RULES.items()}),
                corridor=dict(survivors=len(alive), adopted_survives=adopted,
                              ranges={k: [min(s[k] for s in alive), max(s[k] for s in alive)] for k in keys} if alive else None,
                              candidates=alive),
                status='ADOPTED-SURVIVES' if adopted else 'REFIT' if alive else 'REFUTED')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--predictions', type=Path, default=ROOT / 'results/mov-0019/predictions.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = grade(load(args.predictions))
    write_json(args.out, result)
    for label, v in result['variants'].items():
        print(f"{label}: WC3 matches outcomes {v['matching_outcomes'] or 'none'} (adopted {v['adopted_outcome']})")
    print(f"footprint confirmed: {result['footprint']['confirmed']}; tie observed {result['tie']['observed']}: "
          f"{result['tie']['rules']}; corridor: {result['corridor']['survivors']} survivors, "
          f"adopted survives: {result['corridor']['adopted_survives']}")
    return int(not result['corridor']['adopted_survives'])


if __name__ == '__main__':
    raise SystemExit(main())

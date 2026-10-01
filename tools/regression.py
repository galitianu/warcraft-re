#!/usr/bin/env python3
"""Assess a completed canonical comparison: 0 no regression, 1 regression, 2 invalid.

This is separate from compare_traces' compatibility verdict. No reference or
property tolerance is changed. See docs/phase-4-ci.md for the protected metrics.
"""
import argparse
from pathlib import Path

from trace_contract import BUILD, ROOT, TOLERANCES, load, write_json

CASES = [f'MOV-{n:04d}' for n in range(1, 11)]
GROUPS = ('properties', 'action_properties', 'event_properties')


def tolerance(group, prop):
    if group == 'properties':
        return TOLERANCES[prop]
    if group == 'action_properties':
        return TOLERANCES.get(prop.removeprefix('target_'), 0)
    key = prop.rsplit('.', 1)[-1]
    return TOLERANCES['facing' if key.startswith('facing') else
                      'x' if key.startswith('x_') else 'y' if key.startswith('y_') else 't']


def validate_report(report):
    """Reject absent/partial reports rather than accepting an empty suite."""
    if report['reference_build'] != BUILD or report['tolerances'] != TOLERANCES:
        raise ValueError('wrong reference build or changed tolerances')
    if [c['case'] for c in report['cases']] != CASES:
        raise ValueError('expected all ten ordered MOV cases')
    statuses = []
    for case in report['cases']:
        if set(case['properties']) != set(TOLERANCES) or set(case['action_properties']) != {
                'callback', 'unit', 'command', 'accepted', 't', 'target_x', 'target_y'}:
            raise ValueError('missing/unsupported compared properties')
        for group in GROUPS:
            for prop, stat in case[group].items():
                tolerance(group, prop)
                for key in ('samples', 'failures'):
                    if type(stat[key]) is not int or not 0 <= stat[key] <= 50000:
                        raise ValueError(f'invalid {key}')
                if stat['failures'] > stat['samples']:
                    raise ValueError('failures exceed observations')
                status = stat['status']
                if status not in ('PASS', 'FAIL', 'UNOBSERVED', 'NOT-APPLICABLE'):
                    raise ValueError('unknown property verdict')
                if (status == 'FAIL') != bool(stat['failures']):
                    raise ValueError('inconsistent property verdict')
                if bool(stat['first_divergence']) != bool(stat['failures']):
                    raise ValueError('missing/unexpected first divergence')
                if stat['first_divergence']:
                    first = stat['first_divergence']
                    if type(first['reference_seq']) is not int or not 0 <= first['reference_seq'] <= 50000:
                        raise ValueError('invalid first divergence sequence')
                    if type(first['callback']) is not int or not 0 <= first['callback'] <= 20000:
                        raise ValueError('invalid first divergence callback')
                    if type(first['delta']) not in (int, float) or not abs(first['delta']) <= 2e9:
                        raise ValueError('invalid first divergence delta')
                if status in ('UNOBSERVED', 'NOT-APPLICABLE') and stat['samples']:
                    raise ValueError('unobserved property has observations')
                for value in [stat['max_abs_delta'], *stat['max_abs_delta_by_unit'].values(),
                              *stat['final_delta_by_unit'].values()]:
                    if type(value) not in (int, float) or not abs(value) <= 2e9:
                        raise ValueError('invalid/overflowing report delta')
        failed = bool(case['structural_differences']) or any(
            s['failures'] for g in GROUPS for s in case[g].values())
        if case['status'] != ('FAIL' if failed else 'PASS'):
            raise ValueError('inconsistent case verdict')
        statuses.append(case['status'])
    if report['status'] != ('FAIL' if 'FAIL' in statuses else 'PASS'):
        raise ValueError('inconsistent suite verdict')
    return report


def assess(baseline, actual):
    validate_report(baseline); validate_report(actual)
    changes = []

    def change(path, metric, old, new, classification):
        if old != new:
            changes.append(dict(path=path, metric=metric, before=old, after=new,
                                classification=classification))

    def fixed(path, metric, old, new):
        change(path, metric, old, new, 'REGRESSION')

    def smaller(path, metric, old, new, tol=0):
        classification = ('REGRESSION' if new > max(old, tol) else
                          'IMPROVEMENT' if new < old and old > tol else 'WITHIN-TOLERANCE')
        change(path, metric, old, new, classification)

    fixed('suite', 'timing_variants', baseline['timing_variants'], actual['timing_variants'])
    for key in ('observation_phase', 'seed'):
        fixed('suite', key, baseline['identity']['build'][key], actual['identity']['build'][key])
    for old, new in zip(baseline['cases'], actual['cases']):
        path = old['case']
        for key in ('map_revision', 'observation_phase', 'reference_sha256', 'reference_records',
                    'actual_records', 'reference_samples', 'actual_samples', 'unobserved_properties'):
            fixed(path, key, old[key], new[key])
        # A removed known structural discrepancy is an improvement; a new/changed
        # discrepancy is a regression. These are never hidden by numerical FAIL.
        removed = [s for s in old['structural_differences'] if s not in new['structural_differences']]
        added = [s for s in new['structural_differences'] if s not in old['structural_differences']]
        if removed or added:
            changes.append(dict(path=path, metric='structural_differences', before=removed,
                                after=added, classification='REGRESSION' if added else 'IMPROVEMENT'))
        for group in GROUPS:
            fixed(path, f'{group}.keys', sorted(old[group]), sorted(new[group]))
            for prop in old[group].keys() & new[group].keys():
                a, b = old[group][prop], new[group][prop]
                pp, tol = f'{path}/{group}/{prop}', tolerance(group, prop)
                fixed(pp, 'samples', a['samples'], b['samples'])
                smaller(pp, 'failures', a['failures'], b['failures'])
                if a['status'] in ('UNOBSERVED', 'NOT-APPLICABLE') or b['status'] in ('UNOBSERVED', 'NOT-APPLICABLE'):
                    fixed(pp, 'status', a['status'], b['status'])
                smaller(pp, 'max_abs_delta', a['max_abs_delta'], b['max_abs_delta'], tol)
                for metric in ('max_abs_delta_by_unit', 'final_delta_by_unit'):
                    fixed(pp, f'{metric}.units', sorted(a[metric]), sorted(b[metric]))
                    for unit in a[metric].keys() & b[metric].keys():
                        smaller(pp, f'{metric}/{unit}', abs(a[metric][unit]), abs(b[metric][unit]), tol)
                        if a[metric][unit] != b[metric][unit] and abs(a[metric][unit]) == abs(b[metric][unit]):
                            change(pp, f'{metric}/{unit}.sign', a[metric][unit], b[metric][unit], 'REGRESSION' if abs(b[metric][unit]) > tol else 'WITHIN-TOLERANCE')
                af, bf = a['first_divergence'], b['first_divergence']
                if af and bf:
                    # Location includes source sequence (and therefore watch order)
                    # at equal callbacks. A later failure is an improvement.
                    change(pp, 'first_location', [af['reference_seq'], af['callback'], af['unit']],
                           [bf['reference_seq'], bf['callback'], bf['unit']],
                           'REGRESSION' if bf['reference_seq'] <= af['reference_seq'] else 'IMPROVEMENT')
                    if af['reference_seq'] == bf['reference_seq']:
                        smaller(pp, 'first_abs_delta', abs(af['delta']), abs(bf['delta']), tol)
                elif af != bf:
                    change(pp, 'first_divergence', af, bf, 'REGRESSION' if bf else 'IMPROVEMENT')
    regressions = [c for c in changes if c['classification'] == 'REGRESSION']
    improvements = [c for c in changes if c['classification'] == 'IMPROVEMENT']
    return dict(policy='wc3-regression-v1', regression_verdict='FAIL' if regressions else 'PASS',
                compatibility_verdict=actual['status'],
                compatibility_passes=sum(c['status'] == 'PASS' for c in actual['cases']),
                cases=10, regressions=regressions, improvements=improvements, changes=changes,
                baseline_identity=baseline['identity'], actual_identity=actual['identity'])


def markdown(report):
    lines = ['# Regression assessment', '',
             f"Regression gate: **{report['regression_verdict']}**; compatibility: "
             f"**{report['compatibility_passes']}/10 PASS** ({report['compatibility_verdict']}).", '',
             f"{len(report['regressions'])} regressions, {len(report['improvements'])} improvements; "
             f"{len(report['changes'])} total protected-metric changes.", '',
             '| Property | Metric | Before | After | Assessment |', '|---|---|---|---|---|']
    for c in report['changes']:
        lines.append(f"| {c['path']} | {c['metric']} | {c['before']} | {c['after']} | {c['classification']} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = assess(load(args.baseline), load(args.actual))
        write_json(args.out.with_suffix('.json'), report)
        args.out.with_suffix('.md').write_text(markdown(report))
        print(f"regression {report['regression_verdict']}; compatibility {report['compatibility_passes']}/10 PASS")
        return int(report['regression_verdict'] == 'FAIL')
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        parser.exit(2, f'regression: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

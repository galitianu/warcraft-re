#!/usr/bin/env python3
"""Compare canonical v1 traces; 0 compatible, 1 incompatible, 2 invalid input."""
import argparse
from pathlib import Path
import sys

from compare_movement import delta, format_first
from trace_contract import BUILD, ROOT, TOLERANCES, GENERATED_SHAPES, RETAINED_MOV, load, sha256, validate, write_json


def samples(trace):
    return [r for r in trace['records'] if r['kind'] == 'SAMPLE']


def actions(trace):
    return [r for r in trace['records'] if r['kind'] == 'ACTION']


def stats():
    return dict(samples=0, failures=0, max_abs_delta=0, max_abs_delta_by_unit={},
                final_delta_by_unit={}, first_divergence=None, status='PASS')


def divergence(ref, act, prop, rv, av, difference, tolerance, sample_index=None):
    return dict(reference_seq=ref['seq'], actual_seq=act['seq'], kind=ref['kind'],
                sample_index=sample_index, callback=ref['callback'], unit=ref.get('unit'), property=prop,
                reference_t=ref['time']['reported'] or ref['time']['requested'],
                actual_t=act['time']['reported'] or act['time']['requested'],
                reference_time=ref['time'], actual_time=act['time'],
                reference=rv, actual=av, delta=difference, tolerance=tolerance)


def accumulate(stat, ref, act, prop, rv, av, difference, tolerance, sample_index=None):
    stat['samples'] += 1
    unit = ref.get('unit', 'event')
    stat['max_abs_delta'] = max(stat['max_abs_delta'], abs(difference))
    stat['max_abs_delta_by_unit'][unit] = max(stat['max_abs_delta_by_unit'].get(unit, 0), abs(difference))
    stat['final_delta_by_unit'][unit] = difference
    if abs(difference) > tolerance:
        stat['status'] = 'FAIL'
        stat['failures'] += 1
        if stat['first_divergence'] is None:
            stat['first_divergence'] = divergence(ref, act, prop, rv, av, difference, tolerance, sample_index)


def compare(reference, actual):
    # Each producer is validated against the retained experiment shape independently.
    validate(reference); validate(actual)
    if reference['identity']['engine'] != 'wc3':
        raise ValueError('reference must be the verified WC3 build')
    if reference['scenario'] != actual['scenario']:
        # A new packaging revision can reproduce the SAME scenario bytes. The
        # relation is explicit and independently registered, never inferred from
        # matching samples or relaxed identity/tolerance checks.
        label = reference['scenario']['map_revision']
        exp = reference['scenario']['experiment']
        same_shape = {k: v for k, v in reference['scenario'].items() if k != 'map_revision'} == {
            k: v for k, v in actual['scenario'].items() if k != 'map_revision'}
        same_input = reference['provenance'].get('scenario') == actual['provenance'].get('scenario')
        if not (label in GENERATED_SHAPES and actual['scenario']['map_revision'] == RETAINED_MOV[exp]
                and actual['identity']['engine'] == 'cpp' and same_shape and same_input):
            raise ValueError('incompatible experiment/map revision or scenario bytes')
    refs, acts = samples(reference), samples(actual)
    props = {prop: stats() for prop in TOLERANCES}
    for index, (ref, act) in enumerate(zip(refs, acts)):
        for prop, tolerance in TOLERANCES.items():
            rv = ref['time']['reported'] or ref['time']['requested'] if prop == 't' else ref['values'][prop]
            av = act['time']['reported'] or act['time']['requested'] if prop == 't' else act['values'][prop]
            accumulate(props[prop], ref, act, prop, rv, av, delta(prop, rv, av), tolerance, index)
    structural = []
    for ref, act in zip(reference['units'], actual['units']):
        if ref['type'] != act['type']:
            structural.append(dict(property='unit_type', unit=ref['name'], reference=ref['type'], actual=act['type']))
    ref_actions, act_actions = actions(reference), actions(actual)
    action_props = {prop: stats() for prop in ('callback', 'unit', 'command', 'accepted', 't', 'target_x', 'target_y')}
    if len(ref_actions) != len(act_actions):
        structural.append(dict(property='action_count', reference=len(ref_actions), actual=len(act_actions)))
    for ref, act in zip(ref_actions, act_actions):
        for prop in ('callback', 'unit', 'command', 'accepted'):
            rv, av = ref[prop], act[prop]
            difference = int(av) - int(rv) if prop in ('callback', 'accepted') else int(av != rv)
            accumulate(action_props[prop], ref, act, f'action_{prop}', rv, av, difference, 0)
            if prop in ('callback', 'unit', 'command') and rv != av:
                structural.append(dict(property=f'action_{prop}', reference_seq=ref['seq'], actual_seq=act['seq'], reference=rv, actual=av))
        rv, av = ref['time']['reported'] or ref['time']['requested'], act['time']['reported'] or act['time']['requested']
        accumulate(action_props['t'], ref, act, 'action_t', rv, av, delta('t', rv, av), TOLERANCES['t'])
        if ref['target'] is not None and act['target'] is not None:
            for axis in ('x', 'y'):
                rv, av = ref['target'][axis], act['target'][axis]
                accumulate(action_props[f'target_{axis}'], ref, act, f'target_{axis}', rv, av, delta(axis, rv, av), TOLERANCES[axis])
        elif ref['target'] != act['target']:
            structural.append(dict(property='action_target_kind', reference_seq=ref['seq'], actual_seq=act['seq'], reference=ref['target'], actual=act['target']))
    ref_events = [r for r in reference['records'] if r['kind'] == 'EVENT']
    act_events = [r for r in actual['records'] if r['kind'] == 'EVENT']
    unobserved = []
    event_props = {}
    if actual['identity']['engine'] == 'cpp' and ref_events and not act_events:
        unobserved = sorted({f'{r["name"]}.{key}' for r in ref_events for key in r['values']})
    else:
        if len(ref_events) != len(act_events):
            structural.append(dict(property='event_count', reference=len(ref_events), actual=len(act_events)))
        for ref, act in zip(ref_events, act_events):
            if (ref['callback'], ref['name'], set(ref['values'])) != (act['callback'], act['name'], set(act['values'])):
                structural.append(dict(property='event_order_or_shape', reference_seq=ref['seq'], actual_seq=act['seq']))
                continue
            rv, av = ref['time']['reported'] or ref['time']['requested'], act['time']['reported'] or act['time']['requested']
            accumulate(event_props.setdefault(f'{ref["name"]}.t', stats()), ref, act, f'{ref["name"]}.t', rv, av, delta('t', rv, av), TOLERANCES['t'])
            for key, rv in ref['values'].items():
                prop = f'{ref["name"]}.{key}'
                tol_prop = 'facing' if key.startswith('facing') else 'x' if key.startswith('x_') else 'y' if key.startswith('y_') else 't'
                stat = event_props.setdefault(prop, stats())
                av = act['values'][key]
                accumulate(stat, ref, act, prop, rv, av, delta(tol_prop, rv, av), TOLERANCES[tol_prop])
    # Compare observable interleaving too, not separate lists that could conceal a
    # swapped ACTION/EVENT pair at the same callback. Instrumentation seq differs.
    def observable_order(trace):
        return [(r['kind'], r['callback'], r.get('unit', r.get('name')), r['seq'])
                for r in trace['records'] if r['kind'] in ('SAMPLE', 'ACTION', 'EVENT')
                and not (unobserved and r['kind'] == 'EVENT')]
    reference_order, actual_order = observable_order(reference), observable_order(actual)
    for ref, act in zip(reference_order, actual_order):
        if ref[:3] != act[:3]:
            structural.append(dict(property='observable_record_order', reference_seq=ref[3], actual_seq=act[3],
                                   reference=ref[:3], actual=act[:3]))
            break
    for stat in action_props.values():
        if stat['samples'] == 0:
            stat['status'] = 'UNOBSERVED' if ref_actions else 'NOT-APPLICABLE'
    all_stats = [*props.values(), *action_props.values(), *event_props.values()]
    divergences = [s['first_divergence'] for s in all_stats if s['first_divergence'] is not None]
    first = min(divergences, key=lambda d: d['reference_seq']) if divergences else None
    state_first = next((props[p]['first_divergence'] for p in TOLERANCES if props[p]['first_divergence'] is not None), None)
    state_divergences = [s['first_divergence'] for s in props.values() if s['first_divergence']]
    if state_divergences:
        state_first = min(state_divergences, key=lambda d: d['reference_seq'])
    incompatible = bool(first or structural)
    return dict(case=reference['scenario']['experiment'], map_revision=reference['scenario']['map_revision'],
                status='FAIL' if incompatible else 'PASS',
                scope='declared samples, unit types and ordered commands/targets; unavailable event properties excluded and UNOBSERVED',
                observation_phase=actual['time']['observation_phase'],
                reference_records=len(reference['records']), actual_records=len(actual['records']),
                reference_samples=len(refs), actual_samples=len(acts),
                first_divergence=first, state_first_divergence=state_first,
                properties=props, action_properties=action_props, event_properties=event_props,
                structural_differences=structural, first_structural_divergence=structural[0] if structural else None,
                unobserved_properties=unobserved,
                observation_timing=dict(primary_alignment='callback/unit then ordered actions/events; no resampling',
                                        phase_resolution='unresolved retail update boundary; diagnostic phase never replaces primary',
                                        clock_status=props['t']['status']))


def verify_reference_provenance(reference):
    """Bind CLI reference input to retained independent evidence, not just hashes
    supplied by the same JSON. Direct compare() also supports controlled test data.
    """
    validate(reference)
    manifest_info = reference['provenance']['manifest']
    manifest_path = ROOT / manifest_info['path']
    if sha256(manifest_path) != manifest_info['sha256']:
        raise ValueError('reference manifest digest differs from retained evidence')
    manifest = load(manifest_path)
    for run, expected in zip(reference['provenance']['runs'], manifest['runs']):
        for key in ('run', 'sha256', 'payload_sha256', 'footer'):
            if run[key] != expected[key]:
                raise ValueError(f'reference {key} differs from retained capture manifest')
    for source in [*reference['identity']['source'].values(), reference['identity']['environment']]:
        if sha256(ROOT / source['path']) != source['sha256']:
            raise ValueError('reference source digest differs from retained source')


def compare_suite(reference_root, actual_root, numbers=range(1, 11)):
    cases, identity = [], None
    for n in numbers:
        label = 'MOV-0002-r2' if n == 2 else f'MOV-{n:04d}'
        rp, ap = Path(reference_root) / f'{label}.json', Path(actual_root) / f'MOV-{n:04d}.json'
        ref, act = load(rp), load(ap)
        verify_reference_provenance(ref)
        if identity is None: identity = act['identity']
        if act['identity'] != identity: raise ValueError('mixed suite build/model identities')
        report = compare(ref, act)
        report.update(reference_sha256=sha256(rp), actual_sha256=sha256(ap))
        cases.append(report)
    return dict(reference_build=BUILD, identity=identity, tolerances=TOLERANCES,
                delta_convention='actual minus reference; facing circular [-180,180)',
                status='FAIL' if any(c['status'] == 'FAIL' for c in cases) else 'PASS', cases=cases,
                timing_variants=dict(status='UNOBSERVED', maps=['JASS-0001-p001', 'JASS-0001-p010', 'JASS-0001-p020', 'JASS-0001-p025', 'JASS-0001-p050'],
                                     reason='all retained CLOCKS records normalized; no equivalent C++ JASS/CLOCKS producer'))


def markdown(report):
    lines = ['# Canonical comparison', '', f"Reference `{report['reference_build']}`; {report['identity']['model']['name']}, {report['identity']['build']['observation_phase']}.", '',
             'X/Y 0.001 world unit; circular facing 0.001 degree; current order exact;',
             'clock and action time 0.0000615 s; targets reuse X/Y limits.',
             'Primary callback/unit/action order; no shifts or resampling. Missing CLOCKS: UNOBSERVED.', '',
             '| Case | Verdict | Records WC3 / C++ | Samples | First divergence |', '|---|---|---|---|---|']
    for case in report['cases']:
        lines.append(f"| {case['case']} | {case['status']} | {case['reference_records']} / {case['actual_records']} | {case['actual_samples']} | {format_first(case['first_divergence'])} |")
    for case in report['cases']:
        lines += ['', f"## {case['case']}", '', '| Property | Verdict | Observations / failures | First divergence | Max absolute delta by unit | Final signed delta by unit |', '|---|---|---|---|---|---|']
        for prefix, properties in (('', case['properties']), ('action.', case['action_properties']), ('event.', case['event_properties'])):
            for prop, stat in properties.items():
                lines.append(f"| {prefix}{prop} | {stat['status']} | {stat['samples']} / {stat['failures']} | {format_first(stat['first_divergence'])} | {stat['max_abs_delta_by_unit']} | {stat['final_delta_by_unit']} |")
        lines += ['', f"Structural differences: {case['structural_differences']}", f"Unobserved: {case['unobserved_properties']}"]
    return '\n'.join(lines) + '\n'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=ROOT / 'oracle/canonical' / BUILD)
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--case', choices=[f'MOV-{n:04d}' for n in range(1, 11)], help='compare one declared MOV case')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    try:
        report = compare_suite(args.reference, args.actual, [int(args.case[-4:])] if args.case else range(1, 11))
        if args.json: write_json(args.json, report)
        if args.markdown:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(markdown(report), encoding='utf-8')
        for case in report['cases']: print(f"{case['case']} {case['status']}: {format_first(case['first_divergence'])}")
        return int(report['status'] == 'FAIL')
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError) as error:
        parser.exit(2, f'compare_traces: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

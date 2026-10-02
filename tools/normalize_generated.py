#!/usr/bin/env python3
"""Validate three retained generated-map captures and normalize them losslessly.

Also report exact observation reproduction against the independently authored map.
BEGIN/END revision, declared SETUP and Preload transport are named metadata only.
This does not rewrite controls, captures, fixtures, tolerances or scenario bytes.
"""
import argparse
import hashlib
from pathlib import Path

from normalize_traces import normalize_capture
from oracle_parse import parse
from trace_contract import (BUILD, GENERATED_SHAPES, RETAINED_MOV, ROOT, digest,
                            load, payload, sha256, validate, write_json)

OBSERVED = {'WATCH', 'RUN', 'TICK', 'SAMPLE', 'ACTION', 'EVENT'}


def observations(capture):
    # Keep sequence ORDER, numeric strings, callback indices and the full WATCH
    # properties. Sequence numbers include metadata and are compared separately.
    return [r.split('|')[2:] for r in capture['_records'] if r.split('|')[2] in OBSERVED]


def normalize(label, out):
    if label not in GENERATED_SHAPES:
        raise ValueError('revision needs an independent, manually reviewed shape before normalization')
    base = ROOT / 'oracle/captures' / BUILD / label
    manifest_path = base / 'manifest.json'
    manifest = load(manifest_path)
    exp, callbacks, period, units = GENERATED_SHAPES[label]
    if (manifest['experiment'], manifest['map_label'], manifest['reference_build']) != (exp, label, BUILD):
        raise ValueError('wrong generated capture manifest identity')
    for key in ('map', 'library', 'case', 'environment', 'scenario', 'generation', 'verification'):
        source = manifest[key]
        if sha256(ROOT / source['path']) != source['sha256']:
            raise ValueError(f'{label}: {key} source hash differs')
    scenario = manifest['scenario']
    if scenario['path'] != f'scenarios/{exp}.yaml' or scenario['schema'] != 'wc3-scenario' or scenario['version'] != 1:
        raise ValueError('wrong scenario identity')
    generation = load(ROOT / manifest['generation']['path'])
    generated_input = generation['inputs']
    if len(generated_input) != 1 or generated_input[0] != dict(
            experiment=exp, map_revision=label,
            scenario=dict(path=scenario['path'], sha256=scenario['sha256'], version=1),
            case=dict(file=f'{label}.j', sha256=manifest['case']['sha256'])):
        raise ValueError('generation manifest differs from case/scenario identity')
    checked = manifest['check_map']
    if (not checked['ok'] or not checked['trigger_matches_source'] or not checked['war3map_j_contains_source']
            or checked['war3map_j_runs_init_triggers'] or checked['w3i_format'] != 18
            or checked['sha256'] != manifest['map']['sha256']
            or checked['case_sha256'] != manifest['case']['sha256']
            or checked['library_sha256'] != manifest['library']['sha256']):
        raise ValueError('saved-map verification differs from source identities')
    # Verification is a new read of the selected installation, not availability.
    verification = load(ROOT / manifest['verification']['path'])
    environment = load(ROOT / manifest['environment']['path'])
    if verification['reference_build'] != BUILD or verification['target'] != 'vm' or verification['os_architecture'] != 'ARM64':
        raise ValueError('wrong selected oracle machine/build architecture')
    for installed in environment['files']:
        observed = next((f for f in verification['files'] if f['name'] == installed['name']), None)
        if not observed or observed['sha256'] != installed['sha256']:
            raise ValueError('installation verification differs from selected oracle')
        if 'version' in installed and (observed['version'] != installed['version'] or observed['pe_machine'] != 332):
            raise ValueError('game/editor version or x86 PE identity differs')
    entries = manifest['runs']
    if len(entries) != 3 or [r['run'] for r in entries] != [1, 2, 3]:
        raise ValueError('need exactly three fresh-process retained runs')
    traces, runs, captures = [], [], []
    for entry in entries:
        path = base / entry['file']
        capture = parse(path, experiment=exp, map_label=label)
        if (capture['callbacks'], capture['requested_period'], len(capture['watched'])) != (callbacks, period, units):
            raise ValueError('capture differs from independent shape')
        for key in ('sha256', 'payload_sha256', 'footer'):
            if entry[key] != capture[key]:
                raise ValueError(f'run {entry["run"]}: {key} differs from manifest')
        if entry['map_sha256'] != manifest['map']['sha256'] or not entry['fresh_game_process'] or not entry['previous_output_removed']:
            raise ValueError('capture procedure identity differs')
        traces.append(normalize_capture(capture, manifest))
        captures.append(capture)
        runs.append(dict(run=entry['run'], path=path.relative_to(ROOT).as_posix(), sha256=capture['sha256'],
                         payload_sha256=capture['payload_sha256'], footer=capture['footer'],
                         generated_preload_entries=capture['generated_preload_entries'],
                         fresh_game_process=True, previous_output_removed=True))
    hashes = [digest(payload(t)) for t in traces]
    if len(set(hashes)) != 1:
        raise ValueError('generated WC3 runs disagree; cannot select a representative')
    repeatability = dict(classification='DETERMINISTIC', runs=3, canonical_payload_sha256=hashes,
                         observation_payload_sha256=[r['payload_sha256'] for r in runs],
                         distinct_raw_files=len({r['sha256'] for r in runs}),
                         scope='generated retained map/build/selected Windows 11 Pro ARM64 VM; 3 fresh processes',
                         other_seeds_or_machines='UNKNOWN')
    provenance = dict(manifest=dict(path=manifest_path.relative_to(ROOT).as_posix(), sha256=sha256(manifest_path)),
                      representative_run=1, runs=runs, repeatability=repeatability, scenario=scenario)
    for trace in traces:
        trace['provenance'] = provenance
        validate(trace)
    write_json(out / f'{label}.json', traces[0], compact_records=True)
    control_label = RETAINED_MOV[exp]
    control_path = ROOT / 'oracle/captures' / BUILD / control_label / 'run-01.txt'
    control = parse(control_path, experiment=exp, map_label=control_label)
    before, after = observations(control), observations(captures[0])
    first = next((dict(index=i, control=a, generated=b) for i, (a, b) in enumerate(zip(before, after)) if a != b), None)
    if len(before) != len(after) and first is None:
        i = min(len(before), len(after))
        first = dict(index=i, control=before[i:] or None, generated=after[i:] or None)
    metadata = lambda c: [r for r in c['_records'] if r.split('|')[2] not in OBSERVED]
    return dict(status='PASS' if first is None else 'FAIL', map_revision=label, control_revision=control_label,
                scenario=scenario, completion=traces[0]['completion'], repeatability=repeatability,
                observations=dict(records=len(after), control_sha256=digest(before), generated_sha256=digest(after), first_divergence=first),
                metadata_differences=dict(scope='BEGIN/END map label, SETUP declaration/hash, Preload transport and raw sequence numbers',
                    control_records=metadata(control), generated_records=metadata(captures[0]),
                    control_preload=control['generated_preload_entries'], generated_preload=captures[0]['generated_preload_entries'],
                    control_footer=control['footer'], generated_footers=[c['footer'] for c in captures]),
                fixture_sha256=sha256(out / f'{label}.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', choices=GENERATED_SHAPES, action='append')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        cases = [normalize(label, args.out) for label in args.map or GENERATED_SHAPES]
        status = 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL'
        write_json(args.report, dict(status=status, reference_build=BUILD, cases=cases))
        print(f'Generated capture reproduction {status}: {len(cases)} maps / {len(cases)*3} runs')
        return int(status != 'PASS')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'normalize_generated: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate all 45 Phase 1 captures and write 15 lossless representative fixtures."""
import argparse
import csv
from pathlib import Path

from oracle_parse import parse
from trace_contract import (BUILD, LABELS, ROOT, SCHEMA, counts, digest, load,
                            payload, raw_record, sha256, shape, validate, write_json)


def normalize_capture(capture, manifest):
    exp, callbacks, period, _ = shape(capture['map'])
    records, callback = [], None
    for raw in capture['_records']:
        f = raw.split('|')
        if f[2] == 'TICK':
            callback = int(f[4])
        records.append(raw_record(raw, period, callback))
    return dict(schema=SCHEMA, version=1,
                scenario=dict(experiment=exp, map_revision=capture['map'], callbacks=callbacks, requested_period=period),
                identity=dict(engine='wc3', build=BUILD,
                              source={key: manifest[key] for key in ('map', 'library', 'case')},
                              environment=manifest['environment'],
                              seed=dict(status='unset-unobserved', value=None, retail_equivalent=False), model=None),
                units=capture['watched'],
                time=dict(unit='seconds', position_unit='world-units', facing_unit='degrees',
                          numeric_format='R2SW_6; CLOCKS R2SW_9', clock_duration=capture['clock_duration'],
                          step_us=None, observation_phase='unknown-relative-to-due-update', state_lag_us=None),
                records=records, completion=counts(records), provenance={})


def normalize_all(out):
    summaries = []
    for label in LABELS:
        exp, callbacks, period, units = shape(label)
        base = ROOT / 'oracle/captures' / BUILD / label
        manifest_path = base / 'manifest.json'
        manifest = load(manifest_path)
        if (manifest['experiment'], manifest['map_label'], manifest['reference_build']) != (exp, label, BUILD):
            raise ValueError(f'{label}: wrong manifest identity')
        for key in ('map', 'library', 'case', 'environment'):
            source = manifest[key]
            if sha256(ROOT / source['path']) != source['sha256']:
                raise ValueError(f'{label}: {key} source hash differs')
        if len(manifest['runs']) != 3 or [r['run'] for r in manifest['runs']] != [1, 2, 3]:
            raise ValueError(f'{label}: missing/duplicate manifest runs')
        traces, runs, captures = [], [], []
        for entry in manifest['runs']:
            path = base / entry['file']
            capture = parse(path, experiment=exp, map_label=label)
            if (capture['callbacks'], capture['requested_period'], len(capture['watched'])) != (callbacks, period, units):
                raise ValueError(f'{label}: raw shape differs')
            for key in ('sha256', 'payload_sha256', 'footer'):
                if capture[key] != entry[key]:
                    raise ValueError(f'{label}/{entry["file"]}: manifest {key} differs')
            if entry['map_sha256'] != manifest['map']['sha256'] or not entry['fresh_game_process'] or not entry['previous_output_removed']:
                raise ValueError(f'{label}: manifest run procedure mismatch')
            captures.append(capture)
            traces.append(normalize_capture(capture, manifest))
            runs.append(dict(run=entry['run'], path=path.relative_to(ROOT).as_posix(), sha256=capture['sha256'],
                             payload_sha256=capture['payload_sha256'], footer=capture['footer'],
                             generated_preload_entries=capture['generated_preload_entries'],
                             fresh_game_process=entry['fresh_game_process'], previous_output_removed=entry['previous_output_removed']))
        hashes = [digest(payload(t)) for t in traces]
        if len(set(hashes)) != 1:
            raise ValueError(f'{label}: observation disagreement; cannot select representative')
        # Check both existing CSV projections against exact strings from EVERY run.
        for capture in captures:
            for suffix, key in (('samples', '_samples'), ('events', '_events')):
                path = ROOT / 'oracle/derived' / BUILD / label / f'run-01-{suffix}.csv'
                with path.open(newline='') as source:
                    derived = list(csv.DictReader(source))
                if derived != [{k: str(v) for k, v in row.items()} for row in capture[key]]:
                    raise ValueError(f'{label}: exact {suffix} equality failed')
        repeatability = dict(classification='DETERMINISTIC', runs=3,
                             canonical_payload_sha256=hashes,
                             observation_payload_sha256=[r['payload_sha256'] for r in runs],
                             distinct_raw_files=len({r['sha256'] for r in runs}),
                             scope='retained map/build/Windows 11 Pro ARM64 VM; 3 fresh processes; recorded procedure',
                             other_seeds_or_machines='UNKNOWN')
        provenance = dict(manifest={'path': manifest_path.relative_to(ROOT).as_posix(), 'sha256': sha256(manifest_path)},
                          representative_run=1, runs=runs, repeatability=repeatability)
        for trace in traces:
            trace['provenance'] = provenance
            validate(trace)
        write_json(Path(out) / f'{label}.json', traces[0], compact_records=True)
        summaries.append(dict(map_revision=label, runs_validated=3, exact_samples_and_events_equal=True,
                              completion=traces[0]['completion'], repeatability=repeatability,
                              manifest=provenance['manifest'], runs=runs,
                              fixture_sha256=sha256(Path(out) / f'{label}.json')))
    write_json(Path(out) / 'index.json', dict(build=BUILD, maps=15, runs_validated=45, fixtures=summaries))
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'oracle/canonical' / BUILD)
    args = parser.parse_args()
    try:
        normalize_all(args.out)
        print('Validated 45 retained runs; wrote 15 canonical fixtures and provenance index')
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError, csv.Error) as error:
        parser.exit(2, f'normalize_traces: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

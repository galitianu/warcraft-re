#!/usr/bin/env python3
"""Freeze identities for a verified editor-saved generated map and its raw runs.

Requires mpyq for check_map.py. Run only after authoring and three fresh-process
captures. It refuses to overwrite an existing retained manifest.
"""
import argparse
from pathlib import Path

from generate_oracle import generate
from oracle_parse import parse
from trace_contract import BUILD, EXPERIMENT_SHAPES, GENERATED_SHAPES, ROOT, load, sha256, shape, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', choices=[*GENERATED_SHAPES, *EXPERIMENT_SHAPES], required=True)
    parser.add_argument('--generation', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--codegen', type=Path, required=True)
    parser.add_argument('--rejected-attempt', type=Path, action='append', default=[],
                        help='retained raw output that tooling rejected before its run was logged')
    parser.add_argument('--rejected-reason', help='why the attempts were rejected')
    args = parser.parse_args()
    label = args.map
    experiment = EXPERIMENT_SHAPES.get(label)
    exp, callbacks, period, _ = shape(label)
    if bool(args.rejected_attempt) != bool(args.rejected_reason):
        parser.error('--rejected-attempt and --rejected-reason go together')
    base = ROOT / 'oracle/captures' / BUILD / label
    destination = base / 'manifest.json'
    if destination.exists():
        parser.error('manifest exists; never overwrite retained evidence')
    from check_map import check
    case = Path(f'oracle/generated/maps/{label}.j')
    library = Path('oracle/jass/lib/oracle-v1.j')
    map_path = Path(f'oracle-maps/{label}.w3m')
    scenario = Path(experiment['scenario'] if experiment else f'scenarios/{exp}.yaml')
    # Do not bind a pasted/edited case to an unrelated generation manifest.
    cases, expected_generation = generate(args.codegen, [scenario], label)
    if cases[label + '.j'] != case.read_bytes() or load(args.generation) != expected_generation:
        parser.error('generated case or generation manifest differs from the exact scenario')
    checked = check(map_path, library, case)
    if not checked['ok']:
        parser.error('saved map does not contain exactly library + generated case')
    def source(path):
        return dict(path=path.as_posix(), sha256=sha256(path))
    attempts = []
    for attempt in args.rejected_attempt:
        if attempt.parent != base.relative_to(ROOT) or not attempt.name.startswith('attempt-'):
            parser.error('rejected attempts must be attempt-*.txt in the capture directory')
        report = parse(ROOT / attempt, map_label=label)
        attempts.append(dict(file=attempt.name, sha256=report['sha256'], payload_sha256=report['payload_sha256'],
                             footer=report['footer'], reason=args.rejected_reason))
    manifest = dict(experiment=exp, map_label=label, reference_build=BUILD,
                    definition=experiment['definition'] if experiment else 'docs/phase-6-generation.md',
                    procedure='docs/phase-1-procedure.md',
                    map=dict(**source(map_path), bytes=map_path.stat().st_size), library=source(library), case=source(case),
                    scenario=dict(schema='wc3-scenario', version=2 if experiment else 1, **source(scenario)),
                    generation=source(args.generation), verification=source(args.verification),
                    environment=source(Path(f'oracle/environment/{BUILD}.json')), check_map=checked,
                    rng_seed='not set; retail seed influence unobserved',
                    sampling=dict(requested_period_seconds=period, callbacks=callbacks,
                                  clock_duration_seconds='1000', units='seconds, world-units, degrees',
                                  numeric_format='R2SW(value,1,6)'),
                    transport='rdpipe pull; SHA-256 checked by transport', runs=load(base / 'runs.json'))
    if experiment:
        manifest['sampling']['start_seconds'] = f"{experiment['start_us'] / 1e6:g}"
        manifest['sampling']['state_event'] = 'STATE c10_9/x_9/y_9/facing_9, R2SW(value,1,9); 10 s clock from setup'
    if attempts:
        manifest['rejected_attempts'] = attempts
    # Validate all evidence before committing the manifest. Normalization reads a
    # retained manifest, so write it temporarily and remove only on validation error.
    write_json(destination, manifest)
    try:
        from normalize_generated import normalize
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            report = normalize(label, Path(tmp))
        if report['status'] != 'PASS':
            print('Observed reproduction divergence; manifest retained for investigation')
            return 1
    except Exception:
        destination.unlink()
        raise
    print(f'{label}: verified map, scenario, installation and three fresh runs recorded')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

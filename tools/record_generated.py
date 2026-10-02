#!/usr/bin/env python3
"""Freeze identities for a verified editor-saved generated map and its raw runs.

Requires mpyq for check_map.py. Run only after authoring and three fresh-process
captures. It refuses to overwrite an existing retained manifest.
"""
import argparse
from pathlib import Path

from generate_oracle import generate
from trace_contract import BUILD, GENERATED_SHAPES, ROOT, load, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', choices=GENERATED_SHAPES, required=True)
    parser.add_argument('--generation', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--codegen', type=Path, required=True)
    args = parser.parse_args()
    label = args.map
    exp = GENERATED_SHAPES[label][0]
    base = ROOT / 'oracle/captures' / BUILD / label
    destination = base / 'manifest.json'
    if destination.exists():
        parser.error('manifest exists; never overwrite retained evidence')
    from check_map import check
    case = Path(f'oracle/generated/maps/{label}.j')
    library = Path('oracle/jass/lib/oracle-v1.j')
    map_path = Path(f'oracle-maps/{label}.w3m')
    scenario = Path(f'scenarios/{exp}.yaml')
    # Do not bind a pasted/edited case to an unrelated generation manifest.
    cases, expected_generation = generate(args.codegen, [scenario], label)
    if cases[label + '.j'] != case.read_bytes() or load(args.generation) != expected_generation:
        parser.error('generated case or generation manifest differs from the exact scenario')
    checked = check(map_path, library, case)
    if not checked['ok']:
        parser.error('saved map does not contain exactly library + generated case')
    def source(path):
        return dict(path=path.as_posix(), sha256=sha256(path))
    manifest = dict(experiment=exp, map_label=label, reference_build=BUILD,
                    definition='docs/phase-6-generation.md', procedure='docs/phase-1-procedure.md',
                    map=dict(**source(map_path), bytes=map_path.stat().st_size), library=source(library), case=source(case),
                    scenario=dict(schema='wc3-scenario', version=1, **source(scenario)),
                    generation=source(args.generation), verification=source(args.verification),
                    environment=source(Path(f'oracle/environment/{BUILD}.json')), check_map=checked,
                    rng_seed='not set; retail seed influence unobserved',
                    sampling=dict(requested_period_seconds=GENERATED_SHAPES[label][2], callbacks=GENERATED_SHAPES[label][1],
                                  clock_duration_seconds='1000', units='seconds, world-units, degrees',
                                  numeric_format='R2SW(value,1,6)'),
                    transport='rdpipe pull; SHA-256 checked by transport', runs=load(base / 'runs.json'))
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

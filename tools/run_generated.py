#!/usr/bin/env python3
"""Close the scenario -> WC3 fixture / same scenario -> C++ comparison loop.

Authoring/capture remain the documented rdpipe steps. This local/CI flow validates
all retained generated captures, reproduces canonical fixtures and compares the
scenario-driven runner under the existing contract and fixed tolerances.
"""
import argparse
import os
from pathlib import Path
import subprocess

from compare_traces import compare, verify_reference_provenance
from normalize_generated import normalize
from trace_contract import BUILD, GENERATED_SHAPES, ROOT, load, sha256, write_json

FIXTURES = ROOT / 'oracle/canonical-generated' / BUILD


def run(runner, out, reports, check=True):
    reports.mkdir(parents=True, exist_ok=True)
    cases = []
    for label, (exp, _, _, _) in GENERATED_SHAPES.items():
        reproduction = normalize(label, out / 'references')
        fixture = out / 'references' / f'{label}.json'
        if check and fixture.read_bytes() != (FIXTURES / f'{label}.json').read_bytes():
            raise ValueError(f'{label}: regenerated fixture differs from retained bytes')
        actual = out / 'traces' / label
        result = subprocess.run([str(Path(runner).resolve()), '--scenario', f'scenarios/{exp}.yaml',
                                 '--model', 'v4', '--seed', '1', '--out', str(actual.resolve())],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError(result.stderr)
        reference = load(fixture)
        verify_reference_provenance(reference)
        trace = load(actual / f'{exp}.json')
        comparison = compare(reference, trace)
        comparison.update(reference_sha256=sha256(fixture), actual_sha256=sha256(actual / f'{exp}.json'))
        cases.append(dict(map_revision=label, scenario=reference['provenance']['scenario'],
                          status='PASS' if reproduction['status'] == comparison['status'] == 'PASS' else 'FAIL',
                          reproduction=reproduction, comparison=comparison))
    status = 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL'
    write_json(reports / 'generated-loop.json', dict(status=status, reference_build=BUILD, cases=cases))
    (reports / 'generated-loop.md').write_text('\n'.join([
        '# Generated scenario loop', '', f'Gate: **{status}**.', '',
        'Exact WC3 observation reproduction includes WATCH speeds, RUN, TICK clock strings, SAMPLE and ordered ACTION/EVENT records.',
        'C++ uses the exact same scenario bytes; unchanged tolerances. Packaging revisions are explicitly registered.', '',
        '| Revision | Fresh WC3 runs | Observation reproduction | C++ comparison |', '|---|---|---|---|',
        *[f"| {c['map_revision']} | 3 payload-identical | {c['reproduction']['status']} | {c['comparison']['status']} |" for c in cases]
    ]) + '\n', encoding='utf-8', newline='\n')
    print(f'Generated scenario loop {status}: {len(cases)} maps / {len(cases)*3} WC3 runs')
    return int(status != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, default=ROOT / 'build' / ('wc3test.exe' if os.name == 'nt' else 'wc3test'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--write-fixtures', action='store_true', help='first normalization only; capture changes are never automatic')
    args = parser.parse_args()
    try:
        code = run(args.runner, args.out, args.reports, check=not args.write_fixtures)
        if args.write_fixtures:
            # First creation only: refuse to overwrite already-retained fixtures.
            for label in GENERATED_SHAPES:
                dest = FIXTURES / f'{label}.json'
                if dest.exists():
                    raise ValueError(f'{dest}: retained fixture exists; refusing to overwrite')
            FIXTURES.mkdir(parents=True, exist_ok=True)
            for label in GENERATED_SHAPES:
                (FIXTURES / f'{label}.json').write_bytes((args.out / 'references' / f'{label}.json').read_bytes())
        return code
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_generated: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

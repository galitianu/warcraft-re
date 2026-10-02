#!/usr/bin/env python3
"""Generate deterministic case JASS with the same v1 parser as wc3test.

No captures, fixtures or C++ trace output are read. World Editor packages the map
separately; check_map.py verifies the saved map before capture.
"""
import argparse
import os
from pathlib import Path
import subprocess

from trace_contract import ROOT, load, sha256, write_json

BOUNDS = ROOT / 'oracle/template-bounds.json'
GOLDENS = ROOT / 'oracle/generated/v1'


def generate(codegen, paths, revision=None):
    template = load(BOUNDS)
    if sha256(ROOT / template['template']['path']) != template['template']['sha256']:
        raise ValueError('template differs from the decoded bounds report; re-extract and review its bounds')
    bounds = [str(template['playable_bounds'][k]) for k in ('min_x', 'max_x', 'min_y', 'max_y')]
    paths = [file for path in paths for file in (sorted(path.glob('*.yaml')) if path.is_dir() else [path])]
    if not paths or (revision and len(paths) != 1):
        raise ValueError('need scenarios; --map-revision requires one scenario file')
    result, inputs = {}, []
    for path in paths:
        command = [str(Path(codegen).resolve()), str(path), *bounds, template['template']['sha256']]
        if revision:
            command.append(revision)
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=30)
        if process.returncode:
            raise ValueError(process.stderr.decode('utf-8').strip())
        text = process.stdout
        if b'\r' in text or not text.endswith(b'\n'):
            raise ValueError('generator must emit LF-only, final-newline JASS on every platform')
        # Identity comes from the validated generator output, not a second YAML parser.
        import re
        begin = re.search(rb'call OracleBegin\("([A-Z]+-\d{4})", "([A-Za-z0-9-]+)", 1000\)', text)
        if not begin:
            raise ValueError('generator output missing BEGIN')
        experiment, label = (p.decode('ascii') for p in begin.groups())
        if label in result or experiment in [i['experiment'] for i in inputs]:
            raise ValueError('duplicate scenario experiment/revision')
        result[label + '.j'] = text
        import hashlib
        inputs.append(dict(experiment=experiment, map_revision=label,
                           scenario=dict(path=path.as_posix(), sha256=sha256(path), version=1),
                           case=dict(file=label + '.j', sha256=hashlib.sha256(text).hexdigest())))
    return result, dict(generator='oracle_codegen-v1', template=template['template'],
                        template_bounds_sha256=sha256(BOUNDS),
                        sources={name: sha256(ROOT / name) for name in (
                            'tools/oracle_codegen/main.cpp', 'tools/wc3test/Scenario.cpp',
                            'tools/wc3test/Scenario.h', 'tools/generate_oracle.py')}, inputs=inputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codegen', type=Path, default=ROOT / 'build' / ('oracle_codegen.exe' if os.name == 'nt' else 'oracle_codegen'))
    parser.add_argument('--scenario', type=Path, action='append', required=True)
    parser.add_argument('--map-revision', help='new packaging revision; scenario bytes are unchanged')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check', action='store_true', help='require byte identity with the committed goldens')
    args = parser.parse_args()
    if not args.out and not args.check:
        parser.error('need --out and/or --check')
    try:
        files, manifest = generate(args.codegen, args.scenario, args.map_revision)
        if args.check:
            if {p.name for p in GOLDENS.glob('*.j')} != set(files):
                raise ValueError('golden JASS set differs from the scenario set')
            for name, text in files.items():
                if (GOLDENS / name).read_bytes() != text:
                    raise ValueError(f'{name}: generated JASS differs from golden')
            if load(GOLDENS / 'manifest.json') != manifest:
                raise ValueError('golden generation manifest differs')
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            for name, text in files.items():
                (args.out / name).write_bytes(text)
            write_json(args.out / 'manifest.json', manifest)
        print(f'Generated {len(files)} cases' + ('; committed goldens byte-identical' if args.check else ''))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f'generate_oracle: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())

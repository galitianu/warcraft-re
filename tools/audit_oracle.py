#!/usr/bin/env python3
"""Audit generated cases against unchanged hand-written JASS, without scenarios.

Compare ordered statements, control flow, and literal API arguments. Only local
unit/function names, comments, null cleanup and declared SETUP metadata are
normalized. Unknown executable statements fail rather than being skipped.
"""
import argparse
from pathlib import Path
import re

from trace_contract import ROOT, RETAINED_MOV, sha256, write_json

TOKEN = re.compile(r'"[^"\r\n]*"|\x27[^\x27\r\n]*\x27|[A-Za-z_][A-Za-z_0-9]*|-?\d+(?:\.\d+)?|==|[(),+\-=]')


def statements(path):
    source = Path(path).read_text(encoding='ascii')
    functions, metadata, aliases, local_units = [], [], {}, set()
    current = None
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        if line.startswith('function '):
            name = line.split()[1]
            role = 'hook' if name.endswith('Hook') else 'start' if name.endswith('Start') else 'bootstrap'
            if role == 'bootstrap' and name != 'InitTrig_Melee_Initialization':
                raise ValueError(f'{path}: unknown function {name}')
            aliases, current, local_units = {}, [], set()
            functions.append(dict(role=role, statements=current))
            continue
        if line == 'endfunction':
            current = None
            continue
        if current is None:
            raise ValueError(f'{path}: executable text outside a function')
        if line.startswith('local unit '):
            match = re.fullmatch(r'local unit (\w+)(?: = OracleUnit\((\d+)\))?', line)
            if not match:
                raise ValueError(f'{path}: unknown local declaration: {line}')
            local_units.add(match[1])
            if match[2] is None:
                continue
            aliases[match[1]] = 'unit' + match[2]
            line = 'bind ' + aliases[match[1]] + ' = OracleUnit(' + match[2] + ')'
        elif re.fullmatch(r'set \w+ = null', line) and line.split()[1] in local_units:
            continue
        elif ' = CreateUnit(' in line:
            name = line.split()[1]
            aliases[name] = 'unit' + str(len(aliases))
        if line.startswith('call OracleSetup('):
            metadata.append(dict(statement=line, role=role, after_statement=len(current)))
            continue
        if not (line.startswith(('call ', 'set ', 'if OracleCallback() == ', 'elseif OracleCallback() == ', 'bind ')) or line == 'endif'):
            raise ValueError(f'{path}: unknown statement {line}')
        tokens = TOKEN.findall(line)
        # Ensure tokenization cannot discard a new operator, suffix or argument.
        if ''.join(tokens) != re.sub(r'\s+', '', line):
            # Quoted SETUP is removed above; other strings contain no spaces.
            raise ValueError(f'{path}: unsupported tokens in {line}')
        tokens = [aliases.get(t, 'Hook' if t.endswith('Hook') else 'Start' if t.endswith('Start') else t) for t in tokens]
        current.append(tokens)
    if [f['role'] for f in functions] != ['hook', 'start', 'bootstrap']:
        raise ValueError(f'{path}: unexpected function order')
    if len(metadata) != 1 or metadata[0]['role'] != 'start':
        raise ValueError(f'{path}: need exactly one SETUP in the start function')
    return functions, metadata


def audit(generated):
    cases = []
    for experiment, control in RETAINED_MOV.items():
        before, after = ROOT / f'oracle/jass/{control}.j', generated / f'{control}.j'
        expected, old_setup = statements(before)
        actual, new_setup = statements(after)
        if expected != actual:
            raise ValueError(f'{experiment}: ordered API/control-flow audit differs\ncontrol={expected}\ngenerated={actual}')
        if [(m['role'], m['after_statement']) for m in old_setup] != [(m['role'], m['after_statement']) for m in new_setup]:
            raise ValueError(f'{experiment}: SETUP moved relative to game API calls')
        cases.append(dict(experiment=experiment, control=dict(path=before.relative_to(ROOT).as_posix(), sha256=sha256(before)),
                          generated=dict(path=after.as_posix(), sha256=sha256(after)),
                          status='PASS', ordered_statements=actual,
                          metadata_differences=dict(control_setup=old_setup, generated_setup=new_setup,
                              explanation='Generated SETUP records ordered declared inputs and their exact scenario hash. Comments, function/local names and null cleanup carry no experiment calls.')))
    return dict(status='PASS', cases=cases, scope='ordered case API calls, literal arguments, callback branches and bootstrap; shared library unchanged')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        write_json(args.out, audit(args.generated))
        print('Ordered API audit PASS: all ten cases')
    except (OSError, ValueError) as error:
        parser.exit(2, f'audit_oracle: {error}\n')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""footman-v4 evidence: canonical, exact-text and state-capture comparisons with WC3.

Runs tools/wc3test --model v4 twice in separate processes (bytes must match),
grades it with the unchanged Phase 3 comparator, compares the R2SW_6 text of
every fixture value (compare_exact.py) and the state of every retained
JASS-0001/MOV-0012 run (compare_states.py). Returns 0 when everything is identical
except the KNOWN sampling-order callbacks below, 1 on any other difference, 2 on
invalid input.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

import compare_exact
import compare_states
from compare_traces import compare_suite, markdown
from trace_contract import BUILD, ROOT, sha256, write_json

# Known, unexplained sampling-order differences (docs/footman-v4-results.md): every
# 1 ms run reads frame k / 5 at these callbacks, and these 10/25 ms callbacks read the
# facing from before their frame's update. Any other difference fails the check.
EARLY_1MS = [15, 20, 25, 30, 35]
KNOWN = {
    'JASS-0001-p010': {'facing': list(range(352, 380, 3))},
    'JASS-0001-p025': {'facing': list(range(64, 149, 6))},
}


def known(run):
    if run.endswith('.txt'):
        return {'x': EARLY_1MS, 'y': EARLY_1MS}
    return KNOWN.get(run, {})


def run_model(runner, dest):
    subprocess.run([str(runner), '--out', str(dest), '--model', 'v4', '--seed', '1'],
                   check=True, stdout=subprocess.DEVNULL, timeout=60)


def exact_markdown(report):
    lines = ['# footman-v4 exact text comparison', '',
             'Each C++ float printed as WC3 R2SW(value, 1, 6) and compared as a string with the',
             'canonical fixture: SAMPLE x/y/facing, current order, and the TICK clock.', '',
             '| Case | x | y | facing | order | clock | Result |', '|---|---|---|---|---|---|---|']
    for case, row in report.items():
        cells = [f"{n - row['different'][k]}/{n}" for k, n in row['compared'].items()]
        lines.append(f"| {case} | " + ' | '.join(cells) + f" | {'identical' if not row['first'] else 'DIFFERENT'} |")
    return '\n'.join(lines) + '\n'


def states_markdown(report):
    lines = ['# footman-v4 against the JASS-0001 and MOV-0012 state captures', '',
             '1 ms runs: R2SW_9 X/Y/facing and every timer field, callback k against frame (k - 1) // 5.',
             'p010-p050: canonical R2SW_6 samples, callback k against frame k * period / 5 ms after its update.',
             'Mismatches are listed, never shifted; "—" means not recorded.', '',
             '| Run | clock | timers | x | y | facing | Mismatched callbacks |', '|---|---|---|---|---|---|---|']
    for run, row in report.items():
        cells = [f"{n - row['different'][k]}/{n}" if k in row['compared'] else '—'
                 for k, n in ((k, row['compared'].get(k, 0)) for k in ('t', 'timers', 'x', 'y', 'facing'))]
        where = sorted({m['callback'] for v in row['mismatches'].values() for m in v})
        lines.append(f'| {run} | ' + ' | '.join(cells) + f" | {where or '—'} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--runner', type=Path, required=True, help='built tools/wc3test')
    parser.add_argument('--states', type=Path, required=True, help='built tools/wc3states')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    args = parser.parse_args()
    try:
        references = ROOT / 'oracle/canonical' / BUILD
        dest = args.out / 'v4'
        run_model(args.runner.resolve(), dest)
        with tempfile.TemporaryDirectory() as temp:
            run_model(args.runner.resolve(), Path(temp))
            for path in sorted(dest.iterdir()):
                if path.read_bytes() != (Path(temp) / path.name).read_bytes():
                    raise ValueError(f'separate process output differs: {path.name}')
        suite = compare_suite(references, dest)
        exact = compare_exact.compare_all(references, dest)
        states = compare_states.compare_all(args.states.resolve(), ROOT / 'oracle/captures' / BUILD)
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, compare_states.Invalid, subprocess.SubprocessError) as error:
        parser.exit(2, f'run_footman_v4: {error}\n')
    reports = args.reports
    reports.mkdir(parents=True, exist_ok=True)
    write_json(reports / 'comparison.json', suite)
    (reports / 'comparison.md').write_text(markdown(suite), encoding='utf-8')
    write_json(reports / 'exact.json', exact)
    (reports / 'exact.md').write_text(exact_markdown(exact), encoding='utf-8')
    write_json(reports / 'states.json', states)
    (reports / 'states.md').write_text(states_markdown(states), encoding='utf-8')
    write_json(reports / 'trace-hashes.json', {p.name: sha256(p) for p in sorted(dest.iterdir())})
    passed = sum(c['status'] == 'PASS' for c in suite['cases'])
    identical = sum(not row['first'] for row in exact.values())
    expected_only = all({k: [m['callback'] for m in v] for k, v in row['mismatches'].items()} == known(run)
                        for run, row in states.items())
    clean = sum(not row['mismatches'] for row in states.values())
    print(f'canonical: {passed}/10 PASS; exact text: {identical}/10 identical; separate process bytes equal')
    print(f'state captures: {len(states)} compared, {clean} identical, '
          f"{'the rest differ only at the known sampling-order callbacks' if expected_only else 'UNEXPECTED differences'}")
    return 0 if passed == 10 and identical == 10 and expected_only else 1


if __name__ == '__main__':
    raise SystemExit(main())

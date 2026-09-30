# Reproduce Phase 3

From a clean native ARM Mac checkout, with CMake ≥3.20, system clang++ and Python 3
standard library. No original game installation, network access, renderer or third
party dependency is required.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/normalize_traces.py --out build/normalized
python3 tools/run_phase3.py --runner build/wc3test --out build/phase3 --reports build/phase3-reports
```

Read the [contract](trace-contract-v1.md) and [results](phase-3-results.md).
`normalize_traces.py` reuses `oracle_parse.py`, verifies manifest/map/library/case/
environment/raw hashes, validates **all 45 Phase 1 runs**, checks exact sample and
event CSV equality for every run, and verifies observation payload equality before
selecting run-01. It writes 15 representative JSON fixtures plus an index with every
run's provenance. Committed fixtures are under
[oracle/canonical](../oracle/canonical/wc3-1.29.2-9231-x86/). Phase 0 remains separate.
Normalization reads no simulation output. Raw captures and CSVs are never rewritten.

The runner emits ten `.json` canonical traces alongside its unchanged sample and
action CSVs and `identity.json`. `World` remains independent of serialization and
references. C++ record sequencing and exact state microseconds are captured when
the runner observes or issues orders; metadata describes the binary and model used.
Model parameter JSON now uses float max_digits10 rather than the historical shorter
identity strings. Observation bytes and simulation behavior are unchanged.

`run_phase3.py` checks regenerated fixture bytes against the committed canonical
files, executes v1/v2/v2-before, validates and compares their traces, verifies every
sample/action CSV hash against Phase 2, and checks **all** legacy per-property counts,
verdicts, first divergences, maxima and final deltas. It also projects canonical
records back to CSV values and checks exact equality, then runs each model in a
second process and checks all 31 output files byte-for-byte. It returns 0 when the
complete evidence pipeline succeeds, including honest FAIL results; malformed
inputs, unreproduced migration or subprocess failure return 2.

To obtain compatibility exit codes directly:

```sh
python3 tools/compare_traces.py --actual build/phase3/v2 \
  --json build/v2-comparison.json --markdown build/v2-comparison.md
# Exit 1: completed comparison; nine movement cases incompatible.
python3 tools/compare_traces.py --actual build/phase3/v2 --case MOV-0001
# Exit 0: completed stationary comparison under its declared scope.
python3 tools/compare_traces.py --actual build/missing
# Exit 2: missing/invalid input, not a gameplay verdict.
```

JSON and Markdown reports retain full-run sample/action statistics, per-unit maxima
and final signed deltas, source/global sequence of each first divergence and explicit
requested/reported/state times. Structural differences have their own diagnostics.
JASS-0001 CLOCKS events are preserved, with unavailable C++ timing observables labelled
UNOBSERVED. `--case` restricts a comparison to one declared manual experiment.

The [results directory](../results/phase-3/) contains raw validation, both models and
phase diagnostic, migration checks, independent-process repeatability, output and
evidence hashes, and phase sensitivity. Regenerate deliberately with
`--reports results/phase-3` and inspect the diff. Trace/build identities include
configured Git revision and dirty state: configure after changing revisions.
Canonical observation payload hashes exclude build/transport metadata, while full
trace file hashes include it. No cross-compiler determinism is claimed.

# Progress

As of 30 September 2026.

**Current stage:** Phase 3 complete; Phase 4 is next.
**Retail observations:** Phase 0's 20 MOV-0002 captures, plus 15 Phase 1 maps × 3
fresh-process captures, all payload-identical within each map.
**C++ compatibility:** MOV-0001 passes; MOV-0002–MOV-0010 fail fixed provisional
tolerances, with complete numeric comparisons and first divergences.
**First release:** v0.0.1 — one Footman's movement compared numerically with WC3.

The [plan](Warcraft-III-Reimplementation-Plan.md) is the detailed roadmap. GitHub
issues hold concrete work; this file records capabilities and the next action.
Repository: [galitianu/warcraft-re](https://github.com/galitianu/warcraft-re), private, main.

## Delivered

**Phase 0** ([issue #1](https://github.com/galitianu/warcraft-re/issues/1),
[evidence](docs/phase-0-capture.md)): the manually authored MOV-0002 map runs
automatically and yields complete WC3 text through native PreloadGen functions, with
20 retained, payload-identical captures. The [salvage assessment](docs/salvage.md)
imported nothing from the old workspace.

**Phase 1** ([issue #2](https://github.com/galitianu/warcraft-re/issues/2)): a manual
oracle library.

- Shared JASS instrumentation [oracle-v1](oracle/jass/lib/oracle-v1.j) provides
  begin/end markers, named units, per-callback samples and ordered action/event
  records. Each map pastes it with one [case file](oracle/jass/) into its single
  custom-text trigger. Header script is avoided because it makes the map require the expansion.
- 15 World Editor maps in [oracle-maps](oracle-maps/): MOV-0001, MOV-0002-r2,
  MOV-0003–MOV-0010, JASS-0001-p001/p010/p020/p025/p050. Definitions:
  [phase-1-experiments.md](docs/phase-1-experiments.md). Each saved map was
  verified to contain exactly the intended source.
- 45 raw captures with manifests under [oracle/captures](oracle/captures/wc3-1.29.2-9231-x86/),
  parsed CSVs under [oracle/derived](oracle/derived/wc3-1.29.2-9231-x86/). Tools:
  [oracle_parse.py](tools/oracle_parse.py), [check_map.py](tools/check_map.py),
  [capture_runs.py](tools/capture_runs.py), [we_author.py](tools/we_author.py),
  [summarize_phase1.py](tools/summarize_phase1.py). The parser rejects altered copies
  and keeps equal-time order ([tests](tools/test_oracle_parse.py)).
- Results: [phase-1-results.md](docs/phase-1-results.md). Reproduction:
  [phase-1-procedure.md](docs/phase-1-procedure.md). Agent notes:
  [agent-wc3-workflow.md](docs/agent-wc3-workflow.md).

Key observations (these setups only):

- MOV-0002-r2 reproduces Phase 0's 502 SAMPLE payloads exactly.
- Phase 0's uneven 0.019958/0.020020 s intervals come from the 1000 s clock's float
  resolution. A 10 s clock shows callbacks within ±1e-6 s of every requested period
  from 0.001 to 0.05 s.
- At 1 ms sampling, Footman position changes about every 0.005 s and facing every
  0.03 s. Different sampling periods observe subsequences of one state sequence.
- `SetUnitMoveSpeed` 100 → 150 and 522 → 400, and the traces move at the reported
  speeds. Straight moves stop 11.87 short of (1000,0).
- New orders cause pauses: 1 frozen callback for a collinear replacement, 3 for a 90°
  redirect, 7 for a 180° redirect, and 6 when starting from 180° facing. `stop` halts
  at once.

**Still unresolved:** mechanisms behind the update cadences, stop distances and turn
thresholds; the simulation quantum; seed effects; expansion-format maps; other
machines; and precision beyond six printed decimals. R2SW's 9-decimal digits are not
exact floats.

**Phase 2** ([issue #3](https://github.com/galitianu/warcraft-re/issues/3)):
a dependency-free CMake C++20 headless world, seeded Random owner, move/stop orders
and all ten movement setups. [Results](docs/phase-2-results.md),
[hypotheses](docs/phase-2-model.md), [build/reproduction](docs/phase-2-procedure.md).
Both model versions and the observation-phase diagnostic have committed reports
and reproducible trace hashes in [results/phase-2](results/phase-2/).

Clean ARM Mac Release build and CTest passed; 17 Python tests passed; separate
executable repetitions matched all 63 output-file hashes. Re-parsed 39 retained
WC3 captures and checked exact derived sample/event equality. MOV-0001 agrees;
v2's MOV-0002 first differs at callback 1 in Y (−0.014648), ending 3.990174 units
behind WC3 in X. All nine movement failures remain under unchanged tolerances.
The numerical v0.0.1 gate is met; no tag created. Arrival, replacement latency,
heading/grid drift, residual facing and long-clock offset remain unresolved.

PR #4 follow-up: numeric overflow in malformed comparator input now returns exit 2
instead of numerical-divergence exit 1. Regression checks cover oversized callback
and unit counts; all 19 Python tests pass. Retained Phase 2 reports remain evidence
of their recorded build and comparison-tool revisions.

Pre-Phase 3 research: [Warsmash movement analysis](docs/warsmash-movement-research.md)
suggests separate movement heading/reported facing and 30 ms movement batches.
Matching game archives confirm Footman defaults 0.6 rad turn rate, 60° propulsion
window and orientation mode 0. These explain turn onset/direction and arrival
counts much better than v2's 135° gate, but remain hypotheses; no C++ changes,
new captures or compatibility passes. Grid/angle drift remains unexplained.
Implementation follow-up: [issue #6](https://github.com/galitianu/warcraft-re/issues/6),
after Phase 3's trace contract in [issue #5](https://github.com/galitianu/warcraft-re/issues/5).

**Phase 3** ([issue #5](https://github.com/galitianu/warcraft-re/issues/5)):
[canonical v1 contract](docs/trace-contract-v1.md), [results](docs/phase-3-results.md),
[reproduction](docs/phase-3-procedure.md). All 45 Phase 1 runs validate independently;
15 [canonical fixtures](oracle/canonical/wc3-1.29.2-9231-x86/) retain exact raw numeric
strings, global sample/action/event order, reported/requested time and all-run
provenance. Both C++ models and before-update diagnostic emit the same contract.

Clean ARM Mac Release build, CTest 1/1 and 35 Python tests passed. All 60 legacy CSV
hashes and 30 Phase 2 state reports match exactly; MOV-0001 passes and nine movement
cases fail unchanged tolerances. Added relative redirect action target deltas;
MOV-0004 retains 53 clock failures from callback 503. 93 output files match separate
process runs. [Evidence](results/phase-3/) records scoped repeatability; C++ CLOCKS
properties remain UNOBSERVED. No fresh captures or movement-model changes.

## Next task: Phase 4 — compatibility CI

Build the headless runner, validate committed canonical references and compare the
ten MOV cases in CI with explicit baseline verdicts (MOV-0001 PASS, nine documented
FAILs). Keep malformed/unsupported input fatal and preserve numerical diagnostics;
add small compiler/configuration and repeatability coverage under named scope.
The first moving primitive improvement is [issue #6](https://github.com/galitianu/warcraft-re/issues/6),
using unchanged fixtures/tolerances and before/after reports. Detailed handoff:
[Phase 3 results](docs/phase-3-results.md#verification-and-phase-4-handoff).

## Roadmap status

| Phase | Capability / acceptance evidence | Status |
|---|---|---|
| 0 | Automatic map experiment with reliably recoverable WC3 text | Complete — [evidence](docs/phase-0-capture.md) |
| 1 | Small manual map library with shared JASS instrumentation and parseable traces | Complete — [results](docs/phase-1-results.md) |
| 2 | Native C++ headless equivalent and ten numerically comparable traces | Complete — [results](docs/phase-2-results.md); nine movement failures retained |
| 3 | Canonical normalized traces and stable comparison contract | Complete — [results](docs/phase-3-results.md); all 45 retained runs validated |
| 4 | C++ compatibility CI against committed WC3 references | Next |
| 5 | Declarative scenarios extracted from repeated manual tests | Planned |
| 6 | One scenario drives C++ and generates a runnable WC3 map | Planned |
| 7 | Reliable unattended VM capture, when manual work becomes costly | Planned |
| 8 | Microscopic tests, sweeps, and measured compatibility expansion | Planned |

Advance with actual artifacts and verification. Infrastructure checks are not gameplay passes.

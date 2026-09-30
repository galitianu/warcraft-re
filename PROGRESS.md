# Progress

As of 30 September 2026.

**Current stage:** Phase 1 complete; Phase 2 is next.
**Retail observations:** Phase 0's 20 MOV-0002 captures, plus 15 Phase 1 maps × 3
fresh-process captures, all payload-identical within each map.
**C++ compatibility:** unobserved; no new engine exists yet.
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

## Next task: Phase 2 — native C++ headless equivalent

Tracked in [issue #3](https://github.com/galitianu/warcraft-re/issues/3).

Build the tiny native ARM Mac headless C++ world (plan §5), without raylib. Run all
ten MOV setups and emit traces with the same fields as the WC3 SAMPLE rows
(callback, time, X, Y, facing, order). Then compare numerically with
`oracle/derived/wc3-1.29.2-9231-x86/`. MOV-0001 and MOV-0002 are the v0.0.1 gate;
MOV-0003–MOV-0010 report pass or first divergence. Treat the observed
0.005 s / 0.03 s cadences as hypotheses to test, not a chosen timestep. A failing
numerical comparison is acceptable progress.

## Roadmap status

| Phase | Capability / acceptance evidence | Status |
|---|---|---|
| 0 | Automatic map experiment with reliably recoverable WC3 text | Complete — [evidence](docs/phase-0-capture.md) |
| 1 | Small manual map library with shared JASS instrumentation and parseable traces | Complete — [results](docs/phase-1-results.md) |
| 2 | Native C++ headless equivalent and two numerically comparable traces | Next |
| 3 | Normalized traces, explicit tolerances, first-divergence report | Planned |
| 4 | C++ compatibility CI against committed WC3 references | Planned |
| 5 | Declarative scenarios extracted from repeated manual tests | Planned |
| 6 | One scenario drives C++ and generates a runnable WC3 map | Planned |
| 7 | Reliable unattended VM capture, when manual work becomes costly | Planned |
| 8 | Microscopic tests, sweeps, and measured compatibility expansion | Planned |

Advance with actual artifacts and verification. Infrastructure checks are not gameplay passes.

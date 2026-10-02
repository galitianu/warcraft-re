# Phase 5 — versioned scenarios

[Issue #12](https://github.com/galitianu/warcraft-re/issues/12), plan
[§8](../Warcraft-III-Reimplementation-Plan.md#8-phase-5--extract-a-declarative-scenario-format).
Contract: [scenario-v1.md](scenario-v1.md). Scenarios: [scenarios/](../scenarios/).

**Behavioral question.** Can a data-driven experiment reproduce the hard-coded
runner's complete ordered observations and actions, through the same World API,
without changing gameplay behavior or depending on the WC3 output being graded?

**Gate.** Migration equivalence and preserved compatibility. A schema adds no
gameplay pass and does not resolve the
[unexplained sampling order](footman-v4-results.md#sampling-order).

Reference: WC3 1.29.2 (9231), x86 32-bit, `wc3-1.29.2-9231-x86`, captured in the
recorded Windows 11 Pro ARM64 VM. No capture, fixture, reference or tolerance was
added or changed. No new map was authored.

## Readiness audit

Sources read: `AGENTS.md`, plan §8–9, `PROGRESS.md`, the Phase 0/1 procedures, all
24 case files in [oracle/jass](../oracle/jass/), and the C++ setups in
[Cases.cpp](../tools/wc3test/Cases.cpp), [wc3states](../tools/wc3states/main.cpp) and
[compare_states.py](../tools/compare_states.py).

**What exists.** 24 manually authored WC3 maps: Phase 0's MOV-0002, 15 Phase 1 maps
and 8 MOV-0012 maps. The 23 maps after Phase 0 use the shared oracle-v1 library.
These must be told apart:

| Kind | Members | Counted as |
|---|---|---|
| Experiment IDs (questions) | MOV-0001–MOV-0010, MOV-0012, JASS-0001 | 12 |
| Map revisions of one question | MOV-0002 → MOV-0002-r2; MOV-0012-a → MOV-0012-a-r2 | not new questions |
| Sampling variants | JASS-0001 p001/p010/p020/p025/p050: MOV-0002's `u0` alone, sampled at five periods | one setup |
| Distinct unit/order setups | MOV-0001–0010 (10); JASS-0001 (1); MOV-0012 b–g and a-r2 (7; a = p001) | 18 |
| Model diagnostics | footman-v1–v4, v2 before-due-update | execution choices, not scenarios |

**Repetition actually found.** Every one of the 23 oracle-v1 cases is the same
five steps, written out by hand each time:

| Step | WC3 case files | C++ copies |
|---|---|---|
| Create `hfoo` for Player(0) at (x, y, facing) | 24 `CreateUnit` calls in 23 files, plus acquisition range 0 | `Cases.cpp` facing/second-unit branches; `wc3states` arguments; `compare_states.SCENARIOS` |
| Setters | `SetUnitMoveSpeed` (MOV-0004, -0005); `SetUnitX/Y` (MOV-0012 a-r2, b, c) | `case_number == 4 / 5` branches |
| Watch, then run a schedule | `OracleWatchUnit`; `OracleRun(period, callbacks)`: 0.02 × 250 (10), 0.02 × 600, 0.001 × 500/1000 (9), 0.01, 0.025, 0.05 | `case_callbacks()` |
| Orders keyed by callback | 22 `OracleCallback() == 0` moves; 4 `== 50` branches: relative move (2), absolute move, stop | callback-0 and callback-50 branches |
| Observe | SAMPLE x/y/facing/order every callback (all); CLOCKS (5), STATE (8) events | samples always; no C++ event producer |
| Describe | A hand-written `OracleSetup` string restating the setup (23 files) | — |

The canonical contract's own experiment table (`trace_contract.shape`) is also a
copy, but it is intentionally independent of every producer and stays that way.

**Conclusion: extraction is justified now, for the MOV-0001–MOV-0010 scope.**
The pattern create → set → order at a callback → observe is uniform across every
instrumented map. The C++ runner encodes ten setups as `case_number ==` branches
spread over facing, a second unit, speed, the initial target and callback-50
actions. MOV-0012 added two more hand-copied setup tables. Adding the next
experiment means editing those branches and restating the setup in JASS. 18
distinct setups and 24 maps sit at the low end of the plan's "roughly 20–50",
but this repetition is uniform enough to fix a small v1 schema.

It does **not** justify: events and auxiliary clocks, `SetUnitX/Y`, other periods
in the C++ runner, parameter matrices or JASS generation. Their only demonstrated
consumers are the JASS maps and the state probe. They wait for a C++ consumer, or
for Phase 6. No test was created to reach a count.

## Implementation

- **Parsing.** The project is dependency-free C++20 plus the Python standard
  library, and the runner is C++. [Scenario.cpp](../tools/wc3test/Scenario.cpp)
  parses a strict YAML subset directly (about 300 lines including validation), so
  the bytes hashed are the bytes parsed. No normalization step or C++ JSON reader
  is needed. The subset is valid YAML, and Ruby's Psych reads all ten files with the
  same meaning. Parsing fills a plain struct and knows nothing about the World or
  any reference.
- **Execution.** `movement::run(const scenario::Scenario&, …)` in
  [Cases.cpp](../tools/wc3test/Cases.cpp) maps declarations onto the unchanged
  World API: `create_footman`, `set_move_speed`, `issue_point_order`,
  `issue_immediate_order` and `step`. It follows the hard-coded schedule:
  identical sampling, actions after the due step, and footman-v4's library clock.
  Relative targets read `world.unit(id).position()` at execution. The simulation
  has no dependency on serialization, files, references, a renderer or wall-clock time.
- **Control.** The hard-coded `run(int case_number, …)` is unchanged apart from
  carrying unit names, the period and each action's unit into the trace. It
  remained the default `wc3test` behavior and the migration control until it was
  removed after PR #13 (see [Control removed](#control-removed)).
- **CLI.** `wc3test --scenario FILE_OR_DIR` (repeatable) validates every
  description and runner capability, then simulates, and only then creates
  output. Invalid input exits 2 with a line-numbered message and writes nothing.
- **Provenance.** This is additive and outside the observation payload. The run
  identity lists the scenarios (`experiment`, `map_revision`, `path`, `sha256`), and
  each trace's `provenance.scenario` names its own. The
  [trace contract](trace-contract-v1.md) checks both. It also now accepts a run
  case table that is a subset, so one scenario can be validated alone. Retained
  experiments in that table must still have their independent shapes.

## Verification

Local, native ARM Mac (Darwin 27.0.0), AppleClang 21.0.0, Python 3.14.7:

- **CTest 3/3**: `world_invariants`, the new `scenario_v1`, and `footman_v4_wc3`.
  `scenario_v1` checks SHA-256 against standard vectors, and exact decimal-to-float
  conversion against compiler literals, including exact float midpoints (ties to
  even). It covers 44 syntax/validation cases and the equal-time ordering of
  relative moves and stop. It also covers **80 migrated runs**: 10 cases × 4 models
  × both phases, byte-identical to the hard-coded runner in sample CSV, action CSV
  and canonical records.
- **Python 56/56**, including six new [scenario tests](../tools/test_scenarios.py):
  - Hard-coded and scenario payloads are equal for all five CI suites. CSV bytes
    are equal, and the only metadata differences are `identity.build.scenarios`
    and `provenance.scenario`.
  - Provenance equals `hashlib` of the file, and tampered provenance is rejected.
  - A MOV-0006 description with 300 callbacks runs, but the contract rejects its
    trace and the comparator exits 2. A description cannot redefine a retained shape.
  - The migration gate detects a changed relative offset, accepts a comment-only
    edit with a new hash, and catches a file changed after the run.
  - Fifteen invalid inputs fail with exit 2 and **no output directory**, even when a
    valid scenario is in the same run: an unsupported version, field, order or type;
    a missing unit reference; a duplicate name; truncation at a line boundary and
    mid-line; a non-finite or overflowing number; an invalid period; a sub-microsecond
    time; an off-schedule or post-end action; and the runner-capability rejection of
    0.01 s. A duplicate experiment and a missing file also fail.
  - A two-unit scenario with three actions at one time: they run in file order after
    both samples, with contiguous sequence numbers. Each relative target equals the
    float32 sum of the sampled position and the offset, and the 100 speed request
    is observed as 150. With no retained shape, the contract gives it no verdict.
- **CI entry point** `run_ci.py`: Release with `--archive` and Debug both PASS.
  All 45 Phase 1 runs validate, and all 15 fixtures and the index reproduce byte
  for byte. The archival migration still reproduces the 60 Phase 2 CSV hashes and
  30 historical state reports.

| Suite | Hard-coded | From scenarios | Regression gate (both) | Migration |
|---|---|---|---|---|
| footman-v4 (primary) | 10/10 PASS | 10/10 PASS | PASS | EQUIVALENT |
| footman-v3 | 1/10 | 1/10 | PASS | EQUIVALENT |
| footman-v2 | 1/10 | 1/10 | PASS | EQUIVALENT |
| footman-v2 before-due-update | 1/10 | 1/10 | PASS | EQUIVALENT |
| footman-v1 | 1/10 | 1/10 | PASS | EQUIVALENT |

Tolerances are unchanged. Historical models keep their measured failures, and
both kinds of run are graded against the same baselines.

## CI integration

For each of the five suites, `run_ci.py` now also runs the committed scenarios
twice in fresh processes. It requires identical bytes, then grades them with the
unchanged comparator and checks them against the suite's existing regression
baseline. It writes `reports/<suite>/scenario/migration.json`, which passes only
if:

- every observation payload and CSV byte equals the hard-coded control's;
- the only metadata differences are the named scenario keys;
- every recorded scenario hash matches its committed file;
- the comparison reports agree apart from identity and trace hashes.

Primary v4 must be 10/10 both ways. The aggregate job rechecks the downloaded
scenario traces, repeat hashes and migration verdicts for every configuration,
and that the scenario inputs are identical across hosts. Artifact layout and
policy: [Phase 4 CI](phase-4-ci.md#phase-5-scenario-suites).

## Hosted verification

[PR run 36887017447](https://github.com/galitianu/warcraft-re/actions/runs/36887017447)
passes **all five configurations and the aggregate job**. It ran on the clean PR
merge commit `cbf9d0f` of head `ceaf1c7`. Retained evidence:
[pr-verification.json](../results/phase-5/pr-verification.json) and
[summary](../results/phase-5/pr-verification.md). Downloaded artifacts recheck
identically through `summarize_ci.py`.

| Configuration | Compiler | CTest | Python | v4 hard-coded / scenario | Migration (5 suites) |
|---|---|---|---|---|---|
| macOS ARM64 Release (+ archive) | AppleClang 17.0.0 | 3/3 | 56/56 | 10/10 / 10/10 | EQUIVALENT |
| macOS ARM64 Debug | AppleClang 17.0.0 | 3/3 | 56/56 | 10/10 / 10/10 | EQUIVALENT |
| Linux x64 Release | GCC 13.3.0 | 3/3 | 56/56 | 10/10 / 10/10 | EQUIVALENT |
| Linux x64 Debug | Clang 18.1.3 | 3/3 | 56/56 | 10/10 / 10/10 | EQUIVALENT |
| Windows x64 Release | MSVC 19.44.35229.0 | 3/3 | 56/56 | 10/10 / 10/10 | EQUIVALENT |

The scenario inputs are identical on every host. Cross-host payload equality is
unchanged from Phase 4. v3/v4 are identical everywhere, and v1/v2 differ only in
the explained x64-libm MOV-0007 payload, which their reviewed baselines grade.

The [first PR run](../results/phase-5/initial-pr-run.json) failed on Windows only.
One Python test wrote its temporary scenario with the platform newline (CRLF), and
v1 rejects carriage returns by design. Every other Windows stage passed,
including all five migrations. The test was fixed to write LF; the parser was not
relaxed.

PR #13 merged as `b40fe1b`.
[Main-push run 36982554457](https://github.com/galitianu/warcraft-re/actions/runs/36982554457)
passes all five configurations and the aggregate job on that clean merge commit
([evidence](../results/phase-5/main-verification.md)). Its numbers match the PR run:
CTest 3/3, Python 56/56, v4 10/10 both hard-coded and from scenarios, and every
migration EQUIVALENT. The downloaded artifacts recheck identically.

## Scope and what remains unobserved

- Supported: one or more Footmen at a declared position and facing; requested
  move speeds; absolute and relative move, and stop, at callback times; 0.02 s
  sampling of x/y/facing/order. That covers MOV-0001–MOV-0010.
- Retail verdicts exist only where an independent fixture exists, which here means
  MOV-0001–MOV-0010. A new scenario runs and yields a valid C++ trace shape, but
  it has **no retail compatibility verdict** until it is captured under its own
  experiment ID.
- Not migrated: JASS-0001 timing variants and MOV-0012. Their C++ counterpart is
  the separate state probe, and their CLOCKS/STATE events have no C++ producer,
  so they remain **UNOBSERVED** in canonical comparison.
- Unresolved: sampler/update ordering, the retail simulation quantum, WC3's
  clamping at map bounds, seed effects and retail RNG.

## Control removed

After the main-push run above, the hard-coded `run(int case_number, …)` table,
`case_name`/`case_units`/`case_identity` and the per-suite migration gate were
deleted. `wc3test` now requires `--scenario` and exits 2 without it; every CI
suite, `run_phase2.py`, `run_phase3.py`, `run_footman_v3.py` and
`run_footman_v4.py` pass `--scenario scenarios`. `world_tests` loads its cases
from the same files. CI instead requires each suite's identity to list the ten
committed scenarios with the checkout's hashes, and the aggregate fails if
configurations ran different scenario bytes.

Before deletion, the scenario-only runner was compared locally with the
pre-removal binary: identical observation payloads and CSV bytes for v1–v4 in
both phases (0 differences). After it: CTest 3/3, Python 56/56, local ARM
Release (with archive) and Debug `run_ci.py` PASS, and `run_phase2.py` and
`run_footman_v3.py` reproduce their retained results. No captures, fixtures,
baselines or tolerances changed.

## Reproduction

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build
ctest --test-dir build --output-on-failure
WC3TEST_RUNNER=$PWD/build/wc3test python3 -m unittest discover -s tools -p 'test_*.py' -v
build/wc3test --model v4 --scenario scenarios --out build/scenario-v4
python3 tools/compare_traces.py --actual build/scenario-v4
python3 tools/run_ci.py --build build-ci --compiler /usr/bin/clang++ --config Release \
  --expect-arch arm64 --archive
```

## Next action

Phase 5's extraction is in place. Proceed with the existing research task: design
the sampler/update-order capture
([v4 limitation](footman-v4-results.md#sampling-order)) under a new permanent
experiment ID, described as a scenario where v1 suffices. Its event observations
justify the next schema field only when a C++ consumer needs them. Phase 6's JASS
generator takes these same scenarios as its input.

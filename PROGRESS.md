# Progress

As of 8 October 2026.

**Next roadmap:** [playable Human skirmish](docs/next-roadmap.md), with measured
mechanics and an interactive raylib client advancing together. The delivered
bootstrap is retained below; PR #28 was merged on 6 October and issue #27 is closed.
The [continuous-development controller](docs/continuous-development.md) adds
project-scoped 80% reported-usage admission/stops, alternating eligible providers,
automatic quota resumption, issue dispatch, independent review and CI-bound
integration. The user selected **Claude Code/Codex**, total reported account usage,
and automatic merges after independent review and passing CI. No shared BB
pool/concurrency/provider setting is changed. The cutoff has documented
reporting/in-flight limits. Live enabled state and worker receipts are maintained
in the controller's BB thread storage, outside git.
Both schedules were installed **paused**; their stored launchers completed manual
disabled-policy checks with exit 0 and no model work. Fifty controller/install
negative-control tests pass; the full Python suite passes 140/140. Native ARM64
Release archival compatibility CI passes (CTest 3/3, protected movement/collision
and existing P1 gates). [Bootstrap verification](results/continuous-bootstrap/README.md)
records scope and the zero-request live BB CLI smoke check. No new WC3 captures
or playable-client behavior is claimed by these infrastructure checks.

**Interactive client (milestone 1, first increment, [issue #31](https://github.com/galitianu/warcraft-re/issues/31)):**
an optional raylib executable (`-DWC3_CLIENT=ON`, macOS ARM64) controls three footman-v4 Footmen on
flat placeholder ground: camera pan/zoom, single-unit picking with a selection ring, right-click move
and `S` stop. Input becomes `Session` commands (time, sequence, unit, order, target) applied only
between 5 ms frames. Live play and headless replay share that path; wall time only paces frames.
Two retained smoke recordings replay **identically** under 30 Hz, 60 Hz and irregular render
schedules, headlessly, and against the live client's own checkpoints. The screenshots show move,
a part-way stop and an equal-time move+stop. They were driven by scripted Cocoa events, not physical
input ([evidence](results/client-v1/README.md), [design](docs/client-v1.md)). Default build/CI need
no raylib. Native ARM64 Release `run_ci.py --archive` passes with all movement, 32 collision and
gated P1 checks unchanged. A CI revision fixes platform-dependent RNG snapshot text:
original live hashes are retained and verified before deriving portable v2 checkpoints
([migration evidence](results/client-v1/README.md#portable-snapshot-revision)). Native checks pass;
new-head hosted Linux/Windows checks remain with the controller. Placeholder geometry
claims no visual fidelity.

**Route display (milestone 1, [issue #34](https://github.com/galitianu/warcraft-re/issues/34), P3):** the
selected Footman shows footman-v4's current computed route (cyan polyline from the unit through the remaining
waypoints) instead of a straight destination line; a partial route stops where the plan ends; an unapplied or
unplanned move shows `pending` with no path; stop, arrival, redirect and deselection replace or clear it. The view
copies `Unit::route()`/cursor/partial flag through a const boundary and never plans or mutates; the route algorithm
and command semantics are unchanged. Retained scripted run 0001 (macOS ARM64) shows an unobstructed move, a detour
south of idle Footman 1, a redirect and a part-way stop; `wc3replay` matches headless under 30 Hz/60 Hz/irregular,
6 live checkpoints and all 7 displayed routes exactly ([evidence](results/client-route/README.md),
[design](docs/client-route.md)). Limits: scripted Cocoa input, no partial route shown live (headless tests cover
it), no replan fell inside a screenshot although the model can replan mid-route. Native ARM64 Release
`run_ci.py --archive` passes with all protected gates unchanged. Milestone 1 is not complete: next are the roadmap's
remaining client increments (pause, diagnostic overlay; multiple selection is recorded below).

**Multiple selection (milestone 1, [issue #36](https://github.com/galitianu/warcraft-re/issues/36), P3):**
box selection, shift-click toggle and shift-box add use a sorted presentation-only selection in `wc3view`.
Group move/stop submits existing per-unit commands in ascending index at equal simulation time.
All selected Footmen show rings, destinations and individual orders; the lowest index shows its route.
SEL-0001's scripted macOS ARM64 run shows three-unit selection/move, shift removal and a two-unit
part-way stop; four live checkpoints and five displayed routes match headless and 30 Hz/60 Hz/irregular
replays exactly ([evidence](results/client-selection/README.md), [rules](docs/client-selection.md)).
Native client CTest passes 8/8; native ARM64 Release archival CI passes with protected references/tolerances unchanged.
Every unit receives the same target: WC3 assignment/formations remain unmeasured, a likely **P3** difference,
and three-unit interactions are model behavior (issue #32). Placeholder geometry claims no visual fidelity.
Milestone 1 remains open; next client action is a bounded pause/diagnostic-overlay increment.

**Latest measured gameplay:** Phase 8, first P3 behavior: unit–unit collision ([issue #24](https://github.com/galitianu/warcraft-re/issues/24),
[issue #27](https://github.com/galitianu/warcraft-re/issues/27)). footman-v4 now follows WC3's own pathing
mechanism, read from the retail executable ([model](docs/footman-v4-model.md#unit-pathing)): grid footprints, a
one-cell probe, waits decided by squared speed, and the retail A*. It reproduces **all 26** two-Footman captures
(MOV-0018 to MOV-0021) exactly. Those captures guided the analysis, so [MOV-0022](docs/mov-0022.md) pre-registered
six new layouts: unequal speeds, reversed issue order, a slow crossing unit, a diagonal past an idle unit and an
overtake. All six captures match the predicted traces exactly. No P3, P2 or P1 difference remains in the 32
two-Footman captures; issue #27's acceptance is met.

**Phase 7:** capture capability implemented for four reviewed v1 scenarios.
One command completes generation, verified World Editor packaging, three fresh WC3
runs, lossless candidate normalization and same-scenario C++ comparison, with zero
intervention. Four new revisions / twelve runs reproduce the hand-authored controls
exactly ([evidence](results/phase-7/summary.json), [procedure](docs/phase-7-capture.md)).
[PR #25](https://github.com/galitianu/warcraft-re/pull/25) merged as `c929bd6`. Native archival
CI and all five hosted PR/main configurations pass; downloaded evidence regrades
([main-push delivery](results/phase-7/main-verification/summary.md)). Phase 7 is complete
within its four-scenario scope.

MOV-0015 ([issue #22](https://github.com/galitianu/warcraft-re/issues/22), merged and verified on main)
tested the 1 ms lag rule (T7) and a 30 ms update-event facing clock (FU). Both held in three of four new maps. The
fourth map's sampler started one ulp later than modelled. That rounding was fitted after capture, so no rule is
adopted. These sampling-order differences are **P1, invisible in play** (see AGENTS.md); they stay documented and
gated, and further work on them is deferred.
**Retail observations:** Phase 0's 20 MOV-0002 captures, plus 15 Phase 1 maps and
8 MOV-0012 maps × 3 fresh-process captures, plus fifteen generated revisions × 3,
all payload-identical within each map, plus four Phase 7 revisions × 3 and a separate
three-run manual baseline. Generated observations reproduce their
hand-authored controls exactly.
**C++ compatibility:** footman-v4 passes MOV-0001–MOV-0010 under the fixed tolerances.
Every sample and clock prints the same R2SW_6 text as WC3. It also reproduces every
recorded state of the 1–50 ms JASS-0001/MOV-0012 captures. A few callbacks read a
neighbouring frame for reasons not yet explained (P1: under half a microsecond of
callback timing, at most one frame's 1.35 units or a fraction of a degree). Every MOV-0013/0014 clock reading
matches WC3. Their frame exceptions, and MOV-0015's frame, facing and start
differences, fail canonically in nine of eleven maps (reviewed, gated as observed). footman-v1/v2/v3 keep their documented failures.
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

**Issue #6 movement follow-up** ([issue #6](https://github.com/galitianu/warcraft-re/issues/6)):
[footman-v3](docs/footman-v3-model.md) adds a hidden movement heading (0.6 rad turns,
pre-turn 60° gate), 30 ms logical updates from 10 ms, six 5 ms exposures per batch,
reported facing that accelerates/caps/brakes as `err·(err/0.2 rad)^¼`, and
round-toward-zero float32 coordinates offset from the map corner.
[Results](docs/footman-v3-results.md), [reports](results/footman-v3/).
The rounding rule is inferred from the retained grid (no odd 1/4096 multiple at ≥ 0)
and from 180/45 reading 179.999985/44.999996.

Clean build of `781c7a2`: CTest 1/1, Python 37/37, v1/v2 evidence unchanged and v3
repeatable. Still 1/10 PASS. All 12 movement onsets, 9 idle transitions and order samples now
match. MOV-0004/0010 X pass entirely; MOV-0002 X first fails at callback 88
instead of 4; MOV-0009 turns as WC3 for 24 callbacks. MOV-0002 still fails Y/facing
at callback 1, because east/west heading noise is unmodelled. Arithmetic ties that noise
to `acos` near 0°/180° and X's position on a 1/64 grid, but cannot determine it;
no fitted rule was added. Proposed **MOV-0012**: 1 ms east travel from x=1/512 and
3/512, from (0,256), and at 30°.

**MOV-0012 and footman-v4** (branch `mov-0012`): [MOV-0012](docs/mov-0012.md) captured
eight 1 ms variants (off-grid starts, shifted target, Y=256, 30°, west, short
arrival). It shows that the east/west heading noise is deterministic float32
arithmetic, and that 30° travel is quiet. The game's square root is biased high, so
`acos` of a near-1 cosine lands 0.3–0.4° off axis.
[footman-v4](docs/footman-v4-model.md) runs v3's cadence in a C++ reimplementation of
the retail soft-float. Its lookup tables are generated from formulas, with no game data.
It adds three rules from the retail update order: the heading is re-derived from the
velocity, orders store the moving direction, and the movement clock starts at 0.5 s.
[Results](docs/footman-v4-results.md), [reports](results/footman-v4/).

Clean build of `6247107`: CTest 2/2 (including the `footman_v4_wc3` gate), Python 40/40,
v1/v2/v3 evidence unchanged, Release/Debug bytes identical. **10/10 PASS**, and
3,111 sample rows and 2,860 clocks are text-identical. 26,581 state-capture readings: all
clocks/timers identical; X/Y differ at five early callbacks in each 1 ms run, and facing at
25 update-frame callbacks of p010/p025. That sampling order is unexplained and listed explicitly.

**Phase 4 CI** ([issue #8](https://github.com/galitianu/warcraft-re/issues/8),
[PR #11](https://github.com/galitianu/warcraft-re/pull/11)):
[entry point, policy and reproduction](docs/phase-4-ci.md),
[PR verification](https://github.com/galitianu/warcraft-re/actions/runs/36860946737),
[main-push verification](https://github.com/galitianu/warcraft-re/actions/runs/36861964114),
[retained main evidence](results/phase-4/main-verification.json).
PR #11 merged as `bdaa9ac`; the real push workflow passes all five configurations
and the aggregate job. Downloaded artifact hashes and all 25 comparisons/regression
assessments reproduce locally, with clean build identities bound to the merge commit.
All five configurations pass: ARM macOS AppleClang Release/Debug, Linux x64 GCC
Release/Clang Debug, Windows x64 MSVC Release. Each passes CTest 2/2, Python 50/50,
45 raw runs, 15 exact fixtures, full comparisons and two separate process runs per
model/phase. v4 is required at 10/10; historical suites remain 1/10 with no protected
regression. Native ARM Release also reproduces archival migration evidence.
Negative controls catch passing/failing-property regressions, action/structure
changes, invalid/incomplete input, runner failures and timeouts, and accept improvements.

v3/v4 observation payloads match across measured configurations. Historical v1/v2
MOV-0007 facing differs by one float libm boundary on x64; the runtime probe,
initial failed assessments, complete reviewed x64 baselines and Windows equality
are retained in [Phase 4 evidence](results/phase-4/). References/tolerances are
unchanged; canonical JASS/CLOCKS properties remain UNOBSERVED. Issue #6's movement
result is promoted to the primary required pass, while that GitHub issue remains
open. No release tag or fresh retail capture is included.

**Phase 5 scenarios** ([issue #12](https://github.com/galitianu/warcraft-re/issues/12),
[PR #13](https://github.com/galitianu/warcraft-re/pull/13)):
[readiness audit, verification and scope](docs/phase-5-scenarios.md),
[scenario v1 contract](docs/scenario-v1.md), [scenarios](scenarios/).
The audit found 24 maps, 12 experiment IDs and 18 distinct setups, all
following one pattern (create → set → order at a callback → observe). The setups
are copied by hand across JASS, `Cases.cpp`, `wc3states` and `compare_states`.
That justifies extraction for the MOV-0001–0010 scope only.
`wc3test --scenario` parses a strict, dependency-free YAML subset in C++. It
validates everything before writing anything, maps the declarations onto the
unchanged World API, and records each scenario's SHA-256 as provenance outside
the observation payload. The hard-coded cases were the migration control.

All ten scenarios reproduce the hard-coded payloads and CSV bytes for every
model and phase: 80 runs in CTest, and five suites in CI. v4 is 10/10 PASS from
scenarios; historical suites are 1/10 with no protected regression. Local ARM
Release (with archive) and Debug CI pass, with CTest 3/3 and Python 56/56.
Invalid input exits 2 with no output. A description cannot redefine a retained
trace shape; scenarios without a fixture get no retail verdict. JASS-0001/MOV-0012
events, other periods and `SetUnitX/Y` stay out of v1. No captures, fixtures or
tolerances changed. [PR run 36887017447](https://github.com/galitianu/warcraft-re/actions/runs/36887017447)
passes all five configurations and the aggregate job, with every migration
EQUIVALENT ([evidence](results/phase-5/pr-verification.md)). The first PR run's
Windows-only test newline failure is retained. PR #13 merged as `b40fe1b`; its
[main-push run 36982554457](https://github.com/galitianu/warcraft-re/actions/runs/36982554457)
passes the same gates ([evidence](results/phase-5/main-verification.md)).
With equivalence shown on both triggers, the hard-coded control was then removed:
`wc3test` requires `--scenario`, and every CI suite runs the committed scenarios
([control removed](docs/phase-5-scenarios.md#control-removed)).

## Phase 6 scenario loop

[Issue #14](https://github.com/galitianu/warcraft-re/issues/14),
[PR #16](https://github.com/galitianu/warcraft-re/pull/16):
[route, supported input and reproduction](docs/phase-6-generation.md).
`oracle_codegen` shares the strict v1 parser with wc3test, preserves real tokens,
and binds generated JASS to the original scenario SHA-256. Ten
[goldens](oracle/generated/v1/) pass [pjass](results/phase-6/pjass.json) and the
[independent ordered-call audit](results/phase-6/generator-audit.json).
The World Editor packaging route and oracle-v1 remain unchanged.

The restored selected Windows 11 ARM64 VM's
[installation verification](oracle/environment/phase-6-verification.json) confirms
WC3 1.29.2.9231 x86 and all seven reference-file hashes. MOV-0002-g1, MOV-0004-g1,
MOV-0006-g1 and MOV-0010-g1 are new verified editor-saved maps. Each has three
fresh-process WC3 runs, byte-identical within its revision. Their ordered WATCH,
RUN, TICK, SAMPLE, ACTION and EVENT observations equal the independent controls
exactly; map labels, SETUP and preload/footer metadata are reported separately.
Four new [canonical fixtures](oracle/canonical-generated/wc3-1.29.2-9231-x86/)
and the same unchanged scenarios pass C++ comparisons under the original contract
and tolerances: [full evidence](results/phase-6/generated-loop.json),
[summary](results/phase-6/generated-loop.md). The v0.1 infrastructure comparison
capability is demonstrated; no release tag is created.

Native ARM64 AppleClang Release CI with `--archive`: CTest 3/3, Python 66/66,
4/4 generated comparisons and all historical compatibility/regression gates PASS.
footman-v4 remains 10/10; all [50 before/after payload hashes](results/phase-6/runner-before-after.json)
match. The original 45 Phase 1 runs, 15 fixtures, scenarios, model behavior,
baselines and tolerances remain unchanged. CI retains/regrades downloaded generated
fixtures and C++ traces alongside byte-identical golden JASS and scenario inputs.
Phase 5's scenario-only main-push evidence was
[downloaded and rechecked](results/phase-5/control-removed-main-verification/summary.md).
The real-capture [PR workflow 37005207059](https://github.com/galitianu/warcraft-re/actions/runs/37005207059)
at `37cb228` passes all five configurations and the aggregate job; each passes
CTest 3/3, Python 65/65, generated loop 4/4 and v4 10/10. Downloaded artifacts
[regrade independently](results/phase-6/capture-pr-verification/summary.md),
matching the hosted aggregate report exactly. Generated JASS and scenario inputs
are identical across configurations; historical baselines pass.

PR review follow-up makes generated capture comparison unconditional: missing
manifests/fixtures and disabled/missing downloaded gate reports fail. The
real-capture integrity test no longer skips; historical CI artifacts require an
explicit legacy recheck option. No retail evidence or numeric comparison changes.
Fix `36ad6f0`: native Release with `--archive` and
[PR workflow 37008399150](https://github.com/galitianu/warcraft-re/actions/runs/37008399150)
PASS; all five configurations pass CTest 3/3, Python 66/66, generated loop 4/4
and v4 10/10. Downloaded artifacts [regrade locally](results/phase-6/review-pr-verification/summary.md)
and match the hosted aggregate exactly; every configuration declares the
generated capture gate mandatory. Historical Phase 5 main artifacts also recheck
PASS using the explicit legacy option.

PR #16 merged as `4af616e`. Its real
[main-push workflow 37009239543](https://github.com/galitianu/warcraft-re/actions/runs/37009239543)
passes all five configurations and the aggregate job. The downloaded artifacts
[regrade independently](results/phase-6/main-verification/summary.md) and match
the hosted aggregate exactly, bound to the merge commit and push trigger. Each
configuration passes CTest 3/3, Python 66/66, generated loop 4/4 and v4 10/10;
generation/scenario inputs are identical and historical baselines pass.
All Phase 6 delivery gates are met, with the sampler experiment explicitly split
into #17 as permitted by #14. No release tag is created.

## MOV-0013 sampler start phase

[Issue #17](https://github.com/galitianu/warcraft-re/issues/17):
[question, pre-registered predictions and results](docs/mov-0013.md),
[scenario v2](docs/scenario-v2.md). The predictions were committed (`9fcfe63`) before
capture. Scenario v2 adds only `observe.start` and `observe.state_clock`; every v1
file keeps its meaning. `oracle_codegen` v2 generated four cases without C++ v2 output
(pjass PASS). On the [verified](oracle/environment/mov-0013-verification.json) selected
ARM64 VM, four check_map-verified maps each gave three payload-identical fresh-process
runs ([captures](oracle/captures/wc3-1.29.2-9231-x86/)). The first b/c outputs were
rejected by the parser and are retained.

MOV-0013-a reproduces MOV-0012-a exactly. Exceptions read frame H0 + 1 at a 15–35,
c 25–35, b none and d none. Only H1, tied to the sampler's own callbacks, fits all
four; the order-, grid- and absolute-time hypotheses are refuted. The update grid
stays global. The delayed starts also show a new finding: TICK sits one ulp below the
pre-registered library clock at 875 (b) and 624 (c) callbacks. Post-hoc candidates
for both are recorded, not implemented.

`wc3test` runs v2 under footman-v4 with rule H0. All 50 MOV-0001–0010 model/phase
[payloads are unchanged](results/mov-0013/runner-before-after.json), and v1
scenarios rewritten as v2 give identical v4 observations. Under unchanged tolerances
d passes; a and c fail on x/y and b and c on t. [run_mov0013.py](tools/run_mov0013.py)
requires exactly those differences ([report](results/mov-0013/mov-0013.md)). It is a
required CI gate, and the downloaded artifacts are regraded. Native ARM64
AppleClang Release CI with `--archive` passes: CTest 3/3, Python 69/69, generated
loop 4/4, MOV-0013 gate, v4 10/10 and historical baselines. The JASS-0001/MOV-0012
state gate is unchanged; its hand-written-map descriptions were not migrated
([why](docs/mov-0013.md#results)).
[PR #19](https://github.com/galitianu/warcraft-re/pull/19)'s
[workflow 37015023406](https://github.com/galitianu/warcraft-re/actions/runs/37015023406)
passes all five configurations and the aggregate job, on clean builds of merge ref `34a58e1`.
Each configuration passes CTest 3/3, Python 69/69, generated loop 4/4, the MOV-0013 gate
and v4 10/10. The downloaded artifacts [regrade locally](results/mov-0013/pr-verification/summary.md)
to a report identical to the hosted one. MOV-0013's C++ payloads and the generated JASS
are identical across configurations. PR #19 merged as `f07405e`. Its
[main-push workflow 37017767562](https://github.com/galitianu/warcraft-re/actions/runs/37017767562)
passes the same gates on all five configurations, with clean builds of the merge commit.
The downloaded artifacts [regrade](results/mov-0013/main-verification/summary.md) to a
report identical to the hosted one, and the MOV-0013 payloads equal the PR run's.

## MOV-0014 lag or index, and the timer start

[Issue #20](https://github.com/galitianu/warcraft-re/issues/20):
[pre-registered predictions, decision rules and results](docs/mov-0014.md). The
predictions and rules were committed and pushed (`c4c47a0`) before any map existed:

- three v2 starts (0.3, 0.72, 0.9 s);
- frame rules H1, Lu and Ls;
- clock readings M0, M1, Q16, Q17, Q18 and Qrel;
- [predictions.json](results/mov-0014/predictions.json), regenerated byte for byte by a test.

The installation was [verified](oracle/environment/mov-0014-verification.json), and
three check_map-verified maps gave three payload-identical fresh-process runs each.
[grading.json](results/mov-0014/grading.json) gives the results:

- **Clock.** Only Q17 (timer start rounded down to 2⁻¹⁷ s) predicts all 3,003 TICKs;
  it also matches every earlier retained TICK. As pre-registered, the v2 runner adopts
  it in exact integer arithmetic. All 50 v1-suite payloads are unchanged. MOV-0013-b/c
  change only their reported times and now match WC3; MOV-0013-b passes
  ([before/after](results/mov-0014/runner-before-after.json)).
- **Frames.** The next frame's X/Y is read at a 30–60, b 15 and c 15. H1, Lu and Ls
  are refuted; Ls failed only by its lower bound. A post-hoc candidate (lag before the
  frame under 8 × 2⁻²⁴ s, with pre-update facing at update frames) is recorded but not
  implemented.

The gates now cover both experiments. In MOV-0014, a, b and c fail only on x/y, at
the reviewed callbacks ([report](results/mov-0014/mov-0014.md)). Native ARM64
AppleClang Release CI with `--archive` passes: CTest 3/3, Python 70/70, generated
loop 4/4, MOV-0013 and MOV-0014 gates, v4 10/10 and historical baselines.
[PR #21](https://github.com/galitianu/warcraft-re/pull/21)'s
[workflow 37022849703](https://github.com/galitianu/warcraft-re/actions/runs/37022849703)
passes all five configurations and the aggregate job, on clean builds of merge ref `b4d1969`.
Each passes CTest 3/3, Python 70/70, generated loop 4/4, both experiment gates and v4 10/10.
The downloaded artifacts [regrade locally](results/mov-0014/pr-verification/summary.md)
to a report identical to the hosted one.
PR #21 merged as `43c10b1`. Its
[main-push workflow 37023859883](https://github.com/galitianu/warcraft-re/actions/runs/37023859883)
passes the same gates on all five configurations, with clean builds of the merge commit.
The downloaded artifacts [regrade](results/mov-0014/main-verification/summary.md) to a
report identical to the hosted one, and the experiment payloads equal the PR run's.

## MOV-0015 early-frame threshold and facing clock

[Issue #22](https://github.com/galitianu/warcraft-re/issues/22):
[pre-registered predictions, decision rules and results](docs/mov-0015.md). The
predictions and rules were committed and pushed (`f917687`) before any map existed:

- four v2 starts (0.12, 0.45, 0.999054, 0.997001 s);
- frame rules H0, T7 (lag < 8 × 2⁻²⁴ s) and Tsub (a float32 offset);
- facing rules FH (frame clock) and FU (30 ms update event);
- [predictions.json](results/mov-0015/predictions.json), regenerated byte for byte by a test.

The installation was [verified](oracle/environment/mov-0015-verification.json), and
four check_map-verified maps gave three payload-identical fresh-process runs each.
[grading.json](results/mov-0015/grading.json) gives the results:

- **Pre-registered.** No rule survives all four maps. T7 predicted b, c and d exactly,
  and FU predicted c's five facings past 2 s that FH missed. Tsub is refuted. In a,
  callback 45 also read ahead and callback 10's facing matched neither rule. Map a's
  10 s clock and one TICK read 1 ulp late.
- **Post hoc** ([posthoc.json](results/mov-0015/posthoc.json)): every clock of map a
  fits a sampler start one ulp later, `round-to-nearest(0.5 + float32(start))`, and
  that rule gives the runner's start in every other map. From it, T7 and FU reproduce
  every X/Y and facing of all eleven MOV-0013–0015 maps (11,011 callbacks).
- **C++** is unchanged (H0, FH, truncated start). The MOV-0015 gate requires exactly
  the observed differences ([report](results/mov-0015/mov-0015.md)). The trace
  contract now checks a v2 callback's frame exactly against the float32 clocks. Its
  old microsecond window rejected correct traces past 2 s.

Native ARM64 AppleClang Release CI with `--archive` passes: CTest 3/3, Python 70/70,
generated loop 4/4, the MOV-0013, MOV-0014 and MOV-0015 gates, v4 10/10 and historical
baselines.
[PR #23](https://github.com/galitianu/warcraft-re/pull/23)'s
[workflow 37040588867](https://github.com/galitianu/warcraft-re/actions/runs/37040588867)
passes all five configurations and the aggregate job, on clean builds of merge ref `7c55290`.
Each passes CTest 3/3, Python 70/70, generated loop 4/4, all three experiment gates and
v4 10/10. The downloaded artifacts [regrade locally](results/mov-0015/pr-verification/summary.md)
to a report identical to the hosted one.
PR #23 merged as `53806f3`. Its
[main-push workflow 37041477211](https://github.com/galitianu/warcraft-re/actions/runs/37041477211)
passes the same gates on all five configurations, with clean builds of the merge commit.
The downloaded artifacts [regrade](results/mov-0015/main-verification/summary.md) to a
report identical to the hosted one, and the MOV-0015 C++ trace records equal the PR run's.

**Phase 7** ([issue #18](https://github.com/galitianu/warcraft-re/issues/18)):
[capture_oracle.py](tools/capture_oracle.py) supports exact reviewed MOV-0002/0004/0006/0010
v1 bytes and new packaging revisions. It verifies UTM/rdpipe machine and ARM64 guest,
all seven installation hashes, game/editor versions and x86 PE identities; owns and
renews the desktop lease; validates the saved map and raw transfers; retains failed
stages and stops only its owned processes. Output is a candidate bundle; promotion is
an explicit action. No resume combines changed/stale inputs.

[Four new bundles](results/phase-7/summary.json) retain twelve fresh-process runs,
three identical payloads per map, exact ordered equality with independent controls,
and unchanged-contract C++ PASS. Ordinary integrity tests regrade them offline.
The manual baseline needed eight terminal submissions (one path recovery), seven
additional interventions and 290.56 s. MOV-0002's unattended command needed zero
additional interventions and 151.54 s; the four commands took 143.97–165.73 s. This
includes operator coordination latency, not a controlled VM speed benchmark.
[Real failures](results/phase-7/failures.json) cover wrong/unavailable machine identity,
lease contention and a 0.1 s game-output timeout; all stopped without a result or
canonical promotion. Local tests cover further orchestration/integrity failures.
Stopped-guest startup is tested locally; the working/shared VM was never reset.
Native ARM64 Release archival CI passes ([result](results/phase-7/native-verification/result.json)):
CTest 3/3, Python 83/83, v4 10/10, all five historical regression assessments, 45 Phase 1
runs / 15 unchanged fixtures, the Phase 2 archive, generation/scenario identity and
existing P1 experiment gates. Configure records clean commit `cac0a15`.
[PR workflow 37047975137](https://github.com/galitianu/warcraft-re/actions/runs/37047975137)
passes all five configurations and the aggregate job. [Downloaded evidence](results/phase-7/pr-verification/summary.md)
regrades exactly as the hosted aggregate; all twenty new-candidate comparisons against
the five downloaded v4 suites pass. The initial Linux Clang renewal-test failure
([record](results/phase-7/initial-pr-failure/explanation.md)) is retained; its host-uptime
assumption was corrected without changing production behavior or captures.
Review follow-up: editor authoring now receives the pinned library used by syntax
and saved-map checks. A regression test verifies that an unrelated working directory
and a different local library cannot change the pasted source.
[Final PR workflow 37062537594](https://github.com/galitianu/warcraft-re/actions/runs/37062537594)
passes all five configurations and the aggregate after the fix (`b788160`);
[downloaded artifacts](results/phase-7/review-fix-pr-verification/summary.md) reproduce
the hosted assessment and all twenty new-candidate comparisons. PR #25 merged as
`c929bd6`; its real [main-push workflow 37063014720](https://github.com/galitianu/warcraft-re/actions/runs/37063014720)
passes the same gates. [Retained/regraded evidence](results/phase-7/main-verification/summary.md)
matches the hosted aggregate exactly; all twenty candidate comparisons pass.
Per configuration, CTest 3/3, Python 84/84 and footman-v4 10/10 pass; historical
baselines, original 45 Phase 1 runs / 15 fixtures, Phase 2 archive and generation/
scenario identity gates remain unchanged. Other machines/seeds and retail RNG are unknown.

## MOV-0018 two colliding Footmen

[Issue #24](https://github.com/galitianu/warcraft-re/issues/24), **P3**:
[design, observations, model and results](docs/mov-0018.md). The four v1 variants
were committed before capture (`b667345`): an idle blocker on the path (a), head-on (b),
crossing (c) and an idle blocker 24 units off the path (d). Each was
captured unattended with the Phase 7 command, giving three payload-identical fresh-process runs
on the [verified installation](oracle/environment/).

- **Before** ([comparison](results/mov-0018/before/comparison.json)): all four fail at P3.
  footman-v4 walked through the other unit. WC3 detours 45.8 units south around an idle
  Footman, stops both head-on units and then steps them aside, and makes the crossing unit wait 0.44 s.
- **WC3's behavior.** Routes are 8-connected paths over 32-unit cells, and another
  unit blocks the 3×3 cells around it, so a and d are bit-identical. Units wait
  for a moving unit on the path just ahead. The stop radius is in [14.607, 15.90), not 16.
- **Model:** unit pathing in footman-v4 (grid A*, string pulling, partial routes,
  waits, stop radius 15.5). Every constant is fitted, with its interval in the document.
- **After** ([gate report](results/mov-0018/after/mov0018.md)): a and d PASS bit-identically.
  b and c have the same sides, waits, arrival callbacks (±0) and final positions (≤0.004). Their
  remaining differences are P1: b x/y ≤0.031 units and facing ≤1.81° while u1 waits;
  c facing ≤0.118°. MOV-0001–0010 still pass 10/10 with identical exact text.
- **Gate:** [run_mov0018.py](tools/run_mov0018.py) in CI requires P3 acceptance and exactly
  the reviewed P1 differences. summarize_ci regrades downloaded traces.

Local native ARM64 AppleClang Release CI with `--archive` passes: CTest 3/3, Python 85/85,
generated loop, the MOV-0013/0014/0015/0018 gates, v4 10/10 and the historical baselines. Its MOV-0018
report is byte-identical to the retained one.
[PR #26](https://github.com/galitianu/warcraft-re/pull/26)'s
[workflow 37109955805](https://github.com/galitianu/warcraft-re/actions/runs/37109955805) passes all five
configurations and the aggregate job (head `17950b2`). The downloaded artifacts
[regrade](results/mov-0018/pr-verification/summary.md) to a scope report identical to the hosted one,
and MOV-0018 regrades as PASS in all five configurations.
PR #26 merged as `89042fc`. Its
[main-push workflow 37141634392](https://github.com/galitianu/warcraft-re/actions/runs/37141634392) passes all five
configurations and the aggregate. The downloaded artifacts [regrade](results/mov-0018/main-verification/summary.md)
to a report identical to the hosted one, and every MOV-0018 C++ trace record equals the PR run's.

## MOV-0019 and MOV-0020 who gives way

[Issue #27](https://github.com/galitianu/warcraft-re/issues/27), **P3**. Both designs and
predictions were committed before capture (`d6da91c`, `bff0067`). Ten MOV-0019 and six MOV-0020
maps were each captured in three payload-identical fresh WC3 runs.

- **MOV-0019** ([results](docs/mov-0019.md#results)) confirms the 3×3 footprint and the
  tie order, and **refutes** the wait corridor: in i and j the wrong unit waits (P3).
  Post hoc, partial routes now go to the free node nearest the target, and an idle
  unit covering the target is ignored.
- **MOV-0020** ([results](docs/mov-0020.md#results)) swaps the units' roles. Only
  **role** survives: the eastward unit waits in all six variants, whatever its
  index or order of issue. The partial-route rule passes its pre-registered test (1e-6).
- **Model (post hoc):** a unit blocked by a moving unit on its left that does not see
  it holds one update, routes around it, and that unit holds 20 updates
  ([rule](docs/mov-0020.md#post-hoc-refit-giving-way)).
- **Status** over all 20 captures: P3 acceptance passes in 12. P2 differences remain in
  MOV-0019-d, h, i and MOV-0020-a, c (routes up to 10 units off, a 2-update wait onset,
  the side of a unit that does not move off its line). The **head-on offset family
  (MOV-0019-j, MOV-0020-b, d) stays P3**: WC3's eastward unit waits about 20 updates; the
  model's waits 0–4 and the westward unit swings 39–47 units wide.
- **Gate:** [run_mov0018.py](tools/run_mov0018.py) `--experiment MOV-0018|MOV-0019|MOV-0020`
  runs in CI for all three, recording every comparator failure and each open
  difference with its rating.

Local CI passes: CTest 3/3, Python 87/87, the generated loop, and the
MOV-0013/0014/0015/0018/0019/0020 gates. [PR #28](https://github.com/galitianu/warcraft-re/pull/28)'s
[workflow 37148140178](https://github.com/galitianu/warcraft-re/actions/runs/37148140178) passes all five
configurations and the aggregate (head `79abf58`). The downloaded artifacts
[regrade](results/mov-0020/pr-verification/summary.md) to a scope report identical to the hosted one,
with MOV-0018, 0019 and 0020 PASS in all five configurations.

## MOV-0021 head-on with a lateral offset

[Issue #27](https://github.com/galitianu/warcraft-re/issues/27), **P3**. The design and predictions were
committed before capture (`f1b2fd7`). Six maps were each captured in three payload-identical fresh WC3
runs ([results](docs/mov-0021.md#results)).

- **No hypothesis survives** (heading, rotation, line). Turning MOV-0019-j by 90°
  changes who stops: clockwise, u0 holds 2 updates and u1 5; anticlockwise, neither
  stops. So absolute position or direction decides, not only the units' relative geometry.
  Without partial routes (e), both units wait.
- A float drift of the eastward unit across a cell boundary (y +0.0005 → −0.024)
  separates the mirror (a, both stop) from the anticlockwise turn (b, neither stops).
  A quick search over cell-overlap stop rules found none that fits all 26 captures.
- **Status:** P3 open in a and e (plus MOV-0019-j and MOV-0020-b, d); P2 in b, c, d and f.
  All are gated with their ratings in [run_mov0018.py](tools/run_mov0018.py), which CI runs for MOV-0018 to 0021.

Local CI passes: CTest 3/3, Python 88/88, the generated loop and every gate.
PR #28's [workflow 37271683517](https://github.com/galitianu/warcraft-re/actions/runs/37271683517)
passes all five configurations and the aggregate (head `35ba687`). The downloaded artifacts
[regrade](results/mov-0021/pr-verification/summary.md) to a report identical to the hosted one,
with MOV-0018 to 0021 PASS in all five configurations.

## Retail pathing mechanism

[Issue #27](https://github.com/galitianu/warcraft-re/issues/27). The fitted collision heuristics
(blocking corridor, give-way side rule, plan-time smoothing) are replaced by the mechanism in WC3's own
movement library. Ghidra decompilation of the retail `Warcraft III.exe` gave the rules, and C++
implements them without game code ([model](docs/footman-v4-model.md#unit-pathing),
[World.cpp](src/core/World.cpp)).

- **Result:** all 26 MOV-0018–0021 captures are canonical PASS: every sample, facing included,
  within the comparator's exact tolerances. Before, 14 failed P3-level acceptance (5 rated P3, 9 P2) and 4 were exact.
- **Interpreted, not read:** two choices were made because they fit the captures. The most
  recently ordered unit updates first, and units with a nonzero velocity are not obstacles to
  planning or to the straight-line test. The A* expansion budget is unknown (32768 is used).
- **Held-out test:** [MOV-0022](docs/mov-0022.md) predicted six new layouts from the clean build
  `2ab1e5c` before capture. All six are canonical PASS and each prediction is byte-identical to the
  C++ trace in its capture bundle ([report](results/mov-0022/grading.md)). The interpreted rules held
  on layouts they were not chosen for.
- **Gate:** [run_mov0018.py](tools/run_mov0018.py) now expects no differences for any of the
  32 captures, so any new one fails CI.
- **Generator:** speed setters on several units are now generated (every CreateUnit, then the
  setters, as in MOV-0002's control). MOV-0022's WATCH records show the speeds applied.

Local native ARM64 AppleClang Release CI passes: CTest 3/3, Python 90/90, the generated loop and
every gate (MOV-0013/0014/0015 and MOV-0018 to 0022).
PR #28's [workflow 37299662085](https://github.com/galitianu/warcraft-re/actions/runs/37299662085)
passes all five configurations and the aggregate (head `003ae9e`).

## Exact next action

For controller deployment, independent review and hosted CI evidence, see
[bootstrap PR #30](https://github.com/galitianu/warcraft-re/pull/30). Live activation
and worker receipts reside in BB thread storage; the configured policy uses Claude
Code/Codex and automatic merges. The controller's first two
product issue increments are milestone 1's
interactive Footman (optional raylib client, ordered live input and headless replay)
and milestone 2's pre-registered three-Footman collision question (blocker list
order, recorded blockers and partial routes around a moving group). More than two
units remains unobserved until that experiment; an interactive client is not yet
implemented. [PR #28](https://github.com/galitianu/warcraft-re/pull/28) is already merged.

Deferred (P1): MOV-0016, which would pre-register the rounded sampler start with T7 and
FU ([next experiment](docs/mov-0015.md#next-experiment)). Revisit it only when most
comparable behavior is in place, or if these differences block something more noticeable.

## Roadmap status

| Phase | Capability / acceptance evidence | Status |
|---|---|---|
| 0 | Automatic map experiment with reliably recoverable WC3 text | Complete — [evidence](docs/phase-0-capture.md) |
| 1 | Small manual map library with shared JASS instrumentation and parseable traces | Complete — [results](docs/phase-1-results.md) |
| 2 | Native C++ headless equivalent and ten numerically comparable traces | Complete — [results](docs/phase-2-results.md); nine movement failures retained |
| 3 | Canonical normalized traces and stable comparison contract | Complete — [results](docs/phase-3-results.md); all 45 retained runs validated |
| 4 | C++ compatibility CI against committed WC3 references | Complete — five configurations pass on PR and main push; [evidence](results/phase-4/main-verification.json) |
| 5 | Declarative scenarios extracted from repeated manual tests | Complete — [results](docs/phase-5-scenarios.md); PR and main push pass; [evidence](results/phase-5/main-verification.md) |
| 6 | One scenario drives C++ and generates a runnable WC3 map | Complete — four maps/12 runs; five-configuration PR and main push PASS; [evidence](results/phase-6/main-verification/summary.md) |
| 7 | Reliable unattended capture for four v1 scenarios; 12 fresh runs, exact reproduction, zero intervention | Complete — [captures](results/phase-7/summary.json); five-configuration PR and [main-push verification](results/phase-7/main-verification/summary.md) |
| 8 | Movement/two-unit collision increment and six held-out pathing layouts | First increment delivered; continued through [the playable roadmap](docs/next-roadmap.md) |

Advance with actual artifacts and verification. Infrastructure checks are not gameplay passes.

# Warcraft III reimplementation

A fresh C++ implementation, developed by measuring real Warcraft III and comparing
small behaviors. Raylib will provide the first renderer; compatibility work will
also run headlessly.

Repository: [galitianu/warcraft-re](https://github.com/galitianu/warcraft-re) (private).

**Target:** Warcraft III **1.29.2 (9231), x86 32-bit**
(`wc3-1.29.2-9231-x86`), running in the user's working Windows 11 Pro ARM64 VM.

The bootstrap movement/oracle gates are delivered. **Next destination:** a playable
Human skirmish, with measured mechanics and an interactive raylib client advancing
together. The project-scoped BB dispatcher supports an 80%
reported-usage cutoff, alternating eligible providers and automatic quota resumption.

Start with:

- [Playable roadmap](docs/next-roadmap.md): interactive Footman → small battlefield
  → recognizable scene → Human base → skirmish → broader compatibility.
- [Continuous development](docs/continuous-development.md): BB installation,
  project-only quota enforcement, worktrees, review/CI and recovery.
- [Bootstrap plan](Warcraft-III-Reimplementation-Plan.md): delivered foundation and
  enduring evidence decisions. Its appendix is historical, not completed work.
- [Client v1](docs/client-v1.md): the optional raylib client, command recording
  and render-schedule replay check.
- [Route display](docs/client-route.md): the selected unit's computed route.
- [Multiple selection](docs/client-selection.md) and [pause/diagnostics](docs/client-pause.md):
  box/shift selection, Space pause, F3 overlay.
- [Progress](PROGRESS.md): current state and the next concrete action.
- [Agent guidance](AGENTS.md): scope, evidence, Windows access, and working rules.
- [Salvage assessment](docs/salvage.md): what the previous work actually contains
  and which pieces may help this plan.
- [Phase 0 capture](docs/phase-0-capture.md): the working map, real observations,
  measured limits, and text extraction procedure.
- [Phase 1 results](docs/phase-1-results.md), [experiments](docs/phase-1-experiments.md)
  and [procedure](docs/phase-1-procedure.md): the manual oracle library.
- [Phase 2 results](docs/phase-2-results.md), [model hypotheses](docs/phase-2-model.md)
  and [build/reproduction](docs/phase-2-procedure.md): the native C++ headless world
  and all ten numerical movement comparisons.
- [Phase 3 contract](docs/trace-contract-v1.md), [results](docs/phase-3-results.md)
  and [reproduction](docs/phase-3-procedure.md): lossless canonical WC3/C++ traces,
  scoped repeatability and validated full-run comparison.
- [footman-v3 model](docs/footman-v3-model.md) and [results](docs/footman-v3-results.md):
  hidden heading, 30 ms updates and truncating float32 state (issue #6).
- [footman-v4 model](docs/footman-v4-model.md) and [results](docs/footman-v4-results.md):
  WC3's own soft-float arithmetic; bit-exact on all ten movement fixtures.
  [MOV-0012](docs/mov-0012.md) explains the east/west heading noise.
- [Phase 4 CI](docs/phase-4-ci.md): reusable build/evidence gate, regression policy,
  workflow matrix and artifact interpretation.
- [Scenario v1](docs/scenario-v1.md) and [Phase 5 results](docs/phase-5-scenarios.md):
  versioned YAML descriptions of MOV-0001–MOV-0010 ([scenarios/](scenarios/)) drive
  the C++ runner, its only input; they reproduced the retired hard-coded cases byte for byte.
- [Phase 6 generation](docs/phase-6-generation.md): scenario-to-JASS generation,
  independent control audit, template bounds and the manual WC3 capture loop.
  Four generated maps reproduce their controls exactly over 12 fresh WC3 runs;
  the same scenarios pass their C++ comparisons under unchanged tolerances.
- [Phase 7 capture](docs/phase-7-capture.md): one command packages and captures
  supported v1 scenarios through UTM/rdpipe, retains validated raw evidence and a
  candidate fixture, and compares C++ using identical scenario bytes.
- [MOV-0013](docs/mov-0013.md) and [scenario v2](docs/scenario-v2.md): four generated
  maps move the 1 ms sampler's start and the order. The remaining frame exceptions
  follow the sampler's own callbacks; the delayed library clock is a new mismatch.
- [MOV-0014](docs/mov-0014.md): three more generated maps test MOV-0013's post-hoc
  readings against pre-registered predictions. The 2⁻¹⁷ s timer start is confirmed
  and adopted; no frame rule survives, and a lag-in-seconds candidate remains.
- [MOV-0015](docs/mov-0015.md): four generated maps test that candidate (T7) and a 30 ms
  update-event facing clock (FU). Both held in three maps. The fourth started one ulp
  later than modelled; from that start, fitted after capture, both fit every map.
- [MOV-0018](docs/mov-0018.md) to [MOV-0021](docs/mov-0021.md): 26 two-Footman collision maps
  (idle blocker, head-on, crossing, glancing, mirrored and turned head-ons). footman-v4 follows
  WC3's own grid pathing mechanism, read from the retail executable
  ([model](docs/footman-v4-model.md#unit-pathing)), and reproduces all 26 exactly.
- [MOV-0022](docs/mov-0022.md): six pre-registered layouts the mechanism had not seen
  (unequal speeds, issue order, a slow crossing unit, a diagonal, an overtake). All six
  captures match the predicted traces exactly.
- [Agent workflow notes](docs/agent-wc3-workflow.md): how to author and capture maps
  efficiently through rdpipe.

This repository holds the plan, 24 manually authored and forty-seven generated-case WC3 maps with their JASS,
plus five Phase 7 verification revisions, shared oracle instrumentation, raw captures with identities, parsers and derived
CSVs, versioned v1/v2 scenarios, and a dependency-free C++20 simulation. Phases 0–6 are
complete; compatibility
CI passes on pull requests and main pushes across five measured macOS ARM64, Linux
x64 and Windows x64 configurations. All 45 Phase 1
raw runs normalize to 15 versioned canonical fixtures with complete provenance.
footman-v4 passes all ten movement cases, and every sample and clock prints
the same six-decimal text as WC3. footman-v1–v3 and their documented failures are
retained. The v0.0.1 comparison and v0.1 oracle infrastructure gates are met;
no release tag has been created. Phase 7 now demonstrates unattended capture for
four reviewed v1 scenarios ([procedure](docs/phase-7-capture.md)); native archival CI
passes, and [PR #25](https://github.com/galitianu/warcraft-re/pull/25) passes all five hosted
configurations. Its merged main-push artifacts also pass and [regrade](results/phase-7/main-verification/summary.md).
Phase 7 is complete for these four scenarios. P1 sampler-order work remains deferred; see PROGRESS for
the next action.

Build and run without a window (CMake, system clang and Python standard library):

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/run_phase3.py --runner build/wc3test --out build/phase3 --reports build/phase3-reports
python3 tools/run_footman_v3.py --runner build/wc3test --out build/issue6 --reports build/footman-v3
python3 tools/run_footman_v4.py --runner build/wc3test --states build/wc3states --out build/v4 --reports build/footman-v4
build/wc3test --model v4 --scenario scenarios --out build/scenario-v4   # direct run
```

Use GitHub issues for concrete work and `PROGRESS.md` for the concise status. Keep
results linked to experiments and commits. `tools/dispatch.py` consumes the issue
queue; its runtime bookkeeping stays outside git. It changes no shared pool
threshold or other project's settings/threads. See the continuous-development
procedure for the cutoff's reporting/in-flight limits and selected-account scope.

Windows access is available through `rdpipe`; run `rdpipe guide` before using it.
Reproduce the complete compatibility CI locally with
`python3 tools/run_ci.py --build build-ci --compiler clang++ --config Release`.
See [Phase 4 CI](docs/phase-4-ci.md) for named build scopes and baseline maintenance.

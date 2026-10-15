# Primitive compatibility CI — Phase 4 / issue #8

Behavioral question: can a clean checkout reproduce finite, valid C++ movement
traces and detect regressions against independent Warcraft III evidence, without
an original game installation? The gate requires all 45 retained Phase 1 runs to
validate, all 15 canonical fixtures plus their index to reproduce byte for byte,
CTest and Python integrity/negative controls to pass, two fresh processes per
model/phase to repeat, and complete comparisons of all ten MOV cases.

The primary model is **footman-v4**, after-due-update, seed 1: **10/10 PASS** is
required, including MOV-0001 and MOV-0002. This promotes the movement result from
[issue #6 / PR #10](https://github.com/galitianu/warcraft-re/pull/10), which already
met the first moving primitive gate. Issue #6 remains open on GitHub; CI does not
implement movement or resolve its issue status. Historical v1/v2/v3 and the
separately labelled v2-before diagnostic remain at **1/10 PASS**. A green job
means compatibility **and** the declared evidence/regression gates succeeded;
it does not make historical failures pass or grade unobserved JASS properties.

## Local entry point

Requires CMake >=3.20, Ninja, a C++20 compiler and Python >=3.10, standard library
only. Run from the checkout; output stays under a separate build directory:

```sh
python3 tools/run_ci.py --build build-ci-release --compiler /usr/bin/clang++ \
  --config Release --expect-arch arm64 --archive
python3 tools/run_ci.py --build build-ci-debug --compiler /usr/bin/clang++ \
  --config Debug --expect-arch arm64
# Linux x64:
python3 tools/run_ci.py --build build-ci --compiler g++ --config Release --expect-arch x86_64
# Windows x64: inside an x64 MSVC developer environment with Ninja on PATH:
python tools/run_ci.py --build build-ci --compiler cl --config Release --expect-arch x86_64
```

`--archive` additionally invokes the unchanged **historical migration policy** in
`run_phase3.py`: exact Phase 2 CSV hashes and statistics. It is required in the
native ARM AppleClang Release job, the measured scope of that archival evidence.
The current-model gate has no permanent v2 CSV equality requirement. Future model
improvements use the same canonical comparator and reviewed before/after metrics.

The entry point configures/builds, runs CTest (including v4's exact six-decimal
text and state-capture probe), runs Python integrity and negative controls,
regenerates references independently of C++, executes all five suites twice, and
calls `compare_traces.py` as a subprocess. Exit **0** is compatible; exit **1** is a
completed incompatibility whose full report must pass the regression policy;
exit **2** is fatal invalid/missing/unsupported input. Other exits, crashes,
timeouts, missing artifacts, incomplete traces and repeatability failures fail.
No blanket failure suppression is used. Each executable process is bounded;
CTest and CI jobs have outer timeouts too. Tests accept `WC3TEST_RUNNER` for other
build directories and `.exe` paths.

## Regression policy v1

[regression.py](../tools/regression.py) consumes complete ten-case canonical
comparison reports, separately from the comparator's compatibility verdict.
The initial reviewed baselines are the committed [Phase 3 v1/v2/diagnostic
reports](../results/phase-3/), [v3 report](../results/footman-v3/v3/comparison.json)
and [v4 report](../results/footman-v4/comparison.json). These were measured on
native ARM macOS; other compilers are **not presumed equivalent**. CI compares
against them and retains any changed metrics for investigation.

Protected on every case and every sample/action/event property:

- Same reference identity/hash, map revision, primary/diagnostic phase, seed,
  record/sample counts, property sets, observed counts and per-unit metric keys.
  Missing observations and changed UNOBSERVED/NOT-APPLICABLE scope fail.
- No new or changed unit/action/event/observable-order structural discrepancy.
  Removed known discrepancies are improvements.
- Failure counts cannot increase, including inside an already-failing case.
  New failures in previously passing properties fail immediately.
- First failure cannot move earlier in reference sequence, including watch order
  at equal callbacks. Later first failures and disappearing failures are improvements.
  Its absolute delta cannot increase at the same location above the protected limit.
- Maximum absolute error overall and for each unit, and absolute final signed
  error for each unit, cannot increase beyond `max(baseline error, property
  tolerance)`. A sign reversal of an out-of-tolerance final error also fails.
  Changes inside an already-passing tolerance are recorded as WITHIN-TOLERANCE.
  This ceiling does **not** alter the comparator's fixed tolerances.

All exact action diagnostics (callback, unit, command, acceptance), time and
relative target X/Y are included. Reports retain signed deltas and every first
failure; smaller protected errors are improvements. One improved metric never
cancels another regressed metric. The primary also requires every case PASS and
CTest's stricter exact-text check, so a new six-decimal mismatch cannot hide
inside a tolerance. All v1/v2 baselines retain MOV-0002's callback-1 Y divergence,
MOV-0009's callback-7 onset, MOV-0004's 53 clock failures beginning at callback 503,
and MOV-0006/7's relative redirect target deltas. These historical reports are
never rewritten to hide a new-model improvement.

For a direct assessment:

```sh
python3 tools/regression.py --baseline results/phase-3/v2/comparison.json \
  --actual build-ci/ci/reports/v2/comparison.json --out build-ci/v2-regression
```

Exit 0 means no protected regression (possibly improvements); 1 means regression;
2 means invalid assessment input. `test_regression.py` uses temporary copies of
real C++ traces. It demonstrates a 1/10 compatible baseline passing regression,
a stationary failure, worse maximum/final error without changing 1/10, earlier
failure, changed command/equal-time action insertion, a legitimate improvement,
invalid/overflow/missing/truncated input, explicit comparator exits, nonzero
runner failure, missing artifacts and timeout. Oracle evidence is untouched.

## Artifacts and build scope

[The workflow](../.github/workflows/compatibility.yml) runs on pull requests,
main pushes and manual dispatch. Since 15 October 2026, the active matrix is macOS
ARM64 AppleClang Release/Debug on the Mac mini and Linux x64 GCC Release/Clang Debug
on `nas-pc`, all self-hosted. The owner temporarily disabled Windows x64 MSVC;
historical five-configuration results below remain valid for their named commits
only. See [self-hosted CI](self-hosted-ci.md). The host is measured through Python and runner environment, and the
compiled target is checked through C++ architecture macros; labels alone are
insufficient. Runner labels route jobs; execution evidence establishes scope.
Account/repository availability is established by actual executions, not this table.
The Windows CI host does not change the x86 retail reference identity.

Clang/GCC use `-fno-fast-math -ffp-contract=off`; MSVC uses `/fp:strict`. Build identity records
compiler/version, target, configuration, source SHA-256, configured Git revision
and dirty state, model/parameters, seed and observation phase. CMake cache and
compile commands record actual compiler flags. The source digest includes both
movement and state probe sources. Source checkout uses LF for hashed text, keeps
raw captures/binary maps unchanged, and JSON writes explicitly use UTF-8/LF so
Windows cannot invalidate evidence via newline conversion.

Every job uploads `build-ci/ci/` even after failure (30-day retention):

- `reports/result.json`, `environment.json`, `summary.md`: gate outcome and scope.
- `reports/fixture-validation.json`, `references/`: all-run verification and
  regenerated fixtures, never a reference taken from the implementation.
- `traces/<model>/` and `<model>-repeat/`: both complete sets of canonical JSON,
  sample/action CSVs and build identity.
- `reports/<model>/comparison.{json,md}`, `regression.{json,md}` and
  `repeatability.json`: per-case/property verdicts, observations/failures, first
  divergences, maximum/final errors, structural/action diagnostics, baseline
  path/hash and explicit comparator exit.
- `reports/v4-state-probe/`: exact-text and state-capture sensitivity reports.
  Named sampling-order exceptions remain reported, not resampled away.
- `archive/`: the separate historical migration evidence, when requested.
- `logs/`: command, timeout, exit, elapsed time and output for each stage.

The job summary includes every case/property and changed regression metric.
Failures retain earlier reports and available traces; setup failures are named
as unverified. Canonical timing-variant CLOCKS/JASS observables remain
**UNOBSERVED**. The separate state probe compares retained clock strings under
its named scope, not general JASS equivalence.

The aggregate job downloads all configurations and rechecks artifact hashes. It
reports observation payload hashes separately from full trace/build hashes and
compares scope across compilers/configurations. Byte differences between hosts
are measured, not automatically called nondeterminism: each host must independently
pass compatibility and its declared regression gate. Two separate process runs
with one binary/seed establish only RNG-DETERMINISTIC-WITH-SEED in that scope;
movement draws no RNG and retail RNG equivalence remains UNKNOWN.

## Phase 5 scenario suites

Added for [issue #12](https://github.com/galitianu/warcraft-re/issues/12)
([scenario v1](scenario-v1.md), [results](phase-5-scenarios.md)). Every suite now
runs `wc3test --scenario scenarios …`: the committed `scenarios/MOV-0001..0010.yaml`
are the runner's only input. Each suite's build identity must list those ten
experiments with paths `scenarios/<experiment>.yaml` and the SHA-256 of the files
in the checkout; `result.json` records them per model as `scenario_sha256`, and
each trace carries `provenance.scenario`. The aggregate job checks that every
trace's provenance matches its build identity and fails if configurations ran
different scenario bytes. CTest adds `scenario_v1` (parser, exact decimals, a
complete schedule for every committed scenario under 4 models × 2 phases), and
Python adds `test_scenarios.py`.

Until [PR #13](https://github.com/galitianu/warcraft-re/pull/13) and its main
push, each suite also ran the hard-coded MOV-0001..0010 control and a per-suite
`migration.json` gate required byte-identical payloads and CSVs. That gate passed
on all five configurations on both triggers
([main verification](../results/phase-5/main-verification.md)); the control and the
gate were then removed. Retained Phase 3/4 traces have no scenario provenance;
they came from the hard-coded runner.

## Baseline maintenance and delivery evidence

Never change raw captures, fixtures or tolerances to make a job green. Investigate
any regression report first. An intentional improvement must identify its model
revision and retain complete before/after reports under the same WC3 evidence.
Only then promote newly passing properties/cases and change the explicitly named
baseline path in `BASELINES`. If an additional platform differs numerically,
measure and explain its before/after values before adopting a distinct baseline;
do not import native ARM's byte promise blindly. Baseline review must also preserve
structure/action diagnostics and the named observation phase.

Local native ARM AppleClang Release and Debug: CTest 2/2, Python 50/50, 45 runs,
15 fixtures, v4 10/10, v1/v2/v3 and v2-before 1/10, with no protected regression.
Release/Debug observation payloads match for all five suites. Release archival
migration reproduces the 60 Phase 2 CSVs and 30 historical state reports.
PR and real main-push evidence are retained below; both workflow triggers
have executed successfully on the five measured configurations. No release tag
is part of this work.

### First hosted execution and reviewed Linux baseline

[PR run 36858894376](https://github.com/galitianu/warcraft-re/actions/runs/36858894376)
executed all five requested configurations; the repo/account permitted all runners.
[Retained identities, repeatability hashes and assessments](../results/phase-4/initial-hosted.json)
record the run's actual PR merge source identity separately from its head commit.
Both ARM macOS jobs passed all gates. Linux GCC 13.3.0 Release and Clang 18.1.3
Debug passed v4 10/10 and all integrity checks, but **correctly failed the initial
ARM baseline** on historical MOV-0007 facing. Windows MSVC built and passed CTest
2/2; provenance path separators and Unicode CLI output prevented its evidence
pipeline from completing. Those are portability bugs, not gameplay passes.

Comparing every record shows Linux differs from native ARM only in MOV-0007
SAMPLE facing: v1 callbacks 51–250 (200 records); v2 and v2-before callbacks
76–250 (175 each). ARM prints `179.999985`; Linux prints `180`. GCC Release and
Clang Debug payloads agree for every case/model, and v3/v4 payloads also agree
with ARM. Historical `heading()` calls float `std::atan2` and multiplies by
`180.0f / pi_v<float>`; the westward result is sensitive to the platform's libm.
The added `math_scope` runtime probe measures this exact boundary separately
from retail evidence. The library explanation is an inference from that code and
these records; the subsequent hosted probe directly confirms the adjacent
`atan2` results at this westward boundary.

The complete [Linux v1](../results/phase-4/baselines/x64-libm/v1/comparison.json),
[v2](../results/phase-4/baselines/x64-libm/v2/comparison.json) and
[v2-before](../results/phase-4/baselines/x64-libm/v2-before/comparison.json)
baselines retain comparison reports, original ARM regression assessments and
two-process hashes. Only these historical suites select the measured x64 libm baseline on
Linux/Windows x64; the baseline reports identify their original Linux producer. The actual protected changes are:

| Metric | ARM | Linux |
|---|---|---|
| v1 MOV-0007 facing max absolute delta (overall/u0) | 179.862395° | 179.862410° |
| v1/v2/v2-before MOV-0007 facing final signed delta u0 | +0.3689730000000111° | +0.36898800000000165° |

Failure counts, first divergences, other properties, action/structure diagnostics,
reference hashes and tolerances are unchanged. This is a measured platform
baseline for historical models, not a tolerance relaxation or a new retail match.
All historical suites remain 1/10, and v4's original native baseline still gates
every host. The initial failures and full before/after evidence remain visible.


[The second hosted run](https://github.com/galitianu/warcraft-re/actions/runs/36859644989)
passes every macOS/Linux job. Windows now validates 45 captures and 15 fixtures,
passes CTest 2/2 and Python 50/50, and compares all five suites. Its only remaining
failures are the same historical facing metrics against the initial ARM baseline.
[Windows review evidence](../results/phase-4/windows-review.json) retains those
failures, complete identity and two-process hashes. Every Windows observation
payload equals Linux for every case/model, and the reviewed x64 baseline gives
zero protected-metric changes. It is shared rather than duplicating identical
reports under another host name.

Runtime `math_scope` results: ARM AppleClang `atan2_bits=40490fda`,
`heading_bits=4333ffff` (179.999985°); Linux GCC and Windows MSVC
`atan2_bits=40490fdb`, `heading_bits=43340000` (180°). All use
`degrees_per_radian_bits=42652ee0`. This directly measures the float libm boundary
responsible for the retained historical west-facing difference; it establishes
no new retail compatibility claim.


### Successful hosted verification

[PR run 36860045397](https://github.com/galitianu/warcraft-re/actions/runs/36860045397)
passes **all five configurations and the aggregate job**. Permanent
[JSON evidence](../results/phase-4/hosted-verification.json) and
[scope summary](../results/phase-4/hosted-verification.md) retain actual host/target,
compiler versions, build/source/model/seed identities, observation/full trace
hashes, compatibility counts and workflow identity. Complete per-property reports,
traces, logs, fixture validation and state sensitivity remain in the run artifacts
(30-day retention). Earlier failures remain committed independently.

| Verified configuration | Compiler | Result |
|---|---|---|
| macOS ARM64 Release / Debug | AppleClang 17.0.0.17000013 | Both PASS |
| Linux x64 Release | GCC 13.3.0 | PASS |
| Linux x64 Debug | Clang 18.1.3 | PASS |
| Windows Server 2022 x64 Release | MSVC 19.44.35229.0 | PASS |

Every configuration passes CTest **2/2**, Python **50/50**, all **45** retained
Phase 1 runs, all **15** byte-reproduced fixtures plus the index, two fresh
processes per suite, and full ten-case comparison. v4 is **10/10 PASS** with
exact six-decimal text. Historical suites are **1/10**, with no regression under
the named native/x64 baselines. Native ARM Release also passes the separate
archival migration gates. v3/v4 observation payloads are identical across all
five measured configurations; v1/v2/v2-before have exactly two MOV-0007 payloads
(the explained libm difference) and one for every other case. Full trace hashes
have five variants per case because build identities differ. No broader byte,
JASS, RNG or untested compiler/host claim follows.

### Main-push verification and completed handoff

[PR #11](https://github.com/galitianu/warcraft-re/pull/11) merged as
`bdaa9ac55c7f425f0b10c67f3c12161879f69988` on 1 October 2026.
[Main run 36861964114](https://github.com/galitianu/warcraft-re/actions/runs/36861964114)
is a real **push** workflow on that merge commit. All five configurations and the
aggregate job pass. [Permanent JSON evidence](../results/phase-4/main-verification.json)
and [summary](../results/phase-4/main-verification.md) bind the run to its actual
source/build/model/compiler/host/seed identities. Every configuration records
`git_dirty_at_configure=false` and the exact merge SHA; runner metadata records
`GITHUB_EVENT_NAME=push` and the same SHA.

Downloaded artifacts were rechecked locally using the committed standard-library
tools. All observation/full file hashes reproduce; all **25 canonical suite
comparisons and regression assessments** recomputed from the downloaded traces
match the published reports. Fixture-validation reports confirm **45** runs,
**15** fixtures and no byte differences; logs and recorded exits confirm CTest
**2/2** and Python **50/50** per configuration. v4 remains **10/10**, historical
suites **1/10**, with zero protected-metric changes under the reviewed baselines.
Native ARM Release also passes the separate archival migration gate. Earlier
PR failures and their explanations remain independent evidence.

Both the CI/regression capability gate in issue #8 and the first moving primitive
requirement promoted from issue #6 are demonstrated under this scope. Phase 4's
handoff is complete. Canonical JASS/CLOCKS properties remain UNOBSERVED; the state
probe's named sampling-order exceptions and untested host/compiler/RNG scope
remain the previously documented limits. No tolerance, fixture or raw capture
changed, and no release tag or fresh retail capture was created.

**Exact next action:** design the sampler/update-order experiment named in the
[v4 results](footman-v4-results.md#sampling-order), using the documented capture
workflow before authoring or running a new map.

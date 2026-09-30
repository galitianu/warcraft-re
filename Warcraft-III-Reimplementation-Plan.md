# Warcraft III reimplementation plan

> Build the smallest measurable piece of Warcraft III compatibility first, then grow the C++ engine and its experimental tools together.

Prepared 28 September 2026; updated 29 September 2026 from [Reimplementation Strategy](chatgpt-conversation://6abac337-5df8-83ed-9214-817dea88fc50).

## Scope and how to use this document

This is an implementation plan distilled from the referenced conversation, with the final **Phase 0–8 bootstrap sequence** as its backbone. It covers the engine, raylib boundary, oracle, test design, RNG, CI, hardware, and later investigations.

The conversation API returned **five exchanges**, with no further pages or attachments. All five are reproduced chronologically in Appendix A, including their code, commands, numbers, examples, alternatives, and qualifications. The first retrieved message refers to earlier context (“this is close to what i wanna build”); that earlier context was not present in the returned conversation and has not been invented here.

The checkboxes and acceptance gates below turn the discussion into executable work. Checked items record decisions or validation explicitly reported by the user; unchecked items remain planned work. Example outputs, percentages, tolerances, timing values, paths, version strings, and command syntax are proposed illustrations, **not measured results or tools that already exist**. This document reorganizes the discussion rather than independently validating its technical claims.

### Target correction — 29 September 2026

Build-number correction, 30 September 2026: executable metadata from both installed
copies verifies **1.29.2.9231**, x86. Andrei confirmed that the previously written
`9321` was a typo; the active target and reference identifier below use `9231`.

The compatibility target is **Warcraft III 1.29.2 (9231), x86 32-bit only**. The user has tested it successfully in a **virtualized Windows 11 Pro ARM64 VM**, which is the selected oracle environment. The earlier assumptions about an x64 WC3 build, comparisons between x86 and x64 WC3, and a Windows 10 x64/QEMU setup are superseded. No x86-versus-x64 WC3 comparison is planned.

Use `wc3-1.29.2-9231-x86` as the reference build identifier. Record the Windows 11 Pro ARM64 VM configuration separately from the game's architecture. Running the game successfully was established by the user's test; Phase 0 now records automatic experiment execution and repeatable trace extraction below.

## 1. Decisions and precedence

| Topic | Direction to follow | Earlier proposal or remaining uncertainty |
|---|---|---|
| Project | Build a C++ Warcraft III reimplementation, using real WC3 behavior as the specification. | Do not turn this into a mandatory Warsmash port. |
| Rendering | Start with raylib behind a thin renderer boundary; replace it if concrete limitations arise. | Avoid designing a hypothetical Vulkan abstraction up front. |
| Reference platform | **Windows 11 Pro ARM64 VM**, already tested successfully by the user. | Reuse the working virtualized ARM environment; the earlier Windows 10 x64/QEMU proposal is superseded. |
| WC3 executable | **Warcraft III 1.29.2 (9231), x86 32-bit only.** | No x64 WC3 build or x86/x64 comparison belongs in this plan. |
| Oracle | Start with black-box JASS experiments in real WC3 and recover machine-readable observations. | Debuggers, hooks, and memory inspection are later research tools. |
| Bootstrap order | Manual maps → tiny C++ world → common traces/comparator → CI → scenario format → map generation → VM automation → expansion. | The earlier “design the scenario schema first” suggestion is superseded by the final phased answer. |
| Warsmash | Optional source of hypotheses/formulas when stuck; WC3 evidence decides correctness. | The earlier three-engine adapter/matrix is retained as an optional future facility, not a dependency. |
| Ordinary CI | Run the new engine against committed reference traces/images. | Do not require original WC3 on every commit or PR. |
| Random behavior | Remove randomness when testing deterministic mechanics; characterize RNG separately. | Exact seed/stream compatibility is a later target, not a prerequisite for initial abilities. |
| Schedule | Advance through demonstrated capabilities and acceptance gates. | “A couple weeks,” “first several months,” 95%+ ARM development, and sample pass counts in the conversation were illustrative expectations, not commitments. |

**Authority order:** WC3 experimental evidence → inferred behavioral model → Warsmash research → other open-source WC3 research.

## 2. Phase roadmap

| Phase | Capability gained | Exit gate |
|---|---|---|
| 0 | Measure real WC3 | A manually authored map runs its experiment after loading and produces recoverable machine-readable output. |
| 1 | Repeat manual experiments | Roughly 10–20 small maps share JASS instrumentation and produce parseable traces. |
| 2 | Compare the first C++ behavior | A native ARM Mac headless world runs an equivalent movement experiment; both outputs can be compared. |
| 3 | Make comparisons useful | Both systems use a normalized trace format; the comparator reports the first divergence with explicit tolerances. |
| 4 | Protect progress in CI | C++ compatibility tests run against committed WC3 fixtures without launching WC3. |
| 5 | Extract the scenario format | After roughly 20–50 manual tests reveal repetition, C++ consumes declarative scenarios. |
| 6 | Generate oracle maps | The same scenario produces a WC3 test map and drives the C++ world. |
| 7 | Automate capture | A controller builds, transfers, runs, retrieves, and normalizes VM experiments reliably. |
| 8 | Expand coverage systematically | Microscopic tests, sweeps, and RNG research drive increasingly complete compatibility. |

**First release, v0.0.1:** one Footman can move, and that movement can be compared numerically with real WC3. A numerical comparison is valuable even before it passes.

**Oracle infrastructure milestone, approximately v0.1:** one scenario drives WC3 and C++, and the resulting traces can be compared. Fully automated operation of the Windows 11 Pro ARM64 VM follows when it becomes worth the effort.

## 3. Phase 0 — Prove that WC3 is measurable

### Work

- [x] Select Warcraft III 1.29.2 (9231), x86 32-bit, as the compatibility target.
- [x] Establish that the game runs in the Windows 11 Pro ARM64 VM (tested by the user).
- [x] Record the installed executable identity and working VM configuration for reproducible captures.
- [x] Reuse that VM for the first oracle map experiment.
- [x] Make one tiny test map by hand, with two Footmen, a timer, and JASS instrumentation.
- [x] Issue the movement order programmatically so the experiment runs without interaction once the map loads.
- [x] Emit recognizable start/end markers and position/facing observations.
- [x] Investigate and prove an output extraction mechanism: scripting-supported file output, log/debug output, or another minimally invasive capture method.
- [x] Run the same simple experiment repeatedly to establish basic reliability.

Illustrative raw output:

```text
TEST_BEGIN MOV-0002
T=0 X=0 Y=0 FACING=0
T=32 X=5.25 Y=0 FACING=0
T=64 X=10.50 Y=0 FACING=0
...
TEST_END
```

These timestamps and values are placeholders. Establish timestamp units and actual observation cadence experimentally.

Evidence, 30 September 2026: [Phase 0 capture procedure and 20-run results](docs/phase-0-capture.md).

### Deliverable and gate

A test map plus a documented procedure that reliably yields **WC3 → text file**. Loading the map and retrieving the file may still be manual. Do not require VM launch automation here.

**Resolved, 30 September 2026:** the native PreloadGen route reliably writes complete text in the verified installation. The linked evidence records the mechanism and limits.

## 4. Phase 1 — Build a small manual oracle library

### Work

- [ ] Create approximately 10–20 manually authored maps, each answering one narrow question.
- [ ] Put shared instrumentation into a small JASS library.
- [ ] Establish permanent test IDs and human-readable descriptions.
- [ ] Parse the recovered output with a Python or C++ script; inspect CSV or simple plots.
- [ ] Keep world setup and instrumentation simple enough to understand every observation.

```text
oracle-maps/
  MOV-0001.w3x
  MOV-0002.w3x
  ORD-0001.w3x
  COM-0001.w3x
```

Initial instrumentation vocabulary:

```text
OracleBegin(testId)
OracleWatchUnit(name, unit)
OracleSample()
OracleLogEvent(...)
OracleEnd()
```

The acceptable loop is still: edit JASS → open map → run WC3 → retrieve output → parse → inspect CSV.

Use stable entity names such as `u0`, `attacker`, and `target`. Learn what can actually be observed before designing the declarative schema.

### Deliverable and gate

Reusable JASS instrumentation and a small collection of reproducible, parseable experiments.

**ID reconciliation:** the early bootstrap examples called a moving-unit experiment MOV-0001, while the final milestone/test list used MOV-0001 for stationary and MOV-0002 for straight movement. Adopt the latter consistently for implementation; preserve the original examples in Appendix A. Once assigned, do not reuse permanent IDs for different experiments.

## 5. Phase 2 — Bootstrap the C++ engine beside the oracle

### Work

- [ ] Create a CMake C++ project that builds natively on the ARM Mac.
- [ ] Implement a tiny headless `World`, `Unit`, orders, coordinate state, and a trace capture path.
- [ ] Centralize randomness from the start, even if the initial movement test does not need it.
- [ ] Hard-code an equivalent stationary/movement experiment through the World API.
- [ ] Run a finite number of steps and emit observations suitable for comparison with WC3.
- [ ] Keep raylib in a separate renderer directory; do not require a window for compatibility work.

Minimal initial structure:

```text
src/
  core/
    World.cpp
    Unit.cpp
    Orders.cpp
    Random.cpp
  renderer/
    raylib/
tools/
  wc3test/
oracle/
  jass/
tests/
```

Illustrative runner:

```cpp
World world;
auto footman = world.createUnit(UnitType::Footman, {0, 0});
footman.issueMove({1000, 0});

for (int i = 0; i < 500; ++i) {
    world.step();
    trace.capture(world);
}
```

The loop count is illustrative; it does not establish WC3's simulation quantum.

### Deliverable and gate

Two traces of the same primitive experiment: one from WC3, one from C++. Their differences can be examined numerically. This is the first meaningful project milestone and the basis of **v0.0.1**.

### Explicitly deferred

No W3X parsing, arbitrary map loading, MDX, BLP, terrain rendering, JASS interpreter, abilities, full UI, networking, YAML, or automatic map generation is required for this milestone. A unit, coordinates, an order, and observations are enough.

## 6. Phase 3 — Stabilize traces, normalization, and comparison

### Trace contract

- [ ] Record test identity, exact engine/build identity, observations, and events.
- [ ] Use oracle elapsed time with explicitly declared units; integer milliseconds/microseconds are options.
- [ ] Measure WC3's update cadence independently instead of assuming an engine tick matches it.
- [ ] Preserve exact observation order with monotonically increasing sequence numbers, including records sharing a timestamp.
- [ ] Normalize raw WC3 output into canonical JSON.
- [ ] Preserve observed numeric precision; choose tolerances in the comparator, not by rounding the reference.

Minimal illustrative structure, extending the conversation's sample to make units explicit:

```json
{
  "test": "MOV-0002",
  "engine": "wc3-1.29.2-9231-x86",
  "environment": "windows-11-pro-arm64-vm",
  "time_unit": "ms",
  "samples": [
    {
      "t": 0,
      "units": {
        "u0": {"x": 0, "y": 0, "facing": 0, "order": 851986}
      }
    }
  ],
  "events": []
}
```

The final schema should follow measured needs; sequence numbers must also cover interleaving between events and state observations when that ordering matters.

### Comparator

- [ ] Compare numerical properties with explicit per-property tolerances.
- [ ] Compare order IDs, unit types, and event sequence strictly when the test requires it.
- [ ] Report sample count, property-level pass/fail, first divergence, reference/actual values, and deltas.
- [ ] Continue far enough after the first mismatch to reveal accumulating error.

Starting example only:

```yaml
tolerance:
  position: 0.001
  facing: 0.001
  life: 0.0001
  time: 0.002
strict:
  order: true
  event_sequence: true
  unit_type: true
```

Here the illustrative time tolerance is in seconds; convert explicitly if the trace stores milliseconds. Do not silently relax thresholds until tests pass.

Proposed command:

```bash
wc3test compare reference/wc3-1.29.2-9231-x86/MOV-0002.json build/tests/MOV-0002.json
```

A useful report identifies, for example, “Facing first differs at sample 17: WC3 14.0625°, ours 14.0000°,” or shows position drift growing from +0.006 to +0.013 to +0.021.

### Repeatability classification

Capture each new experiment repeatedly—20 runs was the proposed example—and compare those runs before treating the output as a fixed fixture. Track:

- `DETERMINISTIC`
- `RNG-DETERMINISTIC-WITH-SEED`
- `NONDETERMINISTIC`
- `UNKNOWN`

A changing damage value may reveal RNG; changed timings may indicate other nondeterminism. Investigate rather than selecting one run arbitrarily.

### Deliverable and gate

Both implementations emit compatible traces; comparison produces actionable failures and distinguishes deterministic expectations from unresolved randomness.

## 7. Phase 4 — Put primitive compatibility tests in CI

### Work

- [ ] Commit normalized reference traces grouped by the verified WC3 build.
- [ ] Run CMake, compilation, unit tests, primitive scenario execution, and trace comparison.
- [ ] Make stationary MOV-0001 and straight-line MOV-0002 pass, then grow the small suite.
- [ ] Report real compatibility counts as tests are added.
- [ ] Extend the fast build/test matrix across macOS ARM64, Linux x64, and Windows x64 as infrastructure allows.

```text
reference/
  wc3-1.29.2-9231-x86/
    MOV-0001.json
    MOV-0002.json
    ORD-0001.json
```

Ordinary CI runs the C++ engine against these fixtures. **WC3 does not run in ordinary CI.** The conversation's “12/17 passing” example illustrates progress reporting, not a current result.

### Deliverable and gate

A change can be checked automatically for WC3 compatibility regressions without requiring an original WC3 installation on the CI host.

## 8. Phase 5 — Extract a declarative scenario format

Introduce this after roughly 20–50 manually implemented tests make repeated patterns clear: create units → set properties → wait → issue orders → observe.

### Work

- [ ] Define an engine-independent, versioned experiment description.
- [ ] Support the needs already demonstrated by real tests.
- [ ] Make the C++ runner consume it first.
- [ ] Map declarations onto the same World API used by the hard-coded runner.
- [ ] Keep one logical scenario independent of WC3, the C++ implementation, and any optional Warsmash adapter.

Initial example:

```yaml
id: MOV-0017
units:
  u0:
    type: hfoo
    position: [0, 0]
    facing: 90
    movement_speed: 270
actions:
  - at: 1.0
    unit: u0
    order: move
    point: [1000, 0]
observe:
  units:
    u0: [x, y, facing, order]
duration: 5
```

The broader schema discussed also includes name/version, map size/terrain, owner, target units, observation interval, life observations, event selection, queries, visual camera setup, screenshots, comparison rules, and parameter matrices. Add these when their corresponding tests need them.

The earlier combat example used an empty 64×64 grass world, an owner-0 Footman at [0, 0] facing 0°, an owner-1 Footman at [300, 0] facing 180°, an attack at 1 second, 0.01-second observations, attacked/damaged/death events, and 5-second duration. Treat this as a target schema example; actual sampling capabilities must be measured.

### Deliverable and gate

`scenario.yaml → wc3test → C++ World → trace` works for existing tests. YAML replaces repetitive setup rather than delaying the first useful comparison.

## 9. Phase 6 — Generate WC3 tests from the same scenarios

### Work

- [ ] Build an oracle compiler/generator that emits JASS and packages a test map.
- [ ] Initially copy a template W3X containing flat terrain, no doodads, fixed players, Oracle.j, and the test bootstrap.
- [ ] Inject generated unit creation, property setters, scheduled actions, unit registration, and finish time.
- [ ] Use the same logical scenario on the C++ side, optionally through normalized scenario JSON.
- [ ] Keep instrumentation reusable; generated JASS should mainly express the experiment.
- [ ] Compare the two resulting traces.

Proposed generation commands from the discussion included `compile`, `generate`, and `build`. These were sketches of related capabilities, not three mandatory implementations; choose a coherent CLI when implementing them.

```text
                       scenario.yaml
                       /           \
                 WC3 generator    C++ runner
                      |                |
                generated.w3x       World API
                      |                |
                 real WC3           wc3cpp
                      |                |
                  wc3.json          ours.json
                       \            /
                         comparator
```

### Deliverable and gate

One scenario produces equivalent experiments in both environments. This is the **v0.1 oracle infrastructure** milestone even if running the VM and copying results remain manual.

## 10. Phase 7 — Automate Windows 11 Pro ARM64 VM capture when manual work becomes costly

Initially, `wc3oracle build MOV-0017` followed by manual execution and result copying is acceptable. A handful of new tests per day does not justify building every automation component first.

### Work

- [ ] Introduce a capture command once repeated manual transfer/run/retrieval becomes a practical bottleneck.
- [ ] Integrate with the existing Windows 11 Pro ARM64 VM and its available automation/file-transfer mechanisms; document the VM product and configuration rather than assuming a QEMU/TCG setup.
- [ ] Generate the map.
- [ ] Copy it into a shared VM directory.
- [ ] Launch WC3 and load the map.
- [ ] Let the scripted experiment finish and signal completion.
- [ ] Retrieve the raw trace.
- [ ] Normalize it and produce a candidate reference.
- [ ] Run repeated captures and validate reproducibility before treating a result as canonical.
- [ ] If a result is suspicious, optionally run the same WC3 1.29.2 (9231) x86 executable on the Windows laptop as a control. This checks environment-dependent behavior, not different game architectures.

Proposed endpoint:

```bash
wc3oracle capture MOV-0017
```

### Deliverable and gate

The full capture pipeline works unattended for supported experiments and produces validated, normalized outputs. Graphics reliability and output extraction remain practical success criteria; mere process launch is insufficient.

## 11. Phase 8 — Expand compatibility through experiments

### First movement suite

| ID | Question |
|---|---|
| MOV-0001 | Stationary unit |
| MOV-0002 | Straight movement |
| MOV-0003 | Diagonal movement |
| MOV-0004 | Movement speed 100 |
| MOV-0005 | Movement speed 522 |
| MOV-0006 | 90° turn |
| MOV-0007 | 180° turn |
| MOV-0008 | Interrupted movement |
| MOV-0009 | Target behind the unit |
| MOV-0010 | Stop order |

Investigate surprising behavior with focused sweeps. The conversation's example samples angles 170°, 172°, 174°, …, 190° across MOV-0030 through MOV-0040, then plots the traces to infer the algorithm.

```bash
wc3oracle capture MOV-0030..MOV-0040
```

The larger example crosses movement speeds [100, 200, 270, 400, 522], turn rates [0.1, 0.25, 0.5, 1.0], and angles [10, 45, 90, 135, 180], producing 100 experiments.

### Work cycle

- [ ] Formulate one precise behavioral question.
- [ ] Create a microscopic experiment.
- [ ] Capture repeated WC3 observations.
- [ ] Sweep parameters if needed.
- [ ] Plot/analyze and infer a model.
- [ ] Consult Warsmash or other projects if useful.
- [ ] Implement the model in C++.
- [ ] Make the new tests pass without regressing existing tests.
- [ ] Link unusual compatibility code to the experiment proving it.
- [ ] Move to the next behavior, such as collision after basic movement.

“43/43 movement tests passing” was an illustrative reporting goal. Progress means experimentally supported behavior, not simply more implemented classes.

### Coverage backlog

- **Movement:** acceleration, deceleration, turn rate, collision, target reached, interruptions.
- **Combat:** damage, armor, attack point, backswing, cooldown, projectile behavior, acquisition.
- **Other systems:** orders, abilities, pathing, JASS/API semantics, rendering, RNG.
- **Later integration:** maps, replay tests, long simulations, parser fuzzing, and broad compatibility suites.

Do not begin with a ten-minute melee game when a single controlled interaction can answer the question.

## 12. Oracle design requirements carried through all phases

The oracle's job is to set up an experiment, stimulate real Warcraft, observe exposed behavior, and emit an unambiguous trace. It should not encode assumptions from the new engine.

### JASS instrumentation

Possible module split:

```text
oracle/jass/
  Oracle.j
  OracleUnits.j
  OracleEvents.j
  OracleOrders.j
  OracleTiming.j
```

Functions discussed include unit registration, scheduled attacks, finish time, and logging real/int properties through calls such as `GetUnitX`, `GetUnitY`, and `GetUnitCurrentOrder`.

Use an identifiable prefix and unambiguous records, for example:

```text
@O|00000100|UNIT|attacker|X|0.000000
@O|00000100|UNIT|attacker|Y|0.000000
@O|00000100|UNIT|attacker|ORDER|851983
@O|00001000|ACTION|ATTACK|attacker|target
@O|00001031|EVENT|ATTACKED|attacker|target
@O|00001467|UNIT|target|LIFE|407.000000
```

An earlier alternative envelope was `WC3TEST 1` followed by `TICK` and `EVENT` records. Preserve its intent—recognizable, parseable output—but use elapsed time initially rather than assuming WC3 ticks.

### Four observation classes

| Class | Required scope discussed |
|---|---|
| State | Position, facing, HP, mana, current order, owner, level, XP, hero stats, movement speed, fly height, ability levels, resources, food, unit type |
| Events | Attacked, damaged, death, spell channel/cast/effect/finish/endcast, order issued, point order, target order, region enter/leave, item events, hero events |
| Queries | Timed API-result probes, such as distance(attacker,target) and current_order(attacker); particularly useful for JASS compatibility |
| Visual | Fixed camera position/target, timed screenshots, reference/actual images, image comparison |

Availability and semantics of each observation must be established for the actual target patch. The conversation's example `life_changed` record is a proposed observation, not proof of a native event.

Keep visual and simulation tests separate unless the behavior genuinely needs both. A timestamp alone cannot distinguish same-time events: record sequence numbers, such as damaged event seq 381 followed by life state seq 382.

### Normalization and precision

Keep raw output as experimental evidence while committing normalized references as the comparison contract. If WC3 emits life 406.999969482, preserve it; do not replace it with 407 before comparison. Record time semantics and numeric precision consistently.

## 13. RNG plan

### 13.1 Isolate mechanics from chance

Use guaranteed outcomes when the game permits them. For critical damage multiplication, set chance to 100% and multiplier to 3.0.

Split critical-strike work into:

- CRIT-001: damage calculation.
- CRIT-002: event ordering.
- CRIT-003: floating text.
- CRIT-004: armor interaction.
- CRIT-005: evasion interaction.
- CRIT-006: probability distribution.

A 15% critical event occurring on different individual attacks is not automatically a compatibility failure.

### 13.2 Characterize truly random behavior statistically

- [ ] Capture large samples where probability itself is under test; 100,000 attacks and one million samples were suggested scales.
- [ ] Record normal/critical counts and observed rates.
- [ ] Use an appropriate statistical test or confidence interval rather than an arbitrary percentage tolerance.
- [ ] Store the entire outcome sequence as well as aggregate counts.
- [ ] Examine gap distributions and conditional probability after 0, 1, 2, … failures.
- [ ] Investigate correlations and reset rules.

Independent 15% trials and a pseudo-random distribution can have similar averages but different streak behavior. **PRD is a hypothesis to test per mechanic**, not an established conclusion. A binomial model assumes independence; use it only where appropriate to the measured process.

Illustrative conversation data included 15,073 crits in 100,000 attacks (0.15073), 149,872 in one million (0.149872), and hypothetical conditional probabilities increasing 0.032, 0.064, 0.096, 0.128, 0.160 after failures. None is a captured result.

### 13.3 Give RNG its own suite and analysis tool

```text
tests/rng/
  random_integer/
  random_real/
  damage_variance/
  critical_strike/
  evasion/
  bash/
  item_drop/
  attack_damage/
  proc_distribution/
```

Proposed commands:

```bash
wc3oracle capture RNG-CRIT-001 --runs 1000000
wc3oracle analyze RNG-CRIT-001
```

Clarify in implementation whether “runs” means map launches, experiment repetitions, or individual trials; the conversation uses the word illustratively. Avoid accidentally designing one VM launch per attack.

Reports should include sample/trigger counts, observed and nominal probability, gap distributions, and assessment of independent-RNG versus PRD hypotheses.

### 13.4 Investigate seeding and stream sharing early

- [ ] Emit immediate `GetRandomInt(0, 2147483647)` sequences across repeated game/map starts.
- [ ] Test possible initialization influences: game startup, map startup, system time, player slot, map checksum, and game mode.
- [ ] Compare attacks alone against an extra JASS RNG call followed by the same attacks.
- [ ] Determine whether JASS and gameplay randomness appear to share state.
- [ ] Investigate whether multiple RNG sources exist.

Shifted attack outcomes are evidence about shared state, requiring controlled follow-up rather than an automatic conclusion.

### 13.5 Track three compatibility levels

| Level | Meaning |
|---|---|
| 1 — Distribution | Similar long-run rates, such as approximately 15% procs |
| 2 — Algorithm | Matching mechanics, correlations, probabilities, and reset rules |
| 3 — Bit/sequence | Same seed yields the same stream and decisions |

Investigate generator identity and seed control over time. Exact compatibility matters for future replay/network determinism, but Level 3 is not required to start implementing critical strike.

Centralize randomness through a replaceable abstraction:

```cpp
class RandomSource {
public:
    virtual uint32_t nextInt() = 0;
    virtual float nextReal() = 0;
};

// Example consumer:
if (world.random().roll(chance)) {
    critical();
}
```

Do not scatter `rand() % 100` through simulation code. Allow replacing a temporary generator with a verified Warcraft generator. Leave room for Combat/Jass/Loot domains if experiments establish separate streams; do not assume they are independent in advance.

## 14. Engine and renderer architecture

Use **wc3core → renderer interface → raylib backend**. Simulation, Warcraft formats, MDX animation state, particles, and terrain representation should not depend on raylib types or lifecycle.

A possible thin interface:

```cpp
class Renderer {
public:
    virtual void beginFrame(const Camera& camera) = 0;
    virtual void drawTerrain(const TerrainRenderData&) = 0;
    virtual void drawModel(const ModelInstance&) = 0;
    virtual void drawParticles(const ParticleBatch&) = 0;
    virtual void drawUI(const UICommandList&) = 0;
    virtual void endFrame() = 0;
};
```

Potential reasons to replace raylib later include custom passes, exact WC3 blending, shaders, batching, or platform-specific graphics requirements. Vulkan, Metal, and D3D were possible future backends, not present commitments.

Direct world construction should remain useful:

```cpp
TestWorldBuilder()
    .unit("u0", "hfoo", {0, 0})
    .unit("u1", "hfoo", {500, 0})
    .run();
```

Later, W3X → map loader → the same World API. The same World feeds both HeadlessTest and RaylibRenderer.

A JASS interpreter and arbitrary W3X loading can be deferred for the early months if direct construction supports the compatibility work. Their delay is a scope choice, not a claim that full map compatibility will never need them.

## 15. Hardware and reference-environment plan

### Selected starting arrangement

| Machine/service | Role |
|---|---|
| ARM MacBook Pro | Interactive development |
| ARM Mac Mini | Remote agents, native clang/CMake builds, wc3core, raylib client, long tests, ARM CI, optional Docker/Linux ARM tests; intended host for routine VM oracle captures |
| Windows 11 Pro ARM64 VM | Selected oracle environment; the user has already tested that WC3 1.29.2 (9231) x86 runs successfully here |
| Hosted CI, e.g. GitHub Actions | macOS ARM64, Linux x64, Windows x64 builds of the new C++ engine, subject to runner availability |
| Windows laptop | Optional control for disputed observations, running the same WC3 1.29.2 (9231) x86 executable |
| Steam Deck | Later Linux x86_64 native-client and Wine/Proton testing |

Do not require all machines to participate initially. Reuse the working VM where it is currently hosted; record or reproduce its configuration on the Mac Mini when moving routine captures there. A self-hosted Windows runner remains an optional later convenience.

The C++ engine's cross-platform build matrix is separate from the original game's architecture: a Windows x64 C++ CI build does not imply an x64 WC3 reference executable.

### Working oracle environment

```text
Apple Silicon Mac
    │
    ▼
Virtualized Windows 11 Pro ARM64 VM
    │
    ▼
Warcraft III 1.29.2 (9231)
x86 32-bit executable
    │
    ▼
JASS experiment → raw trace → normalized reference
```

The user has established that the game runs successfully in this environment. Continue directly with measurement and output extraction instead of reopening OS selection or requiring an x86/x64 Windows guest.

Record the VM product, Windows build, VM resources, relevant graphics configuration, executable identity, and file-transfer method alongside the capture procedure. Use the working settings as the baseline. The earlier QEMU TCG configuration, Windows 10/7 suggestions, 2-versus-4 emulated CPU benchmark, and proposed memory sizing are historical suggestions in Appendix A, not requirements for this ARM64 VM.

### Remaining validation

- [ ] Run a deterministic test map repeatedly inside the working VM.
- [ ] Prove reliable extraction and completion detection.
- [ ] Establish sampling precision, repeatability, graphics behavior where relevant, and practical capture throughput.
- [ ] If a trace raises doubts about the execution environment, compare the same scenario and **same x86 game build** on the Windows laptop.

The optional laptop comparison concerns VM-versus-native-Windows behavior only. There is no x64 WC3 executable to compare and no 50–100-test x86/x64 comparison milestone.

### Optional fallback and later targets

Keep the Windows laptop available if a specific capture or compatibility investigation needs it. Steam Deck Wine/Proton remains a later optional environment for the same x86 WC3 build and for testing the new Linux client. Earlier Windows 7/10 and ARM macOS Wine proposals remain in the historical transcript for completeness; they are not setup or benchmarking tasks in the active plan.

## 16. Three CI levels and agentic work

| Level | Trigger and workload | WC3 dependency |
|---|---|---|
| 1 — Fast | Every commit/PR: compilation, unit tests, parsers, deterministic simulations, committed compatibility fixtures; aim for a few minutes | None at runtime |
| 2 — Heavy | Nightly/manual: thousands of scenarios/maps when supported, rendering regressions, replays, parser fuzzing, long deterministic runs | Normally existing references |
| 3 — Oracle | New reference creation, validation, and incompatibility research | Executes WC3 1.29.2 (9231) x86 in the Windows 11 Pro ARM64 VM |

Useful future interfaces:

```bash
wc3test run --scenario movement/turn_rate_001.yaml --ticks 10000 --output actual.json
wc3test compare actual.json reference/wc3-1.29.2-9231-x86/movement/turn_rate_001.json
wc3oracle generate combat/armor.yaml
wc3oracle import wc3-output.txt
```

The `--ticks` option controls the C++ runner; it must not silently redefine oracle elapsed time.

A useful future agent assignment is: “Make movement/turn_rate_001 through turn_rate_027 pass without regressing the compatibility suite.” This is an implementation workflow proposed in the source conversation, not an instruction to start agents as part of writing this plan.

The earlier colocated layout—scenario.yaml, WC3 JSON, optional warsmash.json, and expected.json within a compatibility case—is an alternative to separate tests/ and reference/ trees. Pick one consistent organization; keep the raw WC3 authority clear if using a derived expected.json.

## 17. Repository and traceability

Keep the engine and oracle tooling in the same repository. Grow from the minimal Phase 2 layout toward:

```text
warcraft-re/
  engine/
    simulation/
    world/
    pathing/
    jass/
  renderer/
    raylib/
  formats/
  tools/
    wc3test/
  oracle/
    compiler/
    jass/
    runner/
    normalizer/
    comparator/
  oracle-maps/
  adapters/
    warsmash/              # optional, only if useful
  tests/
    movement/
    combat/
    orders/
    abilities/
    pathing/
    jass/
    rendering/
    rng/
  reference/
    wc3-1.29.2-9231-x86/
```

Use permanent families such as MOV, COM, ORD, JASS, PATH, and RNG. Connect non-obvious compatibility code to specific experiments, e.g. a comment citing MOV-0047 for a measured turn-rate/displacement ordering rule. The example rule in the conversation is illustrative until actually verified.

## 18. Optional later investigations

### Warsmash

Keep its source available to explain measured behavior or suggest a formula. For example, a trace increasing facing by approximately 1.406° every 0.010 seconds might prompt a targeted source investigation.

An optional adapter can eventually run the same scenario and emit warsmash.json beside wc3.json and ours.json. This can expose a Warsmash discrepancy—such as the illustrative armor outputs 100.000 versus 99.997—but does not make Warsmash a co-equal authority or required CI participant.

### Second, invasive oracle

Maintain two distinct purposes if black-box observation becomes insufficient:

- **Oracle A:** unmodified WC3 plus JASS, measuring externally observable behavior maps depend on.
- **Oracle B:** instrumented WC3 with debugger/hooks/memory inspection, investigating internal state that JASS cannot expose.

Introduce Oracle B only when a concrete unanswered question needs it. Use its findings to form hypotheses and validate observable behavior through Oracle A where possible.

## 19. First ten milestones

1. [x] A WC3 map executes its test automatically after loading and produces a recognizable result.
2. [x] WC3 trace extraction works reliably.
3. [ ] The C++ project builds on the ARM Mac and contains a tiny headless World.
4. [ ] C++ emits the same trace representation as WC3.
5. [ ] The comparator identifies the first divergence.
6. [ ] MOV-0001 passes: stationary unit.
7. [ ] MOV-0002 passes: straight-line movement.
8. [ ] CI runs the C++ compatibility suite against committed WC3 references.
9. [ ] The scenario format exists and C++ consumes it.
10. [ ] A scenario generates a runnable WC3 test map.

At milestone 10, the experimental loop is complete:

```text
test description → WC3 → observed behavior
       └────────→ C++ → observed behavior
                         ↓
                        diff
```

## 20. Immediate next actions and unresolved questions

Phase 0 is complete as of 30 September 2026; the following is the original bootstrap sequence. Current next work is recorded in [PROGRESS.md](PROGRESS.md).

1. Record the WC3 1.29.2 (9231) x86 executable identity and the working Windows 11 Pro ARM64 VM configuration.
2. Prepare the first oracle experiment in that already-tested VM.
3. Create one manually authored test map with automatic scripted actions.
4. Prove a reliable, minimally invasive output extraction path.
5. Repeat the experiment and inspect the output.
6. Build the smallest native C++ equivalent and compare it.

Resolve through experiments: actual output transport, sampling precision and cadence, repeatability, available JASS observations, VM/native-Windows agreement if a result needs investigation, RNG seed control and shared streams, and eventual algorithm compatibility.

The goal is to produce verified WC3-compatible behavior almost immediately, then let each new experiment justify the next increment of tooling.

## 21. Source coverage map

| Retrieved exchange, chronological | Plan coverage |
|---|---|
| 1. Raylib, ARM Macs, hardware, CI, controller | Phases 2/4/6/7; sections 14–17 |
| 2. Original architecture/guest-OS discussion and native control | Superseded architecture/OS proposals preserved in Appendix A; corrected environment in Decisions, Phase 0, and section 15 |
| 3. Oracle architecture, observations, schema, sweeps, optional adapters/instrumentation | Phases 1/3/5/6/8; sections 12/17/18 |
| 4. Demoting Warsmash and handling RNG | Decisions; section 13; section 18 |
| 5. Zero-to-tests bootstrap and ten milestones | Phases 0–8; sections 19/20 |

Appendix A preserves every retrieved message in full. Its older recommendations and illustrative outputs remain historical source material; the 29 September 2026 target correction and precedence table above govern this plan. In particular, x64 WC3, x86/x64 comparison, and Windows 10 x64/QEMU recommendations in the transcript are superseded.

---

# Appendix A — Complete retrieved conversation

> **Superseded platform assumptions:** The user corrected the target on 29 September 2026 to Warcraft III 1.29.2 (9231), x86 32-bit only, running successfully in a virtualized Windows 11 Pro ARM64 VM. Historical claims below about an x64 WC3 build, x86/x64 comparisons, or selecting Windows 10 x64/QEMU are retained solely as the original conversation record. They are not active plan requirements.


The following is the chronological source record. It is preserved verbatim at the message-text level, apart from adding role headings. Original chat citation markers and code-fence identifiers may appear; they are source artifacts, not independently checked citations. Requests and suggestions inside this appendix are historical conversation content, not additional tasks being executed.


## Exchange 1

### User

this is close to what i wanna build. i will first use raylib as the graphics engine, then eventually replace it if it holds me back. what do u think of this? and also, how would you structure the CI / hardware situation of the project? the warcraft version i want to port does only run on windows 32 bit or mac os 32bit... and i now basically only work on ARM macs, my macbook pro and a mac mini i use for remote agentic development.. i also have a steam deck and a windows laptop that i could connect up but it would kinda be a hassle.. what dou you think?

### Assistant

I think raylib is a very good choice for the first implementation, especially if you deliberately treat it as a **backend rather than your engine architecture**.

I'd make the boundary something like `wc3core → renderer interface → raylib backend`. Your simulation, Warcraft formats, MDX animation state, particles, terrain representation, etc. shouldn't know that raylib exists. Then if you eventually hit limitations—custom render passes, exact WC3 blending behavior, shaders, batching, platform-specific graphics—you can replace `RaylibRenderer` with Vulkan/Metal/D3D without rewriting the game.

For example, I'd be comfortable with interfaces along these lines:

```cpp
class Renderer {
public:
    virtual void beginFrame(const Camera& camera) = 0;
    virtual void drawTerrain(const TerrainRenderData&) = 0;
    virtual void drawModel(const ModelInstance&) = 0;
    virtual void drawParticles(const ParticleBatch&) = 0;
    virtual void drawUI(const UICommandList&) = 0;
    virtual void endFrame() = 0;
};
```

But **don't overabstract raylib on day one**. A thin boundary is enough. Prematurely inventing your future Vulkan API could cost more time than replacing some raylib-specific code later.

## Your hardware situation is actually pretty good

I'd make the ARM Mac Mini your primary development/CI-ish machine and separate testing into two fundamentally different categories:

```text
                   Git repository
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      ARM macOS      Linux x64       Windows x64
      build/test     build/test       build/test
          │
          └──────────────┬──────────────┘
                         │
                    wc3core tests
                         │
                         ▼
                  compatibility tests
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        reference traces      reference images
        captured earlier      captured earlier
        from WC3 1.29         from WC3 1.29
```

The critical realization is that **CI does not normally need to run Warcraft III**.

Your repository should contain reference outputs captured from WC3:

```text
compat/
  movement/
    turn_rate_001/
      scenario.yaml
      wc3-1.29.2.json
      warsmash.json
      expected.json

  combat/
    armor_001/
      scenario.yaml
      wc3-1.29.2.json

  rendering/
    footman_idle_001/
      reference.png
```

Normal CI runs *your* implementation and compares against those artifacts.

Therefore your ARM Macs can run 95%+ of your development loop without being capable of executing original WC3 at all.

### I'd have three CI levels

**Level 1 — every commit/PR:** compile and test `wc3core` on macOS ARM64, Linux x64 and Windows x64 using hosted CI. Run unit tests, parsers, deterministic simulation tests and previously captured WC3 compatibility traces. This should be fast—ideally a few minutes.

**Level 2 — heavier compatibility CI:** perhaps nightly or manually triggered. Run thousands of maps/scenarios, rendering regression tests, replay tests, fuzz tests for file parsers, long deterministic simulations, etc.

**Level 3 — oracle generation:** this is the unusual one. It actually runs **Warcraft III 1.29** and generates/validates reference results. I would *not* make this part of ordinary CI.

Think of it as:

```text
WC3 Oracle Machine
       │
       │ scenario.w3x
       ▼
 Warcraft III 1.29
       │
       ▼
 trace.csv / screenshots
       │
       ▼
 oracle-import
       │
       ▼
 compat/reference/1.29.2/...
```

You only need the oracle when creating a new test or investigating an incompatibility.

## For the WC3 oracle, I'd use a Windows x86 VM

This is where your ARM Macs become slightly annoying, but I don't think I'd permanently wire your Windows laptop into CI.

Instead, I'd try to establish one reproducible **Windows x86 VM containing WC3 1.29**.

On Apple Silicon, you need x86 emulation rather than normal ARM virtualization:

```text
M-series Mac
     │
     ▼
QEMU
     │ x86_64 emulation
     ▼
Windows x86/x64
     │
     ▼
Warcraft III 1.29 x86
```

It'll be much slower than native virtualization, but **performance isn't particularly important for an oracle**.

If a test takes 20 seconds rather than 2 seconds, who cares? You're using it to answer:

> What exactly does WC3 do here?

rather than to play the game.

I'd initially see how reliable WC3 1.29 is under QEMU on your Mac Mini. If graphics become problematic, then I'd move the oracle to the Windows laptop.

### Your Mac Mini is particularly useful here

Because it's already your remote agentic development machine, I'd essentially make it:

```text
Mac Mini ARM
│
├── native macOS ARM
│   ├── Claude/Codex/agents
│   ├── clang
│   ├── CMake
│   ├── wc3core
│   └── raylib client
│
├── Docker/Linux ARM tests
│
└── QEMU
    └── Windows x86
        └── WC3 1.29 oracle
```

Then your MacBook is just your interactive workstation.

That's a very pleasant setup if the QEMU part works reliably enough.

## Don't throw away the Windows laptop, though

I'd give it one very specific job: **native verification**.

There are going to be moments where you wonder:

> Is this weird result actual Warcraft behavior, or something caused by QEMU/Wine/etc.?

Then:

```text
WC3 1.29 VM result
       │
       ├── agrees → probably good
       │
       ▼
native Win32 WC3 1.29
```

Your Windows laptop becomes the final oracle for questionable results rather than a machine that has to be running 24/7.

You could eventually install a self-hosted CI runner on it, but I wouldn't bother initially.

## The Steam Deck could become surprisingly useful

I'd mostly ignore it at first.

Later, it's a very nice Linux x86_64 compatibility target:

```text
Steam Deck
Linux x86_64
     │
     ├── native wc3 client
     └── Wine/Proton
           └── WC3 1.29
```

Wine/Proton may actually make running old Win32 WC3 considerably easier than emulating an entire x86 Windows machine on ARM.

So your eventual physical test matrix could be:

| Machine | Purpose |
|---|---|
| M-series MacBook Pro | Primary development |
| M-series Mac Mini | agents + long tests + ARM CI |
| GitHub Actions | Linux x64 + Windows x64 + macOS ARM builds |
| Steam Deck | Linux x64 / Proton testing |
| Windows laptop | native WC3 1.29 oracle |

You definitely don't need all five involved initially.

## I'd also make deterministic simulation a first-class design requirement

This interacts strongly with CI.

I'd have a command like:

```bash
wc3test run \
    --scenario movement/turn_rate_001.yaml \
    --ticks 10000 \
    --output actual.json
```

and:

```bash
wc3test compare \
    actual.json \
    reference/wc3-1.29.2/movement/turn_rate_001.json
```

Your CI then has zero dependency on WC3:

```text
checkout
   ↓
build wc3core
   ↓
run scenario
   ↓
actual.json
   ↓
compare
   ↓
WC3 reference.json
   ↓
PASS / FAIL
```

This is also **perfect for agentic development**. You can give an agent an objective such as:

> Make `movement/turn_rate_001` through `turn_rate_027` pass without regressing the existing compatibility suite.

That's much safer than telling it "implement WC3 movement like Warsmash."

The tests provide a hard feedback loop.

## One additional thing I'd strongly consider: an oracle controller

Eventually I'd make your test tooling capable of generating WC3 test maps automatically.

For example:

```bash
wc3oracle generate combat/armor.yaml
```

produces:

```text
generated/
    combat_armor.w3x
```

You transfer/run it in WC3 and it writes something like:

```text
WC3TEST 1
TICK 0 UNIT hfoo0 HP 420
TICK 1 UNIT hfoo0 HP 420
...
EVENT DAMAGED ...
```

Then:

```bash
wc3oracle import wc3-output.txt
```

produces:

```text
reference/wc3-1.29.2/combat/armor.json
```

At that point the tedious reverse-engineering process becomes almost scientific:

```text
                    ┌─────────────┐
                    │ scenario    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           WC3 1.29     Warsmash       yours
              │            │            │
              ▼            ▼            ▼
           trace         trace         trace
              └────────────┼────────────┘
                           ▼
                     diff/report
```

And **that**, more than the graphics backend, is what I'd optimize the architecture around.

Raylib lets you get pixels on the screen quickly. C++ gives you control over the eventual engine. The ARM Macs can handle almost all everyday development. A slow x86 VM can handle routine oracle extraction, and your Windows laptop only needs to come out when you need unquestionable native WC3 behavior.

That's a much less annoying hardware arrangement than trying to make an old 32-bit game part of every CI run.


## Exchange 2

### User

actually, the version of warcraft 3 i have is both x64 and x86. which is faster to emulate? and what version of windows would you put on qemu?

### Assistant

That changes the recommendation quite a bit. If your Warcraft III 1.29 build has a native **x86-64 executable**, I'd start with **x64 Warcraft + 64-bit Windows**.

On an Apple Silicon Mac, both x86 and x86-64 guests require QEMU's TCG CPU emulation rather than native ARM virtualization; QEMU supports both x86 targets under TCG. :chatgpt-content-reference{index="0"} There isn't a general rule that a 32-bit x86 guest will be dramatically faster simply because it's 32-bit. For this workload, the bigger performance issue is **ARM → x86 instruction translation**, plus graphics emulation.

### What I'd install

My first attempt would be:

**Windows 10 x64 21H2/22H2 + WC3 1.29 x64.**

Not Windows 11. You gain essentially nothing for an old game/oracle machine, while Windows 10 is lighter and has fewer requirements to deal with.

I'd configure roughly:

```text
Mac Mini (Apple Silicon)
        │
        ▼
QEMU
  x86_64 machine
  TCG acceleration
  4 emulated cores
  4–8 GB RAM
        │
        ▼
Windows 10 x64
        │
        ▼
Warcraft III 1.29 x64
```

I'd actually benchmark **2 versus 4 virtual CPUs**. With TCG, throwing lots of virtual cores at the guest doesn't necessarily make your particular workload faster.

### But there's an interesting alternative

For a dedicated WC3 oracle, I'd also test **Windows 7 SP1 x64**.

That's potentially a very nice environment for what you're doing:

```text
Windows 7 x64
    +
WC3 1.29 x64
```

It's considerably more period-appropriate, much less resource-hungry, and you're not using this VM as a general-purpose internet-connected computer anyway.

The downside is tooling. Modern guest tools, automation software and other dependencies are generally easier on Windows 10.

So I'd choose:

| Guest | My use |
|---|---|
| **Windows 10 x64** | Default; easiest automation |
| **Windows 7 x64** | Worth benchmarking as a minimal dedicated oracle |
| Windows 10 x86 | Little reason |
| Windows 7 x86 | Only if you discover WC3 x86 behaves differently |
| Windows 11 x64 | Unnecessary |

### More importantly: test x86 and x64 WC3 against each other

Since you're trying to reproduce **behavior**, this is actually useful information.

Before choosing one as canonical, I'd run perhaps 50–100 of your eventual behavioral tests against:

```text
WC3 1.29 x86
vs
WC3 1.29 x64
```

Things like RNG, floating-point calculations, pathing, timers, animation timings, JASS behavior and order processing.

You may discover they're behaviorally identical for everything you care about. Great—declare:

```text
REFERENCE_IMPLEMENTATION =
    Warcraft III 1.29.2 x64 Windows
```

But if you discover something like:

```text
movement/pathing_037

1.29 x86: x = 1834.218750
1.29 x64: x = 1834.218628
```

then you have a decision to make about which executable is actually your compatibility target.

That's particularly relevant because **floating-point behavior can differ between 32-bit x86 and x86-64 builds**, depending on how Blizzard compiled each binary. I wouldn't assume they produce bit-identical simulation results without testing.

### One other possibility I'd benchmark before committing to full Windows/QEMU

Since your objective isn't actually to use Windows—it's to **execute an x86 Warcraft binary on ARM macOS**—I'd experiment with Wine-based approaches too.

Conceptually:

```text
              Apple Silicon
                    │
          ┌─────────┴──────────┐
          │                    │
     Full QEMU x86        translation/Wine
          │                    │
     Windows x64          Win32/Win64 APIs
          │                    │
       WC3 x64              WC3 x64
```

Full-system QEMU has to emulate an entire x86 computer. A compatibility/translation approach can potentially avoid quite a lot of that overhead.

For **oracle correctness**, though, I'd still maintain your native Windows laptop as the control:

```text
             canonical test
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
Mac ARM emulated         Windows x64
WC3 1.29 x64             WC3 1.29 x64
        │                    │
        └─────────┬──────────┘
                  ▼
             compare traces
```

If those consistently agree, you can confidently let the Mac Mini generate thousands of oracle traces unattended and almost never touch the Windows laptop.

So my first experiment would actually be very small: **Windows 10 x64/QEMU + WC3 x64**, run one deterministic test map repeatedly, and establish whether it runs reliably and fast enough. If it's painfully slow, *then* investigate lighter Windows/Wine options rather than prematurely designing the infrastructure around QEMU.


## Exchange 3

### User

ok ill do windows 10 64 bit. but now to the test: how would you design the oracle? what should it consist of?

### Assistant

I'd make the oracle a **small, deliberately boring measurement framework that runs inside real WC3**, rather than something that knows about your C++ implementation. Its only job is:

> Set up a precisely defined experiment → stimulate Warcraft → observe everything Warcraft lets us observe → emit a deterministic trace.

The architecture I'd aim for is:

```text
test definition
      │
      ▼
oracle compiler
      │
      ├──────────────► scenario.w3x
      │
      └──────────────► scenario.json
                             │
                             │ same logical test
                             ▼
                      your C++ engine
      │
      ▼
WC3 1.29
      │
      ▼
oracle trace
      │
      └──────────────┐
                     ▼
                 comparator
                     │
                PASS / FAIL
```

## 1. The test definition should be engine-independent

Don't write tests directly as JASS.

Have your own declarative format:

```yaml
name: "footman_basic_attack"
version: 1

world:
  map: empty_64x64
  terrain: grass

units:
  - name: attacker
    type: hfoo
    owner: 0
    position: [0, 0]
    facing: 0

  - name: target
    type: hfoo
    owner: 1
    position: [300, 0]
    facing: 180

actions:
  - time: 1.0
    action: attack
    unit: attacker
    target: target

observe:
  interval: 0.01

  units:
    attacker:
      - x
      - y
      - facing
      - order
      - life

    target:
      - x
      - y
      - life

  events:
    - attacked
    - damaged
    - death

duration: 5.0
```

This becomes your **canonical description of an experiment**.

Crucially, neither WC3 nor Warsmash nor your engine owns this format.

## 2. Then build an `oracle-compiler`

Something like:

```bash
wc3oracle compile tests/combat/footman_basic_attack.yaml
```

generates a test map:

```text
build/oracle/
    footman_basic_attack.w3x
```

Internally it contains generated JASS roughly equivalent to:

```jass
function InitTest takes nothing returns nothing
    set attacker = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    set target   = CreateUnit(Player(1), 'hfoo', 300, 0, 180)

    call OracleRegisterUnit(attacker, "attacker")
    call OracleRegisterUnit(target, "target")

    call OracleScheduleAttack(1.0, attacker, target)
    call OracleFinishAt(5.0)
endfunction
```

But you almost never manually write that JASS.

## 3. Put a reusable `Oracle.j` library inside every map

This is the actual WC3-side instrumentation.

I'd keep it tiny:

```text
oracle/
    jass/
        Oracle.j
        OracleUnits.j
        OracleEvents.j
        OracleOrders.j
        OracleTiming.j
```

It provides functions such as:

```jass
call OracleLogReal("unit.attacker.x", GetUnitX(attacker))
call OracleLogReal("unit.attacker.y", GetUnitY(attacker))
call OracleLogInt("unit.attacker.order", GetUnitCurrentOrder(attacker))
```

and emits machine-readable records.

Don't optimize for human readability. Optimize for **unambiguous parsing**.

For example:

```text
@O|00000100|UNIT|attacker|X|0.000000
@O|00000100|UNIT|attacker|Y|0.000000
@O|00000100|UNIT|attacker|ORDER|851983

@O|00001000|ACTION|ATTACK|attacker|target

@O|00001031|EVENT|ATTACKED|attacker|target
@O|00001467|UNIT|target|LIFE|407.000000
```

`@O` makes oracle output easy to distinguish from random WC3 output.

---

# 4. Time is one of the hardest parts

I would **not** initially define your oracle around "simulation ticks", because you don't yet know that your C++ notion of a tick corresponds exactly to WC3 internals.

Use oracle elapsed time:

```text
0
0.010
0.020
...
```

or integer micro/milliseconds in the trace.

Then separately investigate Warcraft's internal update cadence.

Eventually you may discover something like:

```text
WC3 simulation quantum = X
```

and design your engine around it.

But the oracle shouldn't assume the answer before you've measured it.

## 5. I'd have four kinds of observations

### State observations

Things JASS exposes directly:

```text
position
facing
HP
mana
current order
owner
level
XP
hero stats
movement speed
fly height
ability levels
resources
food
unit type
```

For example:

```text
1000 STATE attacker X 0
1000 STATE attacker Y 0
1000 STATE attacker ORDER 851983

1010 STATE attacker X 2.3125
1010 STATE attacker Y 0
...
```

These are excellent for continuous behavior.

### Event observations

Potentially even more important:

```text
unit attacked
unit damaged
unit dies
spell channel
spell cast
spell effect
spell finish
spell endcast
order issued
point order
target order
unit enters region
unit leaves region
item events
hero events
```

Record the **exact event ordering**.

You may discover:

```text
1370 EVENT attacked
1460 EVENT damaged
1460 STATE target.life 407
1460 EVENT life_changed
```

Your implementation should eventually reproduce that ordering.

### Query observations

These are tests where you're really testing an API result.

For example:

```yaml
queries:
  - time: 1.0
    expression: distance(attacker,target)

  - time: 1.0
    expression: current_order(attacker)
```

Particularly useful when you get to JASS compatibility.

### Visual observations

Keep these separate.

For example:

```yaml
visual:
  camera:
    position: [...]
    target: [...]

  screenshots:
    - time: 1.0
    - time: 2.0
```

WC3 screenshot:

```text
reference.png
```

Your engine:

```text
actual.png
```

Then image comparison.

Don't mix rendering tests with simulation tests unless necessary.

---

# 6. Events should have sequence numbers

This is something I'd definitely do.

Instead of relying purely on timestamps:

```json
{
  "seq": 381,
  "time": 1.466,
  "type": "EVENT",
  "event": "UNIT_DAMAGED",
  "source": "attacker",
  "target": "target"
}
```

Then:

```json
{
  "seq": 382,
  "time": 1.466,
  "type": "STATE",
  "entity": "target",
  "property": "life",
  "value": 407
}
```

Even if Warcraft exposes identical timer values for two things, you know their ordering.

That will become extremely useful for JASS.

---

# 7. The output should be normalized

Raw WC3 output shouldn't become your permanent reference.

I'd have:

```text
WC3
 │
 ▼
raw trace
 │
 ▼
normalizer
 │
 ▼
canonical oracle JSON
```

For example WC3 might produce:

```text
@O|1466|STATE|target|LIFE|406.999969482
```

Your normalizer might preserve:

```json
{
  "time": 1466,
  "kind": "unit_state",
  "unit": "target",
  "property": "life",
  "value": 406.999969482
}
```

Don't prematurely round it.

**Keep the raw values.**

Your comparator decides tolerances.

## 8. The comparator should understand tolerances

You absolutely don't want:

```cpp
wc3.x == ours.x
```

everywhere.

Instead:

```yaml
tolerance:
  position: 0.001
  facing: 0.001
  life: 0.0001
  time: 0.002

strict:
  order: true
  event_sequence: true
  unit_type: true
```

Then a failure report could say:

```text
FAIL movement/basic_004

First divergence:
  t = 2.437 s

                 WC3             OURS          Δ
x                183.21875       183.22491     +0.00616
y                 94.03125        94.03131     +0.00006
facing            31.640625       31.640625     0
order          851986          851986           ✓

Tolerance:
position = 0.001

First divergence: X
```

And ideally it continues enough to show whether the error explodes:

```text
2.437   +0.006
2.447   +0.013
2.457   +0.021
2.467   +0.031
...
```

That is debugging gold.

---

# 9. Run each WC3 experiment several times

This is extremely important.

When generating a new reference:

```bash
wc3oracle capture movement/basic_004 --runs 20
```

Compare the twenty traces.

If you get:

```text
run 1   identical
run 2   identical
...
run 20  identical
```

great.

But if:

```text
damage:
run 1  17
run 2  19
run 3  17
run 4  22
```

you've just discovered RNG.

Or perhaps timing nondeterminism.

Your oracle tooling should therefore distinguish:

```text
DETERMINISTIC
RNG-DETERMINISTIC-WITH-SEED
NONDETERMINISTIC
UNKNOWN
```

This will tell you a lot about WC3 itself.

## 10. I'd make tests microscopic

Avoid:

> Run a melee game for ten minutes and compare it.

Instead:

```text
movement/
    acceleration
    deceleration
    turn_rate
    collision
    target_reached
    interruption

combat/
    damage
    armor
    attack_point
    backswing
    cooldown
    projectile
    acquisition
```

And then:

```text
turn_rate_001
turn_rate_002
turn_rate_003
...
```

One test answers **one question**.

For example:

> How does a unit with movement speed 270 and turn rate 0.5 rotate toward a destination exactly 90° from its current facing?

That's a good oracle experiment.

---

# 11. Also build parameter sweeps

This is where the system becomes really powerful.

Instead of manually investigating turn rate:

```yaml
matrix:
  movement_speed:
    [100, 200, 270, 400, 522]

  turn_rate:
    [0.1, 0.25, 0.5, 1.0]

  angle:
    [10, 45, 90, 135, 180]
```

Your generator produces **100 experiments**.

Run them against WC3.

Now you have data from which you can infer the actual algorithm.

This is much closer to experimental science than normal game development.

---

# 12. Warsmash gets exactly the same scenarios

Eventually I'd write a Warsmash adapter:

```text
scenario.yaml
     │
     ├──────────► wc3oracle
     │              ↓
     │           WC3 1.29
     │              ↓
     │           wc3.json
     │
     ├──────────► warsmash-test
     │              ↓
     │         warsmash.json
     │
     └──────────► wc3cpp-test
                    ↓
                 ours.json
```

Then:

```text
movement/turn_rate_027

WC3       Warsmash      Ours
 ✓            ✓          ✓

combat/armor_041

WC3       Warsmash      Ours
100.000    99.997       100.000
             ↑
        Warsmash differs
```

This prevents you from unconsciously treating Warsmash as authoritative.

---

# 13. There is one additional oracle I'd eventually want

JASS can only observe things Blizzard exposed to JASS.

Eventually you're going to encounter:

> I need to know internal state X, but JASS can't see it.

That's when I'd introduce a **second, invasive oracle**:

```text
Oracle A
Black-box WC3
JASS only
No modification
        │
        ▼
canonical behavior


Oracle B
Instrumented WC3 process
debugger/hooks/memory inspection
        │
        ▼
internal investigation
```

I would **not start there**.

Start black-box. It gives you much cleaner evidence because you're measuring Warcraft through the same externally observable interface that maps depend on.

Use process instrumentation later when you encounter behavior you simply cannot explain.

---

# 14. I'd put the whole thing in the same repository

Something approximately like:

```text
warcraft-re/
│
├── engine/
│   ├── simulation/
│   ├── world/
│   ├── pathing/
│   ├── jass/
│   └── ...
│
├── renderer/
│   └── raylib/
│
├── formats/
│
├── oracle/
│   ├── compiler/
│   ├── jass/
│   ├── runner/
│   ├── normalizer/
│   └── comparator/
│
├── adapters/
│   └── warsmash/
│
├── tests/
│   ├── movement/
│   ├── combat/
│   ├── orders/
│   ├── abilities/
│   ├── pathing/
│   ├── jass/
│   └── rendering/
│
└── reference/
    └── wc3-1.29/
```

And I'd give every experiment a permanent ID:

```text
MOV-0001
MOV-0002
COM-0001
ORD-0001
JASS-0001
PATH-0001
```

Then your C++ source can literally say:

```cpp
// WC3 compatibility:
// See MOV-0047. Warcraft applies turn-rate limiting
// before displacement calculation.
```

That creates a traceable connection between **weird compatibility code and the experiment proving why it exists**.

The part I'd design first is therefore not the JASS logging itself but the **scenario schema**. If that abstraction is good, you can feed the same experiment into WC3, Warsmash and your C++ engine for years without rewriting the test suite.


## Exchange 4

### User

ok. sice this would be so comprehensive, i almost feel like i could drop warsmash, could just get in the way. what do u think?
besides, how exactly can i handle rng in these oracle runs? there is stuff like critical hits and stuff that is just random

### Assistant

Yes—I would demote Warsmash substantially. Once your oracle becomes comprehensive, **WC3 itself is the specification**, while Warsmash becomes a source you consult when useful rather than something you're trying to port.

That gives you a cleaner project:

```text
                 Warcraft III 1.29
                    ground truth
                         │
                         ▼
                behavioral oracle
                         │
                         ▼
              compatibility spec/tests
                         │
                         ▼
                 your C++ engine
```

### Where I'd still keep Warsmash

I wouldn't delete it from your toolbox. It can save enormous amounts of reverse-engineering time when you observe behavior but can't infer the algorithm.

For example, suppose your oracle establishes:

```text
turn rate = 0.5

t=0.000   0.000°
t=0.010   1.406°
t=0.020   2.812°
t=0.030   4.219°
...
```

You now know *what* WC3 does but perhaps not *why*. Looking at Warsmash may immediately reveal the intended formula.

So I'd establish this priority:

```text
1. WC3 experimental evidence       authoritative
2. Your inferred behavioral model
3. Warsmash                        research/reference
4. Other open-source WC3 projects  research/reference
```

Importantly, don't automatically make Warsmash part of the test matrix. That turns every discrepancy into a three-way investigation when the only comparison that actually determines correctness is:

```text
WC3 vs yours
```

Use Warsmash when you're stuck.

---

# RNG is where the oracle gets interesting

You shouldn't generally try to compare:

```text
WC3 critical hit = 300
ours critical hit = 100

FAIL
```

because that tells you nothing if both engines correctly implement a 15% critical chance.

I'd divide tests into **deterministic tests and stochastic tests**.

For deterministic tests, exact/tolerance comparison works normally.

For RNG-dependent behavior, you have several approaches.

## 1. Remove RNG when testing everything except RNG

This is the most important principle.

Suppose you're testing critical-strike damage multiplication. Don't test a 15% critical strike and wait for it to happen.

Construct the scenario so the probability is effectively guaranteed if the game permits it:

```text
Critical Strike:
chance = 100%
multiplier = 3.0
```

Now you're testing:

> What happens when Critical Strike triggers?

rather than:

> Does Critical Strike happen randomly?

Similarly, separate:

```text
CRIT-001   critical damage calculation
CRIT-002   critical event ordering
CRIT-003   critical floating text
CRIT-004   interaction with armor
CRIT-005   interaction with evasion
CRIT-006   probability distribution
```

Only `CRIT-006` actually needs randomness.

This principle will eliminate RNG from the overwhelming majority of tests.

---

# 2. Test random behavior statistically

For the tests where randomness **is the behavior you're investigating**, run huge samples.

Suppose Critical Strike claims to have a 15% probability.

Create a scenario with perhaps:

```text
100,000 attacks
```

and record:

```text
normal = 84,927
critical = 15,073

observed probability = 0.15073
```

Then your test doesn't say:

```text
expected exact sequence:
normal
normal
critical
normal
...
```

It says:

```yaml
expected:
  event: critical
  probability: 0.15

statistical_test:
  samples: 100000
  tolerance: ...
```

You can use a binomial test/confidence interval rather than an arbitrary percentage tolerance.

Your oracle may tell you:

```text
WC3
N = 1,000,000
critical = 149,872
p ≈ 0.149872
```

Now you've established strong evidence for ~15%.

---

# 3. But don't assume Warcraft RNG is independent

This is where things get much more interesting.

Warcraft may have mechanics using things such as **pseudo-random distribution (PRD)** rather than independent Bernoulli trials.

Conceptually:

```text
Independent 15%:

P(crit on each attack) = 0.15
```

versus something like:

```text
PRD:

miss → probability increases
miss → probability increases
miss → probability increases
crit → probability resets
```

Both can average ~15%, but they behave very differently.

Therefore don't only measure:

```text
number of crits / attacks
```

Record the **entire sequence**:

```text
000001 N
000002 N
000003 C
000004 N
000005 N
000006 N
000007 N
000008 C
...
```

Then analyze things like:

```text
overall frequency
distribution of gaps between procs
P(proc | 0 failures)
P(proc | 1 failure)
P(proc | 2 failures)
...
```

For example you might infer:

```text
failures since proc    observed P(next proc)

0                      0.032
1                      0.064
2                      0.096
3                      0.128
4                      0.160
...
```

That's dramatically more informative than simply finding "15%".

---

# 4. RNG should have its own research suite

I'd create:

```text
tests/
    rng/
        random_integer/
        random_real/
        damage_variance/
        critical_strike/
        evasion/
        bash/
        item_drop/
        attack_damage/
        proc_distribution/
```

And have an `rng-analyze` tool.

For example:

```bash
wc3oracle capture RNG-CRIT-001 --runs 1000000
wc3oracle analyze RNG-CRIT-001
```

producing something like:

```text
Critical Strike Analysis

Samples:              1,000,000
Triggers:               149,983
Observed probability:  14.9983%

Expected nominal:      15.0000%

Gap distribution:
0:   3.2%
1:   6.1%
2:   8.7%
3:  11.0%
...

Independent RNG hypothesis: rejected
PRD hypothesis:             plausible
```

This is exactly the kind of tooling that could uncover undocumented Warcraft mechanics.

---

# 5. Investigate whether you can control WC3's RNG seed

This is something I'd investigate experimentally fairly early.

Create a test map that immediately emits a sequence of:

```jass
GetRandomInt(0, 2147483647)
```

Start WC3/map repeatedly:

```text
Run #1:
193822
483929
...

Run #2:
193822
483929
...
```

If they're identical, excellent—you've found reproducibility somewhere.

If they're different, investigate what affects initialization:

```text
game startup?
map startup?
system time?
player slot?
map checksum?
game mode?
```

Also test whether JASS RNG and gameplay RNG appear to share state.

For example:

```text
experiment A:
attack attack attack attack

experiment B:
GetRandomInt()
attack attack attack attack
```

If the attack outcomes shift, that's evidence that they consume the same RNG stream/state.

That's a **very important compatibility question**.

---

# 6. You may eventually want to reproduce the RNG algorithm itself

Once you've collected sequences like:

```text
r0
r1
r2
r3
...
```

you can try to identify the generator.

Maybe WC3 uses a familiar PRNG; maybe Blizzard wrapped something else; maybe there are several RNG sources.

If you eventually determine:

```text
seed → algorithm → exact WC3 random stream
```

then something wonderful happens.

Your formerly stochastic tests become deterministic:

```text
WC3 seed 0x12345678

attack 1 → normal
attack 2 → normal
attack 3 → critical
attack 4 → normal
...
```

and your C++ implementation can reproduce it exactly.

That's especially important if you eventually want **replay/network determinism**, because deterministic RTS simulation generally requires machines to agree on random outcomes.

---

# 7. I'd distinguish three levels of RNG compatibility

Your project could explicitly track:

```text
Level 1 — Distribution compatibility

15% WC3 proc
≈
15% ours
```

Enough to make gameplay behave correctly statistically.

Then:

```text
Level 2 — Algorithm compatibility

same PRD/RNG mechanics
same probabilities
same correlations
same reset rules
```

Much better.

Finally:

```text
Level 3 — Bit/sequence compatibility

same seed
     ↓
same RNG stream
     ↓
same random decisions
```

That's the ultimate target.

You don't need Level 3 to start implementing Critical Strike. But I'd architect things so Level 3 remains possible.

For example, **never scatter C++ randomness throughout the engine**:

```cpp
// BAD

if (rand() % 100 < chance)
    critical();
```

Instead have something like:

```cpp
class RandomSource {
public:
    virtual uint32_t nextInt() = 0;
    virtual float nextReal() = 0;
};
```

and simulation code goes through a central Warcraft RNG abstraction:

```cpp
if (world.random().roll(chance)) {
    critical();
}
```

Later you can replace:

```text
TemporaryRng
```

with:

```text
Warcraft129Rng
```

without rewriting the engine.

Even better, if you discover multiple RNG streams:

```cpp
world.random(RandomDomain::Combat);
world.random(RandomDomain::Jass);
world.random(RandomDomain::Loot);
```

you have room for that architecture.

---

The oracle therefore isn't merely a regression test suite. Over time it becomes a **scientific characterization of the WC3 1.29 engine**.

And that's precisely why I agree with your instinct about Warsmash: once you've built this infrastructure, making Warsmash a co-equal reference would actually muddy the project. I'd keep its source available as a very useful answer to *"someone else already investigated this—what did they conclude?"*, but make every compatibility decision ultimately answer to your WC3 1.29 oracle.


## Exchange 5

### User

cool. and how do you imagine i could go from 0 to runnable test suits. there will be a lot to do up to that point i think

### Assistant

There is a bootstrap problem: the beautiful `scenario.yaml → WC3 + your engine → compare` system assumes you already have map generation, JASS execution, a simulation, logging, etc. I would **not build all of that first**.

I'd deliberately bootstrap it in layers, with the first useful oracle arriving very early.

### Phase 0: prove you can measure WC3 manually

Before writing any C++, make one tiny WC3 test map by hand.

Two Footmen, a timer, and JASS that prints/logs something like:

```text id="rwhhwc"
TEST_BEGIN MOV-0001
T=0 X=0 Y=0 FACING=0
T=32 X=5.25 Y=0 FACING=0
T=64 X=10.50 Y=0 FACING=0
...
TEST_END
```

Issue a move order programmatically.

Your first objective is simply:

> Can I make WC3 execute a completely unattended experiment and recover machine-readable results?

Solve **output extraction** here. That's actually one of the first practical questions I'd investigate: file output available through the game's scripting environment, log/debug output, or another minimally invasive capture mechanism.

Once you can reliably get:

```text id="kwwt0s"
WC3 → text file
```

you have an oracle.

### Phase 1: forget YAML and map generation

Create maybe 10–20 manually authored oracle maps.

Something like:

```text id="o4cf4k"
oracle-maps/
  MOV-0001.w3x
  MOV-0002.w3x
  ORD-0001.w3x
  COM-0001.w3x
```

Put the reusable instrumentation in a small JASS library:

```jass id="ih77mp"
OracleBegin("MOV-0001")

OracleWatchUnit("footman", u)

OracleSample()

OracleLogEvent(...)

OracleEnd()
```

At this stage, the development loop can be ugly:

```text id="sjjlmb"
edit JASS
   ↓
open map
   ↓
WC3 runs
   ↓
retrieve output
   ↓
Python/C++ script parses output
   ↓
look at CSV
```

That's fine.

You are proving what measurements are actually possible before designing an elaborate schema around assumptions.

### Phase 2: build the C++ project beside it

Now bootstrap the engine, but **don't attempt to load WC3 maps yet**.

I'd start with something like:

```text id="cyq5dc"
src/
  core/
    World.cpp
    Unit.cpp
    Orders.cpp
    Random.cpp

  renderer/
    raylib/

tools/
  wc3test/

oracle/
  jass/

tests/
```

And hard-code the equivalent of `MOV-0001`:

```cpp id="rt3p7v"
World world;

auto footman = world.createUnit(UnitType::Footman, {0, 0});

footman.issueMove({1000, 0});

for (int i = 0; i < 500; ++i) {
    world.step();
    trace.capture(world);
}
```

Now, for the first time:

```text id="hwn3ba"
WC3 MOV-0001
      ↓
 wc3.trace

C++ MOV-0001
      ↓
 ours.trace

      ↓
    diff
```

**This is your first real milestone.**

It could happen surprisingly early because you don't need:

- W3X parsing
- MDX
- BLP
- terrain rendering
- JASS interpreter
- abilities
- UI
- networking
- YAML
- automatic map generation

You need a `Unit`, coordinates, a movement experiment and a trace format.

I'd make this the project's first meaningful release:

```text id="mm9j2h"
v0.0.1

One Footman can move.
Its movement can be compared numerically
against Warcraft III 1.29.
```

That's a fantastic foundation.

---

## Phase 3: stabilize the trace format

Now you've learned what you actually need.

Define something like:

```json id="4i2yd6"
{
  "test": "MOV-0001",
  "engine": "wc3-1.29.2-x64",
  "samples": [
    {
      "t": 0,
      "units": {
        "u0": {
          "x": 0,
          "y": 0,
          "facing": 0,
          "order": 851986
        }
      }
    }
  ],
  "events": []
}
```

Your C++ engine emits exactly the same representation.

Then write:

```bash id="j0j1l9"
wc3test compare \
  reference/wc3-1.29/MOV-0001.json \
  build/tests/MOV-0001.json
```

And get:

```text id="l2gmz1"
MOV-0001

Samples: 313

X       PASS
Y       PASS
Facing  FAIL
Order   PASS

First divergence:
sample 17
WC3:   14.0625°
ours:  14.0000°
```

At this point **CI can already exist**.

---

## Phase 4: put these primitive tests in CI

Now your GitHub CI does:

```text id="4u0gbr"
cmake
  ↓
compile
  ↓
unit tests
  ↓
wc3test run MOV-0001
wc3test run MOV-0002
wc3test run ORD-0001
...
  ↓
compare against committed WC3 traces
```

Notice:

**WC3 still doesn't run in CI.**

The committed traces are fixtures:

```text id="b6up37"
reference/
  wc3-1.29.2-x64/
    MOV-0001.json
    MOV-0002.json
    ORD-0001.json
```

So already, perhaps a couple weeks into the project, you could have:

```text id="pzmkyc"
12/17 WC3 compatibility tests passing
```

That's where I think the project starts becoming fun.

---

# Phase 5: only now invent the scenario format

By now you've manually implemented perhaps 20–50 tests and you'll know what you're repeating.

You'll notice every test does:

```text id="sc58q9"
create unit
set properties
create second unit
wait
issue order
observe
```

**Now** introduce:

```yaml id="qfqdsq"
id: MOV-0017

units:
  u0:
    type: hfoo
    position: [0, 0]
    facing: 90
    movement_speed: 270

actions:
  - at: 1.0
    unit: u0
    order: move
    point: [1000, 0]

observe:
  units:
    u0: [x, y, facing, order]

duration: 5
```

Because you're extracting the abstraction from real tests instead of imagining it beforehand.

Then make your C++ runner consume it first:

```text id="0f8kyy"
scenario.yaml
      ↓
wc3test
      ↓
C++ World
```

That's relatively easy.

---

# Phase 6: generate WC3 tests from the same scenarios

Only then build:

```text id="9pdnkk"
scenario.yaml
      ↓
oracle-generator
      ↓
generated JASS
```

Perhaps you initially maintain a template map:

```text id="m7w5dq"
oracle-template.w3x

contains:
  flat terrain
  no doodads
  fixed players
  Oracle.j
  test bootstrap
```

Your generator copies it and injects:

```jass id="q9i2fu"
function OracleTest takes nothing returns nothing

    set u0 = CreateUnit(
        Player(0),
        'hfoo',
        0,
        0,
        90
    )

    call SetUnitMoveSpeed(u0, 270)

    // ...

endfunction
```

Now you've finally reached:

```text id="n1zwzj"
               MOV-0017.yaml
                /         \
               /           \
              ▼             ▼
      generate WC3       C++ runner
           map               │
            │                │
            ▼                ▼
         WC3.exe          wc3cpp
            │                │
            ▼                ▼
        wc3.json          ours.json
               \           /
                \         /
                 ▼       ▼
                   diff
```

This is probably your **v0.1 oracle infrastructure**.

---

# Phase 7: automate QEMU last

I'd actually keep the Windows VM manual for quite a while.

Initially:

```bash id="frh1vs"
./wc3oracle build MOV-0017
```

Then you manually run the map inside the VM and copy the result back.

That's mildly annoying, but if you're creating five tests per day it's completely acceptable.

Once it becomes annoying enough, automate it.

Then something like:

```bash id="m5g58w"
./wc3oracle capture MOV-0017
```

could eventually:

```text id="utlnfa"
generate map
    ↓
copy into shared VM directory
    ↓
launch WC3
    ↓
load map
    ↓
run experiment
    ↓
WC3 exits/returns
    ↓
retrieve trace
    ↓
normalize
    ↓
reference/MOV-0017.json
```

Now you have your full oracle pipeline.

But you've delayed the complicated VM automation until the project is already producing value.

---

# Phase 8: then expand horizontally

Now your work becomes almost factory-like.

Say you start implementing movement.

You might create:

```text id="cxgb82"
MOV-0001 stationary
MOV-0002 straight movement
MOV-0003 diagonal movement
MOV-0004 movement speed 100
MOV-0005 movement speed 522
MOV-0006 90° turn
MOV-0007 180° turn
MOV-0008 interrupted movement
MOV-0009 target behind unit
MOV-0010 stop order
...
```

Then discover something strange at 180°.

Generate:

```text id="0vzhgi"
MOV-0030 angle 170
MOV-0031 angle 172
MOV-0032 angle 174
...
MOV-0040 angle 190
```

Run:

```bash id="qlx7qf"
wc3oracle capture MOV-0030..MOV-0040
```

Plot the results.

Infer algorithm.

Implement.

CI:

```text id="k2ks43"
Movement compatibility
43 / 43 PASS
```

Then move to collision.

---

# I would deliberately postpone a lot

This is where I think you can keep the project from becoming overwhelming.

For the first several months, you don't necessarily need a JASS interpreter at all.

You also don't need your engine to load arbitrary `.w3x` files.

Your test runner can construct worlds directly:

```cpp id="7q0z5v"
TestWorldBuilder()
    .unit("u0", "hfoo", {0,0})
    .unit("u1", "hfoo", {500,0})
    .run();
```

Then later:

```text id="c0njhn"
W3X
 ↓
map loader
 ↓
same World API
```

Likewise rendering:

```text id="7czhr0"
             World
               │
       ┌───────┴────────┐
       ▼                ▼
 HeadlessTest       RaylibRenderer
```

Most compatibility development can run without a window at all.

---

# What I'd make the first ~10 milestones

I wouldn't plan by "implement Warcraft." I'd plan by increasingly powerful experimental capability:

1. **WC3 test map executes automatically after loading** and produces a recognizable result.
2. **WC3 trace extraction works reliably.**
3. **C++ project builds on your ARM Mac** and a tiny headless `World` exists.
4. **C++ produces the same trace format as WC3.**
5. **Comparator works** and can show the first divergence.
6. **MOV-0001 passes:** stationary unit.
7. **MOV-0002 passes:** straight-line movement.
8. **CI runs the C++ compatibility suite** against committed WC3 references.
9. **Scenario format exists** and C++ consumes it.
10. **Scenario → generated WC3 map works.**

At milestone 10 you have the machine we've been discussing:

```text id="d4enqt"
       test description
              │
       ┌──────┴──────┐
       ▼             ▼
   WC3 1.29         C++
       │             │
       ▼             ▼
   observed        observed
   behavior        behavior
       │             │
       └──────┬──────┘
              ▼
             diff
```

And I think there's an important psychological advantage to this bootstrap: **you should be comparing your C++ code against real WC3 almost immediately**, even if the first comparison is hilariously primitive.

Don't spend three months building "oracle infrastructure" before implementing the game. Build the smallest possible oracle, implement one tiny piece of Warcraft, compare them, and then let the infrastructure and engine grow together. That way the project starts producing verified WC3-compatible behavior from almost the beginning.


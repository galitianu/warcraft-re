# Phase 2: headless Footman world compared with WC3

Completed 30 September 2026 for [issue #3](https://github.com/galitianu/warcraft-re/issues/3).
**The Phase 2 gate is met:** a clean native ARM Mac build runs all ten experiments
headlessly, produces deterministic traces and compares them numerically with
committed WC3 observations. **Gameplay agreement is limited:** MOV-0001 passes;
MOV-0002–MOV-0010 fail the fixed provisional tolerances. The numerical comparison
of MOV-0001/0002 is the basis of v0.0.1; no release tag was created.

## Artifacts and identity

- Source/build commit: `c14c263685eeb843a8a1c8d10ef3eac760a726ea` (clean checkout).
  Build/runner source digest:
  `20a9be4179a0f7d17960dbb2e2beb476c31036c426e5475e658e394b0b75db34`.
- [World](../src/core/World.h), [implementation](../src/core/World.cpp),
  [seeded Random](../src/core/Random.h), [ten cases](../tools/wc3test/Cases.cpp),
  [runner](../tools/wc3test/main.cpp), [CMake](../CMakeLists.txt).
- [Hypotheses written before coding](phase-2-model.md), labelled observed,
  inferred or guessed; [build and reproduction](phase-2-procedure.md).
- [v1 report](../results/phase-2/v1/comparison.md),
  [v2 report](../results/phase-2/v2/comparison.md),
  [before-update diagnostic](../results/phase-2/v2-before/comparison.md).
  Each has the full JSON report and trace hashes beside it.
- [Revision/phase comparison](../results/phase-2/model-history.md),
  [raw verification](../results/phase-2/raw-verification.json),
  [evidence hashes](../results/phase-2/evidence-hashes.json).

Reference is **Warcraft III 1.29.2 (9231), x86 32-bit**,
`wc3-1.29.2-9231-x86`, captured in the recorded Windows 11 Pro ARM64 VM. The
installation was verified during Phase 1; this phase reads those retained captures
and does not launch WC3 or produce new retail observations. MOV-0002 uses revision
`MOV-0002-r2`, independently shown equal to Phase 0's SAMPLE payloads. Source,
maps, raw captures and environment remain unchanged.

Build host: macOS 27.0 build 26A428, arm64; system AppleClang
21.0.0.21000334, CMake 4.4.3, Python 3.14.7, Release configuration. `file` confirms
an arm64 Mach-O runner. No dependencies, window, raylib or wall-clock simulation
time. Float contraction disabled. Seed 1 is recorded, but movement consumes no
random draws and this RNG has no established WC3 correspondence.

## Primary result: footman-v2, after due updates

Each callback's samples precede its actions. C++ observations occur at requested
multiples of 0.02 s, after explicit 1 ms steps. WC3 times remain the printed 1000 s
clock readings. Rows are aligned by callback/unit in sequence order, not resampled.
X/Y tolerate 0.001 world unit, circular facing 0.001°, order exact; auxiliary time
check tolerates 0.0000615 s. These thresholds were fixed before either comparison
and were not widened. Deltas below are **C++ minus WC3**.

| Case | Samples WC3 / C++ | Result | First divergence | Reference → actual; delta |
|---|---|---|---|---|
| MOV-0001 | 251 / 251 | PASS | — | All state/order values agree |
| MOV-0002 | 502 / 502 | FAIL | cb 1, u0 Y | 0.014648 → 0; −0.014648 |
| MOV-0003 | 251 / 251 | FAIL | cb 3, u0 X | 9.544922 → 9.54594231; +0.00102031 |
| MOV-0004 | 601 / 601 | FAIL | cb 1, u0 Y | 0.007813 → 0; −0.007813 |
| MOV-0005 | 251 / 251 | FAIL | cb 1, u0 Y | 0.021484 → 0; −0.021484 |
| MOV-0006 | 251 / 251 | FAIL | cb 1, u0 Y | 0.014648 → 0; −0.014648 |
| MOV-0007 | 251 / 251 | FAIL | cb 1, u0 Y | 0.014648 → 0; −0.014648 |
| MOV-0008 | 251 / 251 | FAIL | cb 1, u0 Y | 0.014648 → 0; −0.014648 |
| MOV-0009 | 251 / 251 | FAIL | cb 7, u0 X | 2.672852 → 4.05000019; +1.37714819 |
| MOV-0010 | 251 / 251 | FAIL | cb 1, u0 Y | 0.014648 → 0; −0.014648 |

The [full report](../results/phase-2/v2/comparison.md) gives every property's sample
count, failing count, first mismatch, max and final delta, including u1 separately.
MOV-0002's control u1 agrees at all samples. u0's first X divergence is callback 4;
its final X delta is −3.990174, final Y −0.033203 and facing −0.388643°.

## Model revision and investigation

v1 moves every 1 ms with immediate facing changes. v2 adds the inferred 5 ms
position / 30 ms facing cadence, a 10 ms inclusive command delay, turn ramp and
135° movement threshold. Both use general target-directed displacement and a
guessed radius 16 stop check. Neither consults oracle files or branches on map ID;
only the runner knows the experiment number.

The [history table](../results/phase-2/model-history.md) records each case and
property's first divergence. Overall divergence moves later for MOV-0003 (1→3)
and MOV-0009 (1→7); all other overall first callbacks are unchanged. X moves from
callback 1 to 4 for all initially aligned straight cases. MOV-0009 facing improves
from 1 to 25, reversal order from 233 to 240, replacement order from 90 to 91,
and initially reversed arrival order from 183 to 189. No property's first callback
moves earlier in this revision. Both versions still pass just one whole case.
The facing error for MOV-0007 remains large (175.10212° max in v2): a later order
mismatch does not establish a correct reversal.

Inspection used raw run-01 records as well as derived values:

1. **First step and accumulating position error.**
   [JASS-0001-p001](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p001/run-01.txt)
   has its first displacement at callback 15, X=1.349609, then X=2.699707 at 20.
   v2 produces 1.35000002 and 2.70000005 at those requested instants. Its first
   MOV-0002 X error is below tolerance, but accumulates to +0.0010774 at callback 4
   and +0.013428 at callback 50. The raw MOV-0002 SAMPLE at callback 1 already has
   Y=0.014648 and facing=0.174245°, while our axis-directed rule yields both zero.
   The observed coordinate grid and heading drift remain unexplained; adding
   synthetic noise or copying the observed heading sequence would not model them.

2. **Arrival.** The guessed fixed radius and per-position stop check fail to explain
   all three measured speeds. The table includes order transitions and endpoints,
   rather than fitting each speed's stop distance:

   | Setup | Idle callback WC3 / v2 | Final X WC3 / v2 | Final X delta |
   |---|---|---|---|
   | Straight, 270 | 184 / 183 | 988.133301 / 984.143127 | −3.990174 |
   | Straight, requested 100 → 150 | 329 / 329 | 985.393066 / 984 | −1.393066 |
   | Straight, requested 522 → 400 | 125 / 124 | 995.957520 / 984 | −11.957520 |

   Agreement on MOV-0004's idle callback is insufficient: its endpoint is wrong.
   Only 20 ms samples exist around arrivals; the actual stop-check time/threshold
   cannot be recovered from them. Next proposed **MOV-0011** question: which
   position/order updates occur during approach and arrival across speeds and
   target distances, sampled at 1 ms? This would test a general arrival rule.

3. **Replacement latency and turning.** Raw
   [MOV-0006](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0006/run-01.txt) and
   [MOV-0008](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0008/run-01.txt) preserve
   the callback-50 position through callbacks 53 and 51 respectively. v2 already
   moves at callback 51 in both: the same command delay used for startup does
   not describe these interruptions, and the 135° threshold alone cannot explain
   the 90° pause. In
   [MOV-0007](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0007/run-01.txt), WC3 faces
   +46.814968° at callback 58; v2 faces 313.590363°, turning clockwise on its exact
   180° tie. WC3's pre-command heading is +0.137590°, so this does **not** establish
   the game's exact-tie policy. The unmodelled small initial heading can change
   which circular direction is shortest. No ID-specific turn direction was added.

4. **Movement while turning and residual facing.**
   [MOV-0009](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0009/run-01.txt) stays still
   through callback 6. v2 does likewise, and its facing agrees within tolerance
   through callback 24. At callback 7 it moves 4.05 along X versus WC3's
   (2.672852, 0.380859): the threshold/cadence hypothesis gets the broad onset but
   not the displacement phase or direction. In
   [MOV-0010](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0010/run-01.txt), both halt
   and become idle at callback 51, but WC3 facing continues to change through 58.
   v2 freezes it immediately. These are retained model limitations.

5. **Observation phase.** Raw JASS-0001-p001 has the first facing change at requested
   0.011 s, while p010 sees it at 0.010 s. Both observe the same state sequence;
   this is an observation-boundary ambiguity. v2 uses the p010-compatible phase.
   Sampling before an exactly due update changes 183 MOV-0002 rows and moves its
   first X mismatch back to callback 1 (−1.34970698); it also makes MOV-0009 facing
   diverge at callback 2 instead of 25. That diagnostic still passes only MOV-0001.
   Neither a phase shift nor before/after selection repairs the unexplained drift,
   stop distances and order latency. Both phase reports are retained; primary
   mismatches are never suppressed as ambiguous.

6. **Long-clock limit.**
   [MOV-0004 raw](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0004/run-01.txt)
   and its derived CSV agree at callback 503: requested 10.06 s, printed 10.059937 s,
   a +0.000063 s C++ delta. The maximum is +0.000112 s; 53 samples exceed the
   original one-ULP clock tolerance. JASS-0001's 10 s clock evidence covers only
   0.5–5 s and does not resolve this longer-run offset. No tolerance was widened
   and no C++ timestamp was forged to match it. Next proposed **JASS-0002** question:
   over 15 s, how do simultaneous elapsed/remaining clocks and requested callback
   counts distinguish accumulated timer error from clock quantization? Do not
   infer a different movement quantum from this discrepancy.

MOV-0011 and JASS-0002 are proposed questions, not authored maps or captured
experiments. No further model rules were guessed to fill these missing observations.

## Verification and acceptance scope

A clean detached checkout of the source commit above was configured and built with
the documented native Release command. CTest: **1/1 entry passed**, checking RNG
seeding, stationary invariance, finite/circular state and repeated ten-case bytes
for both versions. Python: **17 tests passed** (4 comparator integrity tests and
13 existing oracle parser tests). Independent executable repetitions of v1, v2
and v2-before matched **all 63 output hashes**, including identities. Numerical
comparison CLI exited 1 for the nine mismatches; missing input and an out-of-range
seed exited 2. A float-angle normalization bug found during initial execution was
corrected before the source commit; the circular-range invariant now checks all
movement samples. This was an implementation fix, not a hypothesis revision.

The [raw check](../results/phase-2/raw-verification.json) re-parsed 39 files: three
runs for each MOV case and p001/p010/p020. All runs passed capture validation,
within-map payloads matched, and both run-01 sample/event CSVs matched raw rows
exactly. This checks retained evidence integrity, not a fresh retail experiment.

All ten cases have complete numeric results, and MOV-0001/0002 are directly
comparable. Scope is these flat-map Footmen, fixed actions and one native build.
No pathing, collision, map loading, JASS, rendering, arbitrary units, WC3 RNG parity,
cross-platform determinism or general gameplay compatibility is demonstrated.

## Exact Phase 3 handoff

Next implement plan §6: define the canonical trace contract from these existing
raw records and C++ samples/actions, including identity, explicit time units,
monotonic sequence across interleaved observations/events, completion and reported
versus requested clock semantics. Preserve the original numeric strings and
equal-time order. Promote the provisional comparator to that contract with
property tolerances, first-divergence diagnostics and explicit observation-phase
handling; do not silently align away the nine known failures. Establish fixture
repeatability classification with its measured scope. Compatibility CI remains
Phase 4. New retail experiments and tagging v0.0.1 are separate steps.

# Phase 3: canonical traces and stable comparison

Completed 30 September 2026 for [issue #5](https://github.com/galitianu/warcraft-re/issues/5).
**The gate is met:** both producers use the [v1 contract](trace-contract-v1.md), all
45 retained Phase 1 captures validate independently, and complete canonical movement
comparisons preserve the existing one-pass/nine-failure result. This is a trustworthy
comparison capability, not a correction of the movement model.

Source/build tested: `7b3b4c25b430548dae904bf8d3e96e2ca0b3ac2f`, clean detached native
ARM Mac checkout; AppleClang 21.0.0.21000334, Release, arm64, FP contraction off.
Build source SHA-256 `fed4eb0c41dc9172a1068944754defb7142eaf180d69aa42295adb1880cdd52f`.
[Reproduction commands](phase-3-procedure.md), [evidence hashes](../results/phase-3/evidence-hashes.json),
[raw validation](../results/phase-3/raw-verification.json).

## Reference migration and repeatability

15 oracle-v1 maps × 3 retained fresh-process runs were parsed, checked against their
manifests and source hashes, and compared with the existing sample/event CSVs as
exact strings. Representative fixtures contain **10,730 records, 4,666 samples and
1,555 CLOCKS events**; every raw @O record, including BEGIN/SETUP/WATCH/RUN/TICK/END,
is mapped by source sequence and exact payload. Individual run identity, raw/payload
hashes, generated preload entries and differing footers are retained in every
fixture and the [index](../oracle/canonical/wc3-1.29.2-9231-x86/index.json).
No capture, derived CSV, reference numeric value or tolerance was changed.

All three observation payloads per map are identical. Classification is
DETERMINISTIC under the recorded map, WC3 x86 build, Windows 11 Pro ARM64 VM and
fresh-process capture procedure. Different raw-file/footer hashes are transport
variability. Other seeds/machines remain UNKNOWN; the retail seed was unset and
unobserved. Phase 0's independent MOV-0002 evidence remains in its original format.

Two independent C++ process runs per model/phase matched **93 full output files**:
30 canonical JSONs, 60 unchanged sample/action CSVs and three build identities.
[Repeatability](../results/phase-3/v2/repeatability.json) uses
RNG-DETERMINISTIC-WITH-SEED only for that fixed binary/seed scope. Movement does not
draw RNG; this does not demonstrate retail seed/stream compatibility.

## Numerical results

[v1 report](../results/phase-3/v1/comparison.md),
[v2 primary report](../results/phase-3/v2/comparison.md),
[v2 before-update diagnostic](../results/phase-3/v2-before/comparison.md).
Machine-readable JSON accompanies each Markdown report.

All three suites pass MOV-0001 and fail MOV-0002–MOV-0010 under the unchanged
X/Y 0.001 world unit, circular facing 0.001 degree, exact order and auxiliary
clock 0.0000615 second tolerances. Per-property sample counts, failures, first
mismatches, maximum errors and final signed deltas are **exactly identical** to
the retained Phase 2 results. All 60 legacy sample/action file hashes match.
The per-case mappings are recorded in [v1 migration](../results/phase-3/v1/migration.json),
[v2 migration](../results/phase-3/v2/migration.json), and
[diagnostic migration](../results/phase-3/v2-before/migration.json).

The v2 first state mismatches remain:

| Case | Callback / property | Signed actual − WC3 delta |
|---|---|---|
| MOV-0002 | 1 / u0 Y | −0.014648 |
| MOV-0003 | 3 / u0 X | +0.00102031 |
| MOV-0004 | 1 / u0 Y | −0.007813 |
| MOV-0005 | 1 / u0 Y | −0.021484 |
| MOV-0006 | 1 / u0 Y | −0.014648 |
| MOV-0007 | 1 / u0 Y | −0.014648 |
| MOV-0008 | 1 / u0 Y | −0.014648 |
| MOV-0009 | 7 / u0 X | +1.37714819 |
| MOV-0010 | 1 / u0 Y | −0.014648 |

MOV-0002 still ends −3.990174 behind in X. MOV-0004 still has **53 clock failures**,
first at callback 503 (requested 10.060000, observed 10.059937; +0.000063 s).
The 1000-second clock reading is never replaced by callback × period.

New action checks compare command/unit/order of issuance, callback/time, acceptance,
and point targets. Unit types and command acceptance agree in this scope. Relative
MOV-0006/7 callback-50 targets now expose v2 deltas **+0.013428 X / +0.023193 Y**;
both exceed the existing position tolerance. Each target is still computed from
its engine's own state, including the due step before an action in the before-update
diagnostic. No WC3 coordinate is substituted into the model. These are new action
failures; legacy state mismatches remain separately identifiable.

## Time, ordering and missing observations

One producer-local sequence covers all controls, samples, actions and events.
Comparison uses semantic callback/unit/observable record order, not equality of
instrumentation sequence numbers. Equal-time samples/events retain their order;
callback 0/50 samples precede commands. Structural diagnostics are separate from
numerical statistics, while invalid schema, incomplete input, bad identities,
nonfinite values and overflow are exit 2 rather than gameplay FAIL.

The [phase sensitivity report](../results/phase-3/phase-sensitivity.json) compares
v2's separately labelled before-update diagnostic against the same fixture and
lists changed sample states. Its callback-0 lag is zero; later samples lag 1 ms,
while commands still execute after the due step. No nearest-time resampling,
phase switching or dropped rows hides a mismatch. Retail update-boundary phase
remains unresolved. Clock quantization and the long-clock discrepancy remain
separate from position/order errors; observed 5 ms/30 ms cadences do not prove a
simulation quantum.

All five JASS-0001 variants' six/nine-decimal CLOCKS evidence is preserved. Equivalent
C++ CLOCKS/JASS observables are **UNOBSERVED**, never assigned passing statistics.
The current phase does not create a JASS interpreter, new maps or new observations.
Arrival, replacement latency, grid/heading drift, residual facing and long-clock
mechanisms remain the limitations described in [Phase 2](phase-2-results.md).

## Verification and Phase 4 handoff

The documented commands passed from the clean detached source checkout above:
native Release build, CTest **1/1**, Python **35/35**, 45 raw runs, 15 reproducible
fixtures, 30 complete canonical comparisons, 60 unchanged legacy CSV hashes,
30 identical legacy state reports and 93 repeated output files. Focused controls
check precision/source mapping, equal-time sample/action/event interleaving,
completion/counts/identity, circular facing, continued per-unit error reporting,
action timing/acceptance/targets and CLI exit 0/1/2, including numeric overflow.
No original WC3 installation was needed.

**Exact next action:** implement Phase 4 compatibility CI that builds the native
headless runner, validates committed canonical references and runs the comparator
with explicit expected baseline verdicts (MOV-0001 PASS, nine documented FAILs).
Keep input errors fatal and movement failures visible; do not turn all numerical
failures into infrastructure success. Add the planned small compiler/configuration
coverage and repeatability checks under named scope. The first moving primitive
improvement is [issue #6](https://github.com/galitianu/warcraft-re/issues/6), using the
same fixtures/tolerances and before/after reports. New MOV-0011/JASS-0002 captures
and release tagging remain separate work.

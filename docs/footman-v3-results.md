# footman-v3 results

Completed 1 October 2026 for [issue #6](https://github.com/galitianu/warcraft-re/issues/6).
**The compatibility gate is not met.** MOV-0001 still passes; MOV-0002–MOV-0010 still
fail the unchanged tolerances. footman-v3 does reproduce the update cadence, order
latency, turn onset, arrival callbacks and coordinate grid. All its order
samples now match, and X matches entirely for MOV-0004 and MOV-0010. The remaining
failures come chiefly from one unmodelled mechanism: east/west heading noise.
The rules are in [footman-v3-model.md](footman-v3-model.md).

Source/build tested: `781c7a2acde7c63eed480a18fe4673e62dc32951`, clean detached native
ARM Mac checkout configured with `git_dirty_at_configure: false`; AppleClang
21.0.0.21000334, Release, arm64, FP contraction off. Build source SHA-256
`771f1019078b3ddc7c7eaf05625e72da8763736bdb18aa12f6330cfd738d0233`. References are
the unchanged [canonical fixtures](../oracle/canonical/wc3-1.29.2-9231-x86/) from
WC3 1.29.2 (9231), x86 32-bit, `wc3-1.29.2-9231-x86`. No capture, fixture or
tolerance was changed. No new WC3 run was made.

Reports: [v3 primary](../results/footman-v3/v3/comparison.md),
[v3 before-update diagnostic](../results/footman-v3/v3-before/comparison.md),
[before/after](../results/footman-v3/before-after.md),
[observable behaviour](../results/footman-v3/behaviour.md),
[heading arithmetic](../results/footman-v3/heading-analysis.md),
[repeatability](../results/footman-v3/repeatability.json),
[evidence hashes](../results/footman-v3/evidence-hashes.json). Machine-readable JSON
accompanies each Markdown report.

## Reproduction

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/run_phase3.py --runner build/wc3test --out build/phase3 --reports build/phase3-reports
python3 tools/run_footman_v3.py --runner build/wc3test --out build/issue6 --reports build/footman-v3
python3 tools/analyze_heading.py --out build/footman-v3
python3 tools/compare_traces.py --actual build/issue6/v3   # exit 1: nine movement FAILs
```

`run_footman_v3.py` runs v2 (before), v3 and the v3 before-update diagnostic. It
compares all ten traces with the Phase 3 comparator, verifies the v2 run reproduces
every retained Phase 2 CSV hash, and reruns each suite in a separate process.
All output bytes must match. It returns 0 when the comparisons complete,
FAIL verdicts included, and 2 otherwise. `run_phase3.py` still reproduces every
v1/v2 Phase 2/3 statistic and CSV hash.

## Before and after

Primary after-due-update observation, failures / samples and maximum absolute
error (full table in [before-after.md](../results/footman-v3/before-after.md)):

| Case | X v2 → v3 | Y v2 → v3 | Facing v2 → v3 | Order v2 → v3 |
|---|---|---|---|---|
| MOV-0002 | 247, max 3.99 → 163, max 0.0190 | 239 → 239, max 0.0439 | 250 → 250 | 1 → **0** |
| MOV-0003 | 248, max 2.80 → 247, max 0.0596 | 248, max 2.80 → 247, max 0.0591 | 92 → 92 | 1 → **0** |
| MOV-0004 | 597, max 1.39 → **0** | 589 → 589 | 600 → 600 | 0 → 0 |
| MOV-0005 | 247, max 11.96 → 138, max 0.00195 | 242 → 242 | 245 → 245 | 1 → **0** |
| MOV-0006 | 247, max 2.87 → 180, max 0.0439 | 249, max 14.1 → 249, max 0.0439 | 250 → 250 | 3 → **0** |
| MOV-0007 | 247, max 3.95 → 183, max 0.0464 | 233, max 1.07 → 249, max 0.860 | 250, max 175.1 → 248, max 0.433 | 1 → **0** |
| MOV-0008 | 247, max 5.43 → 160, max 0.00195 | 249 → 249 | 250 → 250 | 1 → **0** |
| MOV-0009 | 244, max 3.91 → 166, max 0.0229 | 238, max 1.14 → 241, max 0.788 | 226, max 0.404 → 226, max 0.321 | 1 → **0** |
| MOV-0010 | 247, max 0.0134 → **0** (max 0.000488) | 249 → 249 | 250 → 250 | 0 → 0 |

First divergences: MOV-0002/4/5/6/7/8/10 still first fail in Y at callback 1, by
the same deltas as v2 (both models have no lateral drift). MOV-0003 first fails in X at callback 4
(+0.0014648, was callback 3). MOV-0009 first fails in Y at callback 9 (+0.00586,
was X at callback 7 by +1.377). X first diverges at callback 88 in MOV-0002
(+0.001465, versus v2's callback 4), 113 in MOV-0005 and 91 in MOV-0008, each by
three 1/2048 units.
MOV-0006/7 now fail one action property each: the redirect's target Y is computed
from v3's own callback-50 Y=0 instead of WC3's −0.023193.

Observable behaviour ([behaviour.md](../results/footman-v3/behaviour.md)):

| Behaviour | WC3 | v2 | v3 |
|---|---|---|---|
| Idle callback MOV-0002/4/5 (speed 270/150/400) | 184 / 329 / 125 | 183 / 329 / 124 | **184 / 329 / 125** |
| Idle MOV-0003/6/7/8/9 | 184 / 236 / 241 / 92 / 190 | 183 / 233 / 240 / 91 / 189 | **all equal** |
| First displacement MOV-0006 / 0007 / 0008 / 0009 | 54 / 58 / 52 / 7 | 51 / 58 / 51 / 7 | **54 / 58 / 52 / 7** |
| First travel ° MOV-0006 / 0007 / 0009 | 69.087669 / 172.220846 / 8.109577 | 90 / 180 / 0 | 68.755664 / 171.891873 / **8.109586** |
| Final X MOV-0004 / 0010 | 985.393066 / 267.287109 | 984 / 267.300537 | **985.393066 / 267.287109** |
| Final X MOV-0002 / 0005 | 988.133301 / 995.957520 | 984.143127 / 984 | 988.152344 / 995.959473 |
| MOV-0010 residual facing | 0.1376 → 0.3297 by callback 58 | frozen | frozen at 0 |

**Explained improvements.** Order replacement now waits for the next 30 ms update
and abandons the current batch. This gives MOV-0008's single frozen callback and
MOV-0006's three without a per-order delay. The pre-turn 60° window and 0.6 rad
turns produce the onsets of MOV-0006/7/9. Truncating float32 batches in the
map-corner frame give the exact per-batch X loss at all three speeds, so arrival
on the 30 ms update with radius 16 matches every idle callback. MOV-0005 needs its
83rd batch because 82 × (12 − 1/2048) leaves 16.04 to go. The reported-facing law
reproduces MOV-0009's entire 180° turn within 1e-6° through callback 24. Its X is
exact until callback 85. MOV-0007 now turns counter-clockwise because truncated
atan2 keeps the reversal just below π; no tie rule decides it.

**Regressions.** Y failures increased in MOV-0007 (233 → 249) and MOV-0009
(238 → 241). v2 never left Y=0, so it matched WC3 where WC3's drift returned near 0.
v3 now curves through its turns like WC3, but without WC3's heading noise its Y
differs by up to 0.86 and 0.79. Its maximum Y error is lower in both.
The MOV-0006/7 target-Y action failures above are new. No X or order statistic regressed.

**Diagnostic phase.** The before-update v3 diagnostic first diverges at callback 1
in X for every moving case (e.g. MOV-0002 −1.350098), and at callback 2 in facing for MOV-0009. It supports
the after-due-update observation phase for 20 ms callbacks and does not replace
the primary report.

## What still fails and why

1. **East/west heading noise (blocks MOV-0002 and every east/west case).**
   [Heading arithmetic](../results/footman-v3/heading-analysis.md) shows each 30 ms
   batch of JASS-0001-p001 moving 0.09–0.32° back toward Y=0, while the geometric
   correction is ±0.003°. Facing follows a hidden heading of ±0.27–0.41°. The hidden
   heading fits `acos` of a float32 cosine 185–431 ulps below 1. The travel angle's
   deficit is 159–167 ulps smaller, and it repeats with X's position on a 1/64 grid.
   The diagonal shows a matching direction-cosine shrink. Without this mechanism,
   v3's Y and facing fail from callback 1. The X error also accumulates where
   larger noise angles near arrival cost WC3 an extra 1/2048 in some batches: v3 ends
   +0.019 ahead in MOV-0002 and +0.00195 in MOV-0005. The pre-order hidden heading of 0.3297°
   causes MOV-0006/7's +0.33° travel residual and MOV-0010's residual facing.
   v3 does not fit these values.
2. **Diagonal step length (MOV-0003).** WC3's first 45° batch is 1/2048 shorter on
   both axes than truncated `8.1·cos 45°`; v3 accumulates +0.0596 by the end.
   This appears to be the same direction-cosine error, not a separate rule.
3. **Exposure rounding.** 8 of 150 p001 exposures are one grid unit higher than
   truncated linear interpolation. This is below tolerance and unresolved.
4. **Long clock.** MOV-0004's 53 clock failures from callback 503 are unchanged.

## Unmet gate and next experiment

MOV-0002, the first moving primitive, fails because footman-v3 cannot predict the
hidden heading for near-axial travel. Retained 1 ms data has a single east start
at x=0, so it cannot separate an X-grid dependence from distance, travel direction
or a constant. The smallest discriminating capture is proposed as **MOV-0012**:
*how does near-axial heading noise depend on start position modulo 1/64 and on
travel direction?* Sample one Footman at 1 ms with nine-decimal X/Y/facing for
0.5 s, using JASS-0001-p001's library and timing.

- Variants: east travel from (1/512, 0) and (3/512, 0), changing the start
  frac(64x) from p001's 0.
- Also: east travel from (0, 256), moving Y away from the frame boundary.
- Also: travel at 30° from the origin.

The model predicts each variant's onset and X. The noise hypothesis predicts how
batch ulps shift with frac(64x) and that 30° travel is quiet. MOV-0011 (1 ms
arrival) remains proposed, but is lower priority: v3 matches all arrival
callbacks. New captures require the [documented workflow](agent-wc3-workflow.md)
and provenance. No map was authored or captured for this result.

## Verification

From the clean detached checkout above: native Release build, CTest **1/1** (now
including footman-v3 grid, exposure, ramp, propulsion window, reversal and stop
checks), Python **37/37**, and `run_phase3.py` with all v1/v2 legacy
statistics/CSV hashes and 93 repeated files unchanged. `run_footman_v3.py`
completed 30 comparisons, reproduced the retained v2 CSV hashes, and found every
output file byte-identical in a second process for v2, v3 and v3-before.
`analyze_heading.py` predicts all 14 unsnapped braking steps within 0.000008°.
Repeatability covers this binary and seed only; movement draws no RNG and no
cross-compiler determinism is claimed.

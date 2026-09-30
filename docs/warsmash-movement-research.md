# Warsmash movement research

30 September 2026. Question: can Warsmash explain the retained Footman movement
captures and suggest a better C++ model? This is source research and arithmetic on
existing references, not a new WC3 capture or a compatibility result.

The strongest hypothesis is **separate movement heading and reported facing**.
Our v2 model uses its slowly changing facing for the movement gate, then moves
directly toward the destination. A faster internal heading, a 60° gate and a
separate facing smoother explain the measured turn pauses and travel directions
more coherently. The 30 ms movement-batch hypothesis below also explains the
different arrival distances better than checking arrival every 5 ms.

## Identities and inputs

- Read-only checkout: `/Users/andrei/Desktop/WarsmashModEngine`, remote
  `https://github.com/Retera/WarsmashModEngine.git`, clean commit
  `f9e0aeed4be372d6016519d0e97b384aa873f374`. No Warsmash build or execution.
- Retail references: `wc3-1.29.2-9231-x86`, WC3 1.29.2 (9231), x86 32-bit,
  captured in the Windows 11 ARM64 VM identified in the
  [environment manifest](../oracle/environment/wc3-1.29.2-9231-x86.json).
  Map/source/procedure identities and repeatability remain those of
  [Phase 1](phase-1-procedure.md); no additional platform scope is implied.
- Arithmetic uses u0 from `run-01-samples.csv` under
  [the retained derived references](../oracle/derived/wc3-1.29.2-9231-x86/).
  These are six-decimal JASS readings, not exact hidden state. Callbacks request
  0.02 s unless discussing the named 1 ms JASS variant. Preserve the reported
  clock readings; use callback × requested period only as nominal time.
- Read `Units\UnitData.slk` directly with `mpyq.MPQArchive(..., listfile=False)`
  from the local matching installation, without extracting game files into git.
  Both `War3.mpq` and `War3x.mpq` give hfoo `turnRate=0.6`, `propWin=60`,
  `orientInterp=0`. These are archive defaults, not a claim that arbitrary maps
  cannot override them. Rehashed both archives and matched the environment manifest:
  `60a4e380b3ae753b304be837edac53bebed0ae69b611e7f2ebfc2b036bf00d47`
  and `69fb8fd8aefe1657d75d53f970e20dbd9d9c23d42a3c2582cca4a97a16becfc7`.

## Separate headings explain turning

Warsmash's [CBehaviorMove](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/viewer5/handlers/w3x/simulation/behaviors/CBehaviorMove.java#L178)
turns logical facing by up to `turnRate` radians each simulation update. It checks
the **pre-turn** error against `propWin`, then moves along the updated logical
heading. A path must also be available. This order matters: a unit that turns
inside the window during an update still waits for the next update to move.

Separately, [RenderUnit](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/viewer5/handlers/w3x/rendersim/RenderUnit.java#L353)
smooths its own facing toward logical facing. Its
[orientation mode 0](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/viewer5/handlers/w3x/rendersim/OrientationInterpolation.java#L8)
accelerates by 0.07 rad and caps at 0.2 rad: the initial increments are
0.07, 0.14, 0.2 rad. At a 30 ms update these are 4.010705°, 8.021409° and
11.459156°, matching our observed large-turn ramp. The author describes this
table as an approximation inferred from gameplay; it is not recovered retail code.
Warsmash updates the smoother per render frame and scales the angle by
`deltaTime / 0.03`, so its implementation does not establish retail's cadence.

Apply a candidate 0.6 rad logical turn and pre-turn 60° gate to our observations:

| Case | First permitted logical turn | Predicted travel direction, nominal start heading | Measured first displacement direction | Measured facing at that sample |
|---|---|---|---|---|
| MOV-0006, 90° redirect | 2nd: prior error 55.6225° | 68.754935° | 69.087669° (callback 54) | 12.437501° |
| MOV-0007, 180° reverse | 5th: prior error 42.4901° | 171.887339° | 172.220846° (callback 58) | 46.814968° |
| MOV-0009, start facing 180° | 5th: prior error 42.4901° | 8.112661° | 8.109577° (callback 7) | 133.590378° |

Reproduce measured directions with
`degrees(atan2(new_y-old_y, new_x-old_x)) % 360`. For MOV-0006/7 the old sample is
callback 50, immediately before the replacement order; for MOV-0009 it is callback
0. Select the first subsequent changed position. Predictions use `degrees(n*0.6)`
for an initially eastward unit and `180-degrees(n*0.6)` for MOV-0009.

The first two differences are approximately the same +0.333° heading offset,
consistent with a shared pre-order hidden heading. That heading has **not** been
observed directly and must not become a fitted per-case constant. MOV-0009 differs
by about 0.0031°, so even this strong explanation leaves numerical work.
Its separately predicted reported facing after five updates is
`180-degrees(0.07+0.14+3*0.2) = 133.590419°`, only 0.000041° from the capture.

The timing also fits a candidate globally phased 30 ms logical update: initial
turns at nominal 0.01, 0.04, …; the fifth at 0.13 precedes MOV-0009's first
observed displacement at 0.14. After the order at 1.00, turns at 1.03, 1.06, …
make MOV-0006 eligible at 1.06 and MOV-0007 at 1.15; their first changed samples
are 1.08 and 1.16. A collinear replacement needs no turn wait but could wait until
1.03, explaining MOV-0008's frozen 1.02 sample and movement at 1.04. These are
phase hypotheses, not measured internal tick timestamps or an established path
latency mechanism. Continuing facing after `stop` is also consistent with a
separate smoother.

**Critical limit:** Warsmash's JASS
[GetUnitFacing](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/parsers/jass/Jass2.java#L3625)
and [GetUnitX/Y](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/parsers/jass/Jass2.java#L4259)
return logical CUnit state, not RenderUnit's smoothed state. Our retail readings
come from these JASS natives. Thus Warsmash suggests the separation but does not
implement the observable interface needed to reproduce our traces. Calling the
retail readings literally renderer state would go beyond the evidence.

## Larger movement batches could explain arrival

Warsmash [smooths position toward logical coordinates](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/viewer5/handlers/w3x/rendersim/RenderUnit.java#L200)
at `speed * renderDeltaTime`. This provides a mechanism by which smaller observed
position steps need not be the logical movement quantum. Retail's 5 ms position
cadence therefore does not require checking arrival every 5 ms, as v2 does.

For each final reference position compute radial displacement from origin and
divide by `speed * 0.03`. Rounded to the nearest integer, the results are:

| Case | Speed | Candidate 30 ms batches | Ideal displacement | Observed displacement | Observed − ideal |
|---|---|---|---|---|---|
| MOV-0002-r2 | 270 | 122 | 988.2 | 988.133302 | −0.066698 |
| MOV-0003 | 270 | 122 | 988.2 | 988.111638 | −0.088362 |
| MOV-0004 | 150 | 219 | 985.5 | 985.393066 | −0.106934 |
| MOV-0005 | 400 | 83 | 996 | 995.957520 | −0.042480 |
| MOV-0008 | 270 | 60 | 486 | 485.974609 | −0.025391 |
| MOV-0009 | 270 | 122 | 988.2 | 988.048340 | −0.151660 |

MOV-0008 includes movement before replacement; the count is a whole-path
arithmetic comparison, not a count of identical directional steps. MOV-0009 also
turns during travel, so radial displacement is not total path length.

A candidate 16-unit arrival radius checked at 30 ms boundaries can accommodate
the different short stops. At speed 400, 82 ideal batches reach 984 exactly;
even a tiny accumulated shortfall leaves the unit more than 16 away, requiring
batch 83. This is a plausible explanation, not proof of a 16-unit radius.
The nominal completion times `0.01 + batches*0.03` give first 20 ms observation
callbacks 184, 329 and 125 for the straight 270/150/400 cases, matching the captures.
Adding the four blocked turning updates (0.12 s) gives callback 190 for MOV-0009.

As a further numerical clue, MOV-0004's final X equals
`219 * (4.5 - 1/2048) = 985.39306640625` within six-decimal printing. This does
not establish the quantization rule: all measured coordinates lie on a 1/4096
grid, and other cases have heading drift and different accumulated losses.

Warsmash itself uses a
[50 ms simulation step](https://github.com/Retera/WarsmashModEngine/blob/f9e0aeed4be372d6016519d0e97b384aa873f374/core/src/com/etheller/warsmash/util/WarsmashConstants.java#L20),
walks to the exact waypoint, and has no equivalent 16-unit stop in the inspected
move behavior. Its timer tick handling also cannot explain the retail 1 ms
callbacks. The proposed 30 ms batching comes from retail arithmetic, not its
simulation constant. No applicable 1/4096 coordinate rule was found in the
inspected movement/render paths. The inspected speed setter and derived speed
calculation also do not explain retail's measured 150–400 clamp.

## Consequence for our engine

Keep Phase 2 results and tolerances intact. After Phase 3 fixes the trace contract,
the next movement increment should test one general candidate model:

1. Separate hidden movement heading from reported facing; use the default
   0.6 rad turn and a pre-turn 60° propulsion window for this Footman.
2. Test globally phased 30 ms movement/order/arrival updates with observed
   5 ms position exposure and a separate 30 ms facing smoother. Both are
   headless state updates; importing a graphics frame loop is unnecessary.
3. Investigate grid/angle precision from the retained traces before choosing
   quantization. Preserve the measured speed clamp independently of Warsmash.

Acceptance remains the existing fixed property tolerances on every MOV-0001–10
trace, with first divergences retained. Improved pauses or approximate endpoints
alone do not constitute compatibility. Missing evidence includes direct logical
state, high-frequency redirect/arrival sampling, and controlled turn-rate and
propulsion-window changes. No engine code, fixtures, comparisons or third-party
checkout were changed for this research.

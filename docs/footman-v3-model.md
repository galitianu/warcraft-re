# footman-v3 movement hypotheses

For [issue #6](https://github.com/galitianu/warcraft-re/issues/6). Written while the
model was being developed from the retained captures, and before its comparison
results were recorded. Authority is the
[committed WC3 fixtures](../oracle/canonical/wc3-1.29.2-9231-x86/): WC3 1.29.2 (9231),
x86 32-bit, `wc3-1.29.2-9231-x86`, in the recorded Windows 11 Pro ARM64 VM. No new
capture was made. Warsmash (`f9e0aeed4be372d6016519d0e97b384aa873f374`, read-only)
suggested which hypotheses to test; it is not evidence of retail behavior. No
code is imported from it. Arithmetic is reproduced by
[analyze_heading.py](../tools/analyze_heading.py) and retained in
[heading-analysis.md](../results/footman-v3/heading-analysis.md).

**Behavioral question.** Does one general model with a hidden movement heading,
globally phased 30 ms logical updates, 5 ms position exposure, a separate
reported-facing smoother and round-toward-zero float32 state reproduce MOV-0001–
MOV-0010? **Acceptance gate:** unchanged X/Y 0.001, facing 0.001° circular, exact
order and 0.0000615 s clock tolerances on every sample/action of all ten traces.
The model has no experiment IDs, callbacks or reference coordinates. footman-v1/v2
and their retained results are unchanged.

Status words: **observed** means read directly from retained captures; **inferred**
is a rule that reproduces several independent observations; **guessed** is a choice
that the retained evidence does not determine.

## Rules

| Rule | Status and evidence |
|---|---|
| Logical updates every 30 ms at 10, 40, 70, … ms after callback 0 | **Inferred.** p001/p010 facing changes; batch boundaries in p001; MOV-0006/7/8 order timings below. The phase is relative to the oracle's callback 0, not a measured internal timestamp. |
| An order is first processed at the next update | **Inferred.** Callback-50 orders follow the 1.00 s update; WC3's first effects are at 1.03 s (turn) and 1.035 s (MOV-0008 exposure). No order-specific delay. |
| A replacement or stop abandons the current batch where it is shown | **Inferred** from MOV-0008's frozen callback 51 and MOV-0010's unchanged callback-50 position. |
| Each update turns a hidden heading by at most 0.6 rad toward the target | **Inferred.** Footman `turnRate=0.6` in matching game archives (recorded in the [research](warsmash-movement-research.md)). MOV-0009 first travels at 8.109577° versus predicted 8.109586°. |
| Movement uses the post-turn heading only if the pre-turn error is ≤ 60° | **Inferred.** `propWin=60`. Predicts the frozen callbacks of MOV-0006 (3), MOV-0007 (7) and MOV-0009 (6). |
| Each moving update computes a batch of `speed × 0.03` along the heading | **Inferred.** p001 batches have constant dX of 33176/4096. Arrival callbacks at 150/270/400. |
| The batch is exposed in six equal 5 ms steps | **Inferred.** p001: linear interpolation then truncation matches 142/150 exposures; the other 8 differ by one grid unit (≤ 0.000488, below tolerance). Mechanism of those 8 unresolved. |
| An update ends the order when the target is ≤ 16 units away | **Guessed radius, inferred cadence.** Observed stop distances lie in [14.61, 16.04). Inclusive/exclusive boundary is not observed. |
| Speed clamp 150–400 | **Observed** endpoints (Phase 1), unchanged from v1/v2. |
| Coordinates are float32 relative to the map's minimum corner (−4096, −4096) | **Inferred.** 6,222 retained MOV coordinates: all are multiples of 1/4096, and every odd multiple is negative (none of ≥ 0). This is float32 spacing in [2048, 4096) versus [4096, 8192) after a +4096 offset. Origin is a property of the 64×64 oracle map. |
| Float32 results round toward zero | **Inferred.** Facing 180 reads 179.999985 and 45 reads 44.999996 after a truncating degree→radian→degree round trip; round-to-nearest returns 180 and 45 exactly. Truncation also gives every observed per-batch X: 8.099609375 at 270, 4.5−1/2048 at 150 (MOV-0004 ends exactly at 219 batches) and 12−1/2048 at 400, which forces MOV-0005's 83rd batch. The emulation evaluates each operation in double and truncates once; the exact retail operation order is unknown. |
| Reported facing chases the hidden heading every update with velocity carry-over: add 0.07 rad, cap 0.2 rad, brake to `err × (err/0.2 rad)^¼`, snap when `err < 0.001 rad` | **Inferred.** The 0.07/0.14/0.2 rad ramp (MOV-0006/7/9; Warsmash orientation mode 0). The braking law predicts all 14 unsnapped approach steps after MOV-0002's arrival, MOV-0010's stop and MOV-0006's turn within 0.000008°. Snaps occur at errors ≤ 0.0547°; a 0.0590° error does not snap. MOV-0006/7 start their ramp from the previous 0.1339° step, showing carried velocity. Warsmash's own end phase differs and is not used. |
| An exact reversal turns counter-clockwise | **Guessed** and never exercised here. Under truncation no retained case is an exact tie: WC3's MOV-0007 heading is +0.33° before reversing, and MOV-0009's 180° start is stored below π. |
| No lateral wander, heading noise or randomness | **Known omission.** The next section records why. Movement draws no RNG. |

## Not modelled: east/west heading noise

East/west travel zigzags (Y within ±0.04, facing ±0.26°), whereas travel north
(MOV-0006 after its turn) is straight and diagonal facing stays within 45 ± 0.0016°.
Retained arithmetic constrains the mechanism but does not determine it:

- In p001, each 30 ms batch moves in one direction. That direction always points
  back toward Y=0, with magnitude 0.09–0.32°. The geometric target direction is only
  ±0.003°.
- Inverting the braking law gives the hidden heading each batch chases: ±0.27–0.41°.
  Its square in units of `acos(1 − 2⁻²⁴)²` is within ±0.2 of an integer in every
  batch. This suggests the heading is `acos` of a float32 cosine 185–431 ulps below 1.
  `acos` is ill-conditioned only near 0° and 180°, which explains the axis dependence.
- The batch travel angle has a deficit about 163 ulps smaller (159–167 across all 16
  batches). That deficit repeats every 8 batches, matching X's advance of
  518.375/64 per batch. It is consistent with
  `(frac(64·x) − ~0.04) / 64 / distance`, but the offset and the computation that
  would produce a 1/64-unit X dependence are unknown.
- On the diagonal, WC3's first batch is one 1/2048 unit shorter on both axes than
  truncated `8.1·cos 45°`, and facing reads 45.00053°. Both fit a direction
  cosine about 9.3e-6 below exact, the same magnitude as the 163-ulp constant.
- The pre-order hidden heading derived this way (0.3297°) explains MOV-0006/7's
  +0.333° travel residual and MOV-0010's residual facing target. It is therefore
  not an independent constant.

Implementing a fitted `frac(64x)` rule, a 163-ulp constant or a copied heading
sequence would be per-observation fitting, so footman-v3 does not. Its X, order and
turn timing can be correct while Y/facing fail from callback 1 of east/west travel.

## Observation and comparison

Unchanged from Phase 2/3: samples after all 1 ms steps due at the requested callback
time; callbacks 0/50 sample before issuing orders; MOV-0006/7 targets come from the
engine's own callback-50 state. A before-update diagnostic is labelled separately
and never replaces the primary comparison.

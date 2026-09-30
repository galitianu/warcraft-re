# Phase 1 results: manual movement oracle library

Captured 30 September 2026 for [issue #2](https://github.com/galitianu/warcraft-re/issues/2),
from `wc3-1.29.2-9231-x86` in the recorded Windows 11 Pro ARM64 VM. The installation
was re-verified at capture time (see each manifest). Definitions:
[phase-1-experiments.md](phase-1-experiments.md). Procedure:
[phase-1-procedure.md](phase-1-procedure.md). Everything below is an observation of
these setups unless it is labelled a hypothesis.

## Library and repeatability

There are 15 new maps: 10 movement maps and 5 JASS-0001 timing variants. All were
authored in World Editor from the Phase 0 map, with [oracle-v1](../oracle/jass/lib/oracle-v1.j)
plus one case file in the single custom-text trigger. Every saved map passed
[check_map.py](../tools/check_map.py) (exact trigger text, no header script,
`war3map.j` contents, RoC w3i format 18).

Each map has **3 fresh-process captures**, with the old output deleted and confirmed
absent before every launch. All 45 parse with [oracle_parse.py](../tools/oracle_parse.py).
Within each map the three `@O` observation payloads are **identical**, and so are
WC3's generated preload entries (26 asset paths). Raw files differ only in the
generated `PreloadEnd` footer (5.0/5.1; 0.6/0.7 for p001; 12.0 for MOV-0004).
Hashes and runs are in each `oracle/captures/wc3-1.29.2-9231-x86/<map>/manifest.json`.
Parsed CSVs and the summary are in [oracle/derived](../oracle/derived/wc3-1.29.2-9231-x86/).
RNG seed was not set; repeatability is established for this setup only.

One earlier MOV-0001 trial capture was discarded before retention. The parser then
rejected WC3's generated asset lines, and the capture lacked run metadata. It was
not used for any result.

| Map | Records | Result in one line | Captures |
|---|---|---|---|
| MOV-0001 | 507 | Stationary: (0,0), facing 0, order 0 for all 251 samples | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0001/) |
| MOV-0002-r2 | 760 | All 502 SAMPLE payloads equal Phase 0's MOV-0002 | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0002-r2/) |
| MOV-0003 | 508 | Diagonal: same arrival callback as straight, radial stop 988.111638 | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0003/) |
| MOV-0004 | 1208 | Requested 100 → reported 150; 3.0 units per 0.02 s | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0004/) |
| MOV-0005 | 508 | Requested 522 → reported 400; 8.0 units per 0.02 s | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0005/) |
| MOV-0006 | 509 | 90° redirect: no displacement for 3 callbacks, then moves while turning | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0006/) |
| MOV-0007 | 509 | 180° redirect: no displacement for 7 callbacks | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0007/) |
| MOV-0008 | 509 | Collinear replacement: one frozen callback, then stops 14.03 short of 500 | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0008/) |
| MOV-0009 | 508 | Turn from 180°: first displacement at callback 7, facing 133.59° | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0009/) |
| MOV-0010 | 509 | Stop: order 0 and no further displacement from callback 51 | [dir](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0010/) |
| JASS-0001-p001…p050 | 309–1509 | See timing below | [p001](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p001/) [p010](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p010/) [p020](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p020/) [p025](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p025/) [p050](../oracle/captures/wc3-1.29.2-9231-x86/JASS-0001-p050/) |

## JASS-0001: sampling and clock precision

**Clock resolution depends on the timer's duration.** In the same callbacks, the
elapsed readings of three one-shot clocks started together differ in resolution:

| Clock | Observed callback intervals at requested 0.02 s (p020) |
|---|---|
| 1000 s, 6 dp (library TICK) | 0.019958, 0.019959, 0.020019, 0.020020 |
| 100 s, 9 dp | 0.019996608 … 0.020004288 |
| 10 s, 9 dp | 0.019999488 … 0.020000456 |

The spread matches float32 resolution at each clock's remaining time: 2⁻¹⁴ ≈ 6.1e-5
below 1024 s, ≈ 7.6e-6 below 128 s, ≈ 9.5e-7 below 16 s. Also, 10 s-clock
`elapsed + remaining` always reads 10 within 7e-8. Phase 0's 0.019958/0.020020
intervals are therefore clock quantization, not irregular callbacks. The evidence
is consistent with elapsed being computed as duration minus a float remaining time;
that is a hypothesis about the mechanism. At every requested period (0.001, 0.010,
0.020, 0.025, 0.050 s), the 10 s clock reports intervals within ±1e-6 s of the
request. No two callbacks share a reading: there are 0 equal-time callbacks, even at
0.001 s, 500 callbacks. So timer callbacks are not limited to the observed unit-update
cadence below.

**R2SW precision:** `R2SW(value, 1, 9)` does emit 9 decimals, but not the exact float.
The nearest float to 2.699707 is 2.69970703125, and 9-dp output prints 2.699707008;
8.099609375 prints 8.099609368. The six-decimal library fields are unaffected. No
output here establishes internal bits beyond what is printed.

**Observed unit-state cadence** (single Footman, move to (1000,0) at t=0):

- **Position:** with 1 ms callbacks (p001), X/Y change at 97 callbacks in 0.5 s.
  95 gaps are 5 callbacks and one is 6 (0.035 → 0.041). Each change is 1.349609 or
  1.350097 units, which is 270 × 0.005. The first displacement is seen at 0.015 s. At
  p010, callbacks show 2.6997 per 0.01 s, and nothing at t=0.01.
- **Facing:** facing changes every 30 callbacks at p001 (0.011, 0.041, 0.071, …).
  At p010 it changes at 0.010, 0.040, 0.070, …, i.e. every 0.03 s. During turns it steps
  by 11.459152° (0.2 rad) per change.
- **Consistency across samplings:** within the first 0.5 s, every distinct state that
  p010, p020, p025 and p050 observe occurs, in order, in p001's state sequence. From
  0.04 s, p001's reading at a given 1000 s-clock time can show the state from just
  before an update that p020 already shows. p010 and p025 likewise differ from p020 in
  facing at a few instants when facing updates (e.g. t = 3.52). All positions at shared
  readings agree for p010, p025 and p050, and all final states equal p020's.

**Established:** in these maps, requested periods down to 0.001 s give callbacks at
the requested spacing. Positions change about every 0.005 s and facing every 0.03 s
of clock time. The sampling period changes *which* states are observed, not the
sequence of states observed. Repeatability holds within each variant.

**Not established:** the mechanism, a simulation quantum, and whether 0.005/0.03 s
cadences hold for other units, speeds, loads or machines. Also unestablished: what
orders a timer callback relative to a unit update due at the same time, and the one
6-callback position gap. Samples at 0.02 s alias a 0.03 s facing cadence, which is
why facing appears to change in two of every three callbacks. Treat any timestep
chosen for C++ as a hypothesis to test against these captures.

## Movement cases

The one-factor baseline is `JASS-0001-p020`. Its u0 samples equal `MOV-0002-r2`'s u0
samples at all 251 callbacks, so the `u1` control and the extra clock logging did not
change u0. "Callback n" is the nth 0.02 s callback on the 1000 s clock.

**MOV-0001 (stationary).** An uncommanded Footman kept X=0, Y=0, facing 0 and order 0
at all 251 samples over 5.000000 s. The unit also reports speed and default speed
270. Scope: 5 s, no seed, acquisition range 0.

**MOV-0002 (straight, reproduced).** The oracle-v1 revision's 502 SAMPLE payloads
are byte-identical to Phase 0's; only envelope and record numbering differ. Order
851986 is seen from callback 1 and becomes 0 at callback 184 (t=3.680054). The unit
then stays at X=988.133301, Y=0.033203. Facing keeps changing until callback 190
and ends at 0.388643. It never reaches 1000: it stops 11.866699 short. Lateral Y
stays within −0.038…+0.044, and facing within 0.26° of 0 while moving.

**MOV-0003 (diagonal).** The target 707.106781 was issued as 707.106750 (float). The
initial facing 45 reads 44.999996. Arrival is at the same callback, 184, and the unit
stops at (698.700195, 698.700684), 988.111638 from the origin versus 988.133301
straight. The most common step is 5.399285 versus 5.399414–5.399903 straight.
Facing stays within 45 ± 0.0016°, much steadier than the straight case (up to 0.26° off while moving). That
the grid-aligned axis makes the difference is a hypothesis.

**MOV-0004 (speed 100).** `SetUnitMoveSpeed(100)` is reported as speed **150**; the
default is still 270. The steady step is 2.999512 per callback, i.e. 150 units/s.
Arrival is at callback 329 (t=6.580017), at X=985.393066, 14.606934 short. The
trace confirms the clamped value is the one used.

**MOV-0005 (speed 522).** Reported speed is **400**; the steady step is 7.999512
(400 units/s). Arrival is at callback 125 (t=2.500000), at X=995.957520, 4.042480
short. 522 is not reached in this RoC-format map. Why the stop distance is 11.87,
14.61 and 4.04 at 270, 150 and 400 is unexplained.

**MOV-0006 (90° redirect).** At callback 50 the unit is at (267.287109, −0.023193).
The new order targets (267.287109, 999.976807) and is accepted. There is **no
displacement at callbacks 51–53**. Facing turns 0.14 → 4.28 → 12.44, then +11.459°
steps. The first displacement comes at callback 54 (t=1.080017) while facing is
12.44°, moving mostly +Y (X drifts to 270.17 at most). Facing is within 1° of 90 at
callback 64. Arrival is at callback 236 at (267.322754, 987.575195), 12.40 short,
with final facing 90.165085.

**MOV-0007 (180° redirect while moving).** The redirect target is (−732.712891,
−0.023193). There is **no displacement at callbacks 51–57** (7 callbacks, ~0.14 s).
Facing turns through 90 (increasing), so the unit turns counter-clockwise. The first
displacement is at callback 58 (t=1.160034) while facing is 46.81°. It moves in −X,
with Y deviating up to +1.07. Facing is within 1° of 180 at callback 76, and the unit
stops at X=−720.797363 (11.92 short) at callback 241.

**MOV-0008 (collinear replacement).** Replacing (1000,0) with (500,0) at callback 50
gives **one callback without displacement** (51). Motion resumes at callback 52 in
the same direction with no turn. That is the only deviation from the baseline before
arrival: the first divergence from p020 is callback 51. Order becomes 0 at callback 92
(t=1.840027) at X=485.974609, 14.025391 short of 500. So an accepted replacement move
order takes effect by the next observed callback: the old trajectory is abandoned,
with a pause of 0.02 s or less at this sampling.

**MOV-0009 (initially facing away).** Facing 180 reads 179.999985. The unit turns
toward 0 through decreasing angles: 175.99, 167.97, then −11.459° steps. It is
**stationary through callback 6** and first displaced at callback 7 (t=0.140015)
while facing 133.59°, moving about +8° off the X axis. Facing is within 1° of 0 at
callback 25 (x=99.81). Arrival is at callback 190 at X=988.048340, 0.085 behind
MOV-0002's stop.

**MOV-0010 (stop).** `stop` at callback 50 is accepted. Order is 0 from callback 51,
and position stays at (267.287109, −0.023193), the callback-50 position, for all later
samples. Facing still changes for a few updates (0.1376 → 0.3297 by callback 58),
then holds.

**Hypotheses raised, not tested:** (1) a new move order or stop suspends
displacement for at least one update. The 90° and 180° redirects and the start from
rest wait until facing is within about 135° of the travel direction: first
displacement came at 77.6°, 133.2° and 133.6° off. (2) Turning uses 0.2 rad per
0.03 s after a short ramp (4.0°, 8.0°). (3) Emitted positions are on a 1/4096 grid:
all 9,332 X/Y values in these 15 maps are multiples of 1/4096 within six-decimal
rounding, and 44 of 1,004 values in MOV-0002-r2 are not multiples of 1/2048.

## Limits

- Six-decimal values; seeds unset; one machine and VM configuration; RoC-format maps
  (w3i 18) played on the installed game.
- Each movement case uses one timer period (0.02 s) and one clock (1000 s). Its
  times carry that clock's ±6e-5 s quantization.
- Three captures per map show repeatability, not general determinism.
- Stop distances, turn thresholds and pauses are observations of these setups, not rules.

## Phase 2 handoff

`MOV-0001` and `MOV-0002` (`MOV-0002-r2` plus Phase 0's 20 runs) are ready as the first
C++ comparison experiments. Use their `SAMPLE` rows (`oracle/derived/.../run-01-samples.csv`)
as initial state, per-callback X/Y/facing/order and final state. JASS-0001 supplies
the sampling context: positions change about every 0.005 s and facing every 0.03 s;
treat both as hypotheses to test. Keep every experiment's 0.02 s callback times as
observation times, not as the C++ step.

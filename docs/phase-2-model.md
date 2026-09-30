# Phase 2 movement hypotheses

For [issue #3](https://github.com/galitianu/warcraft-re/issues/3). Written before
implementation. Authority is the committed WC3 captures; this document describes
a proposed model, not established retail mechanics. No rules depend on experiment
IDs, callbacks, reference CSVs or previously observed coordinates.

## Increments and acceptance checks

1. Can a small native world reproduce stationary state and generate finite,
   deterministic movement observations? Build a C++20 library and runner with no
   dependencies or window. Check RNG seeding, stationary invariance and identical
   trace bytes on repeated runs. These are engine checks, not gameplay passes.
2. Where does a deliberately simple movement model first diverge? Run v1 for all
   ten Phase 1 MOV setups, sample before callback actions, and compare every
   X/Y/facing/order value. Require complete sample counts, explicit tolerances,
   first divergences and max/final deltas even when comparisons fail.
3. Does incorporating the observed cadences improve the same suite? Run v2 under
   unchanged tolerances and record first-divergence changes for every case and
   property. Investigate remaining errors against raw MOV and JASS-0001 records;
   retain both versions. An improvement in one case does not justify concealing
   regressions in another.

## Shared hypotheses

| Rule | Status and evidence |
|---|---|
| Footman default speed 270 units/s; requested speed clamped to 150–400 | Observed for these setups: WATCH and displacement in MOV-0002/0004/0005. General clamp between endpoints is inferred. |
| Move order 851986; stop 851972; idle current order 0 | Observed IDs in SAMPLE rows; stop action resolves to idle by next sample (MOV-0010). |
| Coordinates and facing stored as float32 | Inferred from issued diagonal target and clock precision, not an exact internal-state claim. Emit nine significant digits for float state. |
| Central Random owns a seeded `std::mt19937` stream | Guessed implementation choice, **no WC3 RNG compatibility claim**. Movement uses no draws. Seed 1 by default, recorded in identity. |
| One explicit step = 0.001 s; integer step scheduling | Guessed integration/scheduling parameter. JASS-0001 permits 1 ms observations; it does **not** establish a WC3 simulation quantum. |
| Displacement points directly at the destination, independent of facing | Inferred approximation: MOV-0007/0009 travel toward their target while facing far away. Lateral wander is unmodelled. |
| Stop when distance is at most 16 world units, checked before movement; idle immediately | Guessed round radius, motivated only by observed short stops (roughly 4–15). No speed-dependent rule established; do not fit one from three endpoints. |
| Stop cancels movement and freezes facing immediately | Guessed simplification; MOV-0010 already shows residual facing updates, so a facing mismatch is expected. |

## footman-v1: simple baseline

Every 1 ms step moves by speed × 0.001 toward the destination. Facing snaps to the
travel direction on that step. Orders have no latency; no turning threshold or
grid quantization. The initial callback samples before issuing move. This is an
intentionally simple guessed baseline; it should expose the first-callback
half-step, turning and arrival differences.

## footman-v2: cadence hypothesis

Only these changes from v1 are proposed:

- Position advances on every fifth explicit step (0.005 s), by speed × 0.005.
  A move command suspends movement for 0.010 s inclusive, so an aligned command at
  t=0 first moves at 0.015 s. **Inferred** from JASS-0001-p001's first displacement
  and MOV-0002's half-sized first callback; applying the same delay to replacement
  orders is **guessed** and may fail MOV-0008.
- Facing advances at 0.010 s then every 0.030 s, before position updates due at
  the same instant. **Inferred** cadence/initial phase from JASS-0001-p010; relative
  update ordering is **guessed**.
- Turn increments ramp through 0.07, 0.14, then 0.2 radians per facing update,
  capped at the remaining circular angle. The ramp resets on each move order.
  **Inferred approximation** from MOV-0006/0007/0009's 4°, 8°, 11.459° ramp.
- Movement waits while facing is more than 135° from the travel direction.
  **Inferred approximation** from MOV-0007/0009's first movement. This alone cannot
  explain MOV-0006's three frozen callbacks. Exactly opposite directions turn
  clockwise (negative angle); this tie choice is **guessed** and MOV-0007 may fail.

No grid quantization or synthetic lateral/facing noise is added: captures show
these effects, but do not establish a causal rule. The model is expected to fail
small tolerances even if its broad timing improves.

## Observation and comparison policy

Runner samples at requested callback × 0.02 seconds, after all steps due at that
instant, and then performs callback actions. Callback 0 precedes all orders.
MOV-0006/0007 targets come from the **model's** callback-50 state, exactly as JASS
uses its own state. MOV-0002 includes u1; MOV-0004 has 600 callbacks; others 250.

Match by ordered (callback, unit), never nearest timestamp or sorted float time.
The reference's 1000 s clock is quantized; preserve its printed readings and report
time deltas separately against the requested C++ schedule. Provisionally use
0.001 world unit for X/Y, 0.001 degree circular difference for facing, exact order,
and 0.0000615 s for the clock check (one float ULP below 1024 s plus print rounding).
Declare these in `tools/compare_movement.py` only. Never widen them to obtain passes.

Coincident sample/update ordering is unresolved in WC3. The primary comparison
keeps the chosen after-update phase and every mismatch. Additional before-update
observations can diagnose a boundary difference, but cannot replace the primary
trace or turn its failure into a pass. Neither phase resolves grid/wander or
arrival mechanisms. [Phase 1 results](phase-1-results.md) describe p001/p010/p020
observing neighboring states at shared clock readings.

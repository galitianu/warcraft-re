# Phase 1 experiment definitions

Defined before authoring, for [issue #2](https://github.com/galitianu/warcraft-re/issues/2).
Permanent IDs are never reused for a different question. Results are recorded
separately in [phase-1-results.md](phase-1-results.md); nothing here is a measurement.

## Common setup

Every map is authored manually in World Editor 1.29.2.9231, starting from the Phase 0
map (64×64 Lordaeron Summer, flat Dirt, no water, no placed units or doodads, one
player start location). Its single custom-text trigger (Melee Initialization)
contains the shared library [oracle-v1](../oracle/jass/lib/oracle-v1.j) followed by
one case file from [oracle/jass](../oracle/jass/). The map header stays empty.
(Correction during authoring: the header was the first plan, but World Editor then
marks the map as requiring the expansion.) See
[phase-1-procedure.md](phase-1-procedure.md) for authoring and capture.

- Build: `wc3-1.29.2-9231-x86`, the VM recorded in
  [the environment identity](../oracle/environment/wc3-1.29.2-9231-x86.json).
- Start: a timer event 0.5 s after map initialization calls the case's start function.
- Environment: normal game speed, locked; time of day 12, suspended; fog and black mask off.
- Units: unmodified `hfoo` Footmen of `Player(0)`, acquisition range 0.
  Unit `u0` starts at (0, 0) unless stated.
- Camera: `SetCameraPosition(384, 192)`, as in Phase 0.
- RNG: no seed is set. The effect of the seed is not tested.
- Sampling: callback 0 starts the 1000 s elapsed clock (experiment time zero), samples
  all watched units and runs the case's actions. A periodic timer then requests
  callbacks at the stated period. Each callback emits TICK, one SAMPLE per watched
  unit, then any actions/events. Every record in a callback uses one clock reading.
- Units of time: seconds from the clock's start. Distances: WC3 world units.
  Facing: degrees as returned by `GetUnitFacing`. Orders: `GetUnitCurrentOrder` IDs.
- Reals: `R2SW(value, 1, 6)` unless a field name ends in `_9` (9 decimals).
- Completion: END with `callbacks` equal to the requested count, a continuous sequence,
  one SAMPLE per watched unit per TICK, and the `PreloadEnd` envelope.
- Retention: at least three fresh-process captures per map, with the old output
  removed before every launch.

## Movement cases

"Callback 50" is the 50th periodic callback (requested 1.0 s at 0.02 s). Actions run
after that callback's samples; their effect can first appear at callback 51.

| ID / map | Question | Setup and actions | Callbacks |
|---|---|---|---|
| `MOV-0001` | Does an uncommanded Footman keep its position, facing and current order over the capture interval? | `u0` facing 0°; no orders | 250 at 0.02 s |
| `MOV-0002-r2` | Does Phase 0's straight move to (1000, 0) reproduce under the shared library, including arrival? | Phase 0 setup: `u0` (0,0) facing 0°, control `u1` (0,384) facing 0°; callback 0: `u0` move to (1000, 0) | 250 at 0.02 s |
| `MOV-0003` | How does a diagonal move differ from the straight baseline? | `u0` facing 45°; callback 0: move to (707.106781, 707.106781), distance 1000 | 250 at 0.02 s |
| `MOV-0004` | What movement trace and reported speed result when speed is set to 100? | `SetUnitMoveSpeed(u0, 100)` before WATCH; callback 0: move to (1000, 0) | 600 at 0.02 s |
| `MOV-0005` | What movement trace and reported speed result when speed is set to 522? | `SetUnitMoveSpeed(u0, 522)` before WATCH; callback 0: move to (1000, 0) | 250 at 0.02 s |
| `MOV-0006` | How do facing and displacement change when a moving unit is redirected by 90°? | callback 0: move to (1000, 0); callback 50: move to (x, y + 1000), from that callback's position | 250 at 0.02 s |
| `MOV-0007` | How do facing and displacement change when a moving unit is redirected by 180°? | callback 0: move to (1000, 0); callback 50: move to (x − 1000, y) | 250 at 0.02 s |
| `MOV-0008` | When does a replacement move order interrupt the previous trajectory? | callback 0: move to (1000, 0); callback 50: move to (500, 0), collinear and nearer, so no turn is requested | 250 at 0.02 s |
| `MOV-0009` | How does a stationary unit initially facing away from its destination begin moving toward a target behind it? | `u0` facing 180°; callback 0: move to (1000, 0) | 250 at 0.02 s |
| `MOV-0010` | What happens to position/facing/order after a moving unit receives stop? | callback 0: move to (1000, 0); callback 50: immediate `stop` | 250 at 0.02 s |

Observables: SAMPLE X, Y, facing and order for every callback; WATCH reported and
default move speed; ACTION acceptance and the exact target used.

MOV-0003 keeps the initial facing pointed at the target so that the diagonal axis is
the only change; MOV-0009 changes only the initial facing. MOV-0007 reverses a
*moving* unit, MOV-0009 turns a *stationary* one. MOV-0008 changes only the
destination, so any deviation before arrival would come from replacement itself.

The Phase 0 map and 20 captures stay unchanged. `MOV-0002-r2` is a separately named
revision under the same question and ID.

Single-unit maps have no `u1` control. `JASS-0001-p020` is the same single-unit
straight move at the same period, and serves as the one-factor baseline for
MOV-0003–MOV-0010. Comparing it with `MOV-0002-r2`'s `u0` tests whether `u1` matters.

## Timing case: JASS-0001

Question: how do requested sampling periods and elapsed-time clock precision affect
the movement observations we can recover?

All variants use the single-unit straight move: `u0` (0,0) facing 0°, move to
(1000, 0) at callback 0. Each callback also emits a `CLOCKS` EVENT reading two
auxiliary one-shot clocks of 100 s and 10 s, started in callback 0, plus the 1000 s
clock, the 10 s clock's remaining time and X/Y/facing, printed with 9 decimals.

| Map | Requested period | Callbacks | Requested span |
|---|---|---|---|
| `JASS-0001-p001` | 0.001 s | 500 | 0.5 s |
| `JASS-0001-p010` | 0.010 s | 500 | 5 s |
| `JASS-0001-p020` | 0.020 s | 250 | 5 s |
| `JASS-0001-p025` | 0.025 s | 200 | 5 s |
| `JASS-0001-p050` | 0.050 s | 100 | 5 s |

Observables: requested period; TICK clock readings (1000 s clock, 6 decimals);
auxiliary clock readings; callback count and sequence order when readings coincide;
the times at which unit state changes between consecutive samples.

Hypotheses to test, not results: (1) the coarse reported intervals in Phase 0
(0.019958/0.020020 s) come from the 1000 s clock's float resolution, so the 10 s
clock should report finer intervals; (2) unit state changes at a cadence independent
of the requested period. Completion: as above, for each variant; no single timer
period is accepted as the simulation quantum.

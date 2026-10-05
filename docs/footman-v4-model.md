# footman-v4 movement model

footman-v4 reproduces WC3 1.29.2 (9231), x86 32-bit (`wc3-1.29.2-9231-x86`), Footman
movement **bit for bit** on every retained capture it is compared with. It keeps
footman-v3's cadence: 30 ms logical updates from 10 ms, 5 ms frames, the 60° propulsion
window, 0.6 rad turns, the facing smoother and the map-corner frame. It replaces
v3's double-then-truncate emulation with the game's own float32 arithmetic and fixes
three rules that v3 lacked. Results: [footman-v4-results.md](footman-v4-results.md).

## Provenance

The arithmetic and update order come from static analysis of the retail
`Warcraft III.exe` (the hashed file in the [environment
record](../oracle/environment/wc3-1.29.2-9231-x86.json)). Every rule was then checked
against the WC3 captures. Those captures are the authority, and the analysis only proposed rules.

- **No game code or data is in the repository.** [SoftFloat.cpp](../src/core/SoftFloat.cpp)
  is an independent C++ implementation of the observed behaviour.
- **Lookup tables are generated, not copied.** Each of the four retail tables
  (reciprocal, sine, arccosine, arccosine near 1) is produced by a closed-form
  formula. During development every entry was compared with the executable and all matched exactly.
  Nothing from the executable is read at build or run time.
- **Retail function addresses** below are research references only, so the analysis can be repeated.

The emulator was first written in Python (outside the repository). The C++ port was compared with it
on 50,000 random cases with zero differences. [world_tests.cpp](../tests/world_tests.cpp)
pins fixed vectors.

## Arithmetic (`wc3::sf`)

Values are IEEE-754 binary32 bit patterns. Host floating point is used only for comparisons, as retail does.

| Operation | Behaviour | Retail |
|---|---|---|
| add / sub | 24-bit mantissas with one guard bit; the smaller operand is aligned with an arithmetic shift, so its rounding goes toward −∞; result truncated | `0x9a01c0` / `0x9a00b0` |
| mul | Truncating 24×24-bit product | `0x99ffe0` |
| recip, div | 1024-entry table plus linear interpolation; `div(a, b) = a·recip(b)`, except `a == b` gives 1 | |
| sqrt | 16-bit integer square root of the mantissa; biased high (about 1.5e-5 relative in the near-axial cases examined) | `0x9a20a0` |
| sin / cos | Angle × 2²⁰/2π, truncated to an integer; 1024-entry quarter table interpolated with weight `byte/255` | `0x9a1da0` / `0x9a0fe0` |
| acos | 1024-entry table; near 1, a 138-entry table indexed by the leading zeros and next three bits of `1 − x` | |
| pow, exp, log, fmod, atof | As retail (rational/polynomial approximations; atof is the game's decimal parser) | |
| Angle(v, L) | `≤ 1e-5 → 0`; `acos(div(x, L))`; `2π − a` when `y < 0` | `0x998640` |
| angle_to(target, current) | `d = current − target`, then wrapped into [−π, π] | `0x8a19b0` |
| wrap | fmod by 2π, then add 2π if negative | `0x8aead0` |

Near-axial travel has `L = sqrt(dx² + dy²)` up to 1.5e-5 relative above `|dx|`. The
cosine passed to `acos` is then a few hundred ulps below 1, and the angle comes out
0.3–0.4° off axis. This is footman-v3's unexplained "heading noise", and it is
deterministic arithmetic.

## Update rules

At each update (`0x8aa740` → `0x8b00c0` → `0x8aeb50` → `0x8b01c0`):

1. **Integrate** `pos = add(pos, mul(vel, dt))`, where `dt` is the movement clock
   difference since the last integration (`0x8bc740`).
2. **Heading.** While moving, the current heading is re-derived from the velocity:
   `h = Angle(vel, |vel|)` if `|vel| ≥ 4e-7`, otherwise the stored heading. *(New in
   v4. v3 carried the previous update's heading.)*
3. **Arrival** if `distance ≤ 15.5` (16 before MOV-0018): order ends, velocity 0, stored heading and facing
   target `= wrap(h)`.
4. **Steering:** `err = angle_to(Angle(target − pos), h)`, zeroed if `|err| < 2e-7`;
   `hu = add(h, ±min(0.6, |err|))`. Speed is used only if `|err| ≤ mul(60, π/180)`.
5. **Velocity** (`0x8b01c0`, applied through `0x8bbc50`):
   `vel = add(vel, sub(speed·(cos hu, sin hu), vel))`. Zero it if `|vel|² < 2e-7`.
   Scale it by `mul(speed, recip(|vel|))` if `|vel| > speed`. The facing target is
   `Angle(vel)` when `|vel|² ≥ 4e-7`. With no speed: velocity 0, and the stored
   heading and facing target are `wrap(hu)`.
6. **Facing smoother** (v3's law in retail arithmetic): `fv += ±0.07`; cap
   `min(0.2, |err|)`, times `(|err|/0.2)^0.25` below 0.2; snap when `|err| < 0.001`.
   Constants come from `atof` of the decimal strings.

**Orders.** A new move order or stop halts the unit immediately. It integrates, stores
`Angle(vel)` as its heading if moving, and zeroes the velocity. *(New in v4.)* A stop
processes its facing at the next update.

**Exposure.** `GetUnitX/Y` returns `pos + vel·(clock_now − clock_last)` without
storing it. The facing reading is `mul(f, 180/π)`.

## Unit pathing

Retail's movement library (NIpse in `Warcraft III.exe`) keeps every unit's footprint
in a grid of 32-unit cells from the map corner. The rules below were read from the
retail code; the points marked *interpreted* were chosen among readings the code
allows, by the captures (see [rule status](#rule-status)). With one unit the
pathing only plans a straight route, so MOV-0001–0010 are unaffected.

- **Footprint** (`0x8bc900`, `0x801930`): a Footman (collision class 1, `0x8a8220`)
  covers the 2×2 cells `{fx−1, fx} × {fy−1, fy}`, `f = floor(position / 32)`. It is
  re-registered when the unit integrates, so a unit not yet processed this update
  still covers last update's cells.
- **Order of processing** (*interpreted*): the most recently ordered unit updates first.
- **Planning** (`0x8a6cc0` → `0x8bd560`) happens at the unit's first update after an
  order. Later replans need 10 updates since the last plan (`+0x7c`); a unit waiting for
  one holds. Planning uses A* over cells (`0x8bfce0`, `0x8bf8b0`, `0x8c0890`, `0x8c0ae0`):
  - A node is a cell. A move to one of its 8 neighbours is open when the cells it newly
    covers are free (`0x8be080`: a ring of 12 cells and one mask per move).
  - Straight moves cost 15 and diagonal ones 21. The heuristic is `0x8bda00`'s integer
    distance estimate. The open list is a 1-based binary heap with stale entries
    skipped by version (`0x8a3090`, `0x8a2d20`); it decides between equal paths.
  - Units with a nonzero velocity are not obstacles (*interpreted*: cell tests skip
    agents flagged `0x60000000` unless `+0xce` is set, and only a few callers set it).
  - If the search never meets an occupied cell (`+0xcd`), the unit walks straight at
    the target. Otherwise it follows the path's cell centres.
  - An unreachable target ends the route at the first-found node nearest it. That
    partial route is replanned on arrival, holding that update.
- **Waypoints** (`0x8a6ed0`, `0x8a7ac0`, `0x8a8b40`): a waypoint is reached within
  0.49 cells (15.68). The unit then skips to the last following waypoint it can reach
  in a straight line. The straight-line test steps one cell at a time and checks the
  cells each step newly covers. Its first step compares against cell (0, 0) rather than
  the start cell, so it always checks the north-east L of the swept box.
- **Probe** (`0x8a5f30`, walker `0x8bea00`): each update the unit checks the cells it
  would newly cover one cell ahead (less if the waypoint is nearer). The probe sees
  all units, moving or not (`0x8a8090`):
  - **No unit in the way:** the unit moves.
  - **A moving unit that is not itself held for another:** if its squared speed is at
    least this unit's, this unit holds 4 more updates (5 in all). Otherwise that unit
    holds 20 and this one carries on down the list. Equal nominal speeds are decided
    by ulps of the soft-float velocities.
  - **Only stationary or held units:** the unit drops its route and holds. It replans
    when the 10-update limit allows.
- **Steering while held** (`0x8b0b90`, `0x8a5760`): speed is 0 and the heading still
  turns. It turns toward the waypoint on the update a moving unit is found, and
  toward the order target otherwise.

Positions enter these tests as float32 values evaluated in double; retail evaluates
them in float32. Only a value within an ulp or so of a cell boundary could differ (P1).

## Clocks

- **Movement clock:** one value per 5 ms frame, `c₀ = 0.5 s`,
  `c_{n+1} = add(c_n, 0.005f)`. Its binade sets how much each frame's step is
  truncated, so `dt` drifts. The 20 ms fixtures admit a start between about 0.496 and
  0.505 s. The library clock below admits only exactly 0.5.
- **Library clock** (`TimerGetElapsed` in [oracle-v1](../oracle/jass/lib/oracle-v1.j)):
  a periodic timer's scheduled time advances by `add(t, period)` from 0.5 s. Elapsed
  time on a one-shot timer of length `D` is `sub(D, sub(add(0.5, D), t))`. This is
  emulated in the runner ([Cases.cpp](../tools/wc3test/Cases.cpp)), not the engine,
  and is declared in each v4 trace's `library_clock` parameter.

## Rule status

| Rule | Status |
|---|---|
| Arithmetic, tables, update order and constants above | **Inferred** from retail code, then confirmed bit for bit by every retained capture |
| Stop radius 15.5, inclusive | **Fitted**: [MOV-0018](mov-0018.md#fitted-intervals) bounds it to [14.607, 15.90); MOV-0001–0010 agree with any value there. Not read from game data. |
| Unit pathing (above) | **Inferred** from retail code. Reproduces all 26 two-Footman captures (MOV-0018–0021) exactly. Those captures predate the analysis and guided it, and the processing order and the meaning of the `0x60000000` flag were chosen to fit them. Supersedes the fitted heuristics of [MOV-0018](mov-0018.md#model)–[MOV-0021](mov-0021.md#results). Not yet tested on a pre-registered capture. |
| Movement clock start 0.5 s | **Inferred**: the only start (of those tested) that reproduces every library-clock reading |
| Which frame, and which side of an update, a callback observes | **Partly unexplained.** See the [results](footman-v4-results.md#sampling-order). The 20 ms runner rule (after the update at step 20k) is exact for all fixtures |
| Speed clamp 150–400 | **Observed** endpoints, unchanged |
| An exact reversal | Never exercised, as in v3 |

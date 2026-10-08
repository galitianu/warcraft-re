# Client v1: interactive Footman (issue #31)

Milestone 1, first client increment ([roadmap](next-roadmap.md#first-client-increment)).
**Question (P3):** can real move/stop input control the measured footman-v4 world
while rendering leaves simulation outcomes unchanged?

Placeholder geometry (blue cylinders on a flat green grid) establishes interaction
only. It claims **no Warcraft III visual fidelity**, and nothing here was captured
from WC3: the movement itself is footman-v4, graded by the existing fixtures.

## Boundary

| Layer | Files | Depends on |
|---|---|---|
| Simulation | `src/core/World.*` (+ `World::snapshot()`, every field as bytes for exact comparison) | nothing |
| Commands | `src/core/Session.*` in `wc3world` | World |
| Client state | `src/client/View.*` (`wc3view`): `Pacer`, `Camera`, `pick`, `Controller`, `unit_views` | const World / Session |
| Window | `src/client/main.cpp`, `SmokeInput.mm` (`wc3client`, optional) | raylib, Cocoa |

- A **command** records simulation time (µs), a stable sequence number, the entity
  (unit index in creation order), the order (`move`/`stop`) and a move target
  (float32 bits). `Session::submit` stamps live input with the current time and
  the next sequence; `Session::schedule` queues recorded commands. The single
  `Session::advance_frame()` applies every due command in sequence order and then
  simulates one 5 ms frame (footman-v4's exposure period, the frame at which the
  scenario runner issues orders), so live input and replay share one path.
  Equal-time commands apply in sequence order: a move then a stop in the same
  frame leaves the unit idle; a stop then a move leaves it moving.
- **Wall time** enters only `client::Pacer`, which converts elapsed µs into whole
  frames, carries the remainder, and drops wall time beyond 20 frames (100 ms) per
  render so a stall slows the game instead of changing it. Simulation time is
  always frame count × 5 ms; the 1 ms step and footman-v4 cadence are unchanged.
- **Camera, picking, selection and drawing** read `const World&`/`const Session&`.
  Within one render frame the client reads input in a fixed order (left click,
  right click, `S`); raylib does not expose the order of events inside one poll.
- Recordings (`*.rec`) are canonical text (`wc3-command-recording 1`) with the
  scene (`flat-footmen-3`: Footmen 0/1/2 at x = -192/0/192, y = 0, facing 90),
  model, seed, frame period, commands and end time. The live client also writes
  `*.checkpoints`: SHA-256 of `World::snapshot()` every 1 s of simulation and at
  the end, computed while playing.

## Replay check

`wc3replay RECORDING [--live CHECKPOINTS] [--json REPORT]` replays headlessly (frames
back to back) and through the client's render loop under three named wall-clock
schedules: **30 Hz** (33333/33333/33334 µs), **60 Hz** (16666/16667/16667 µs) and
**irregular** (repeating 7000, 41000, 16667, 1000, 0, 250000, 3000, 25000, 9999,
33334, 4999, 5001 µs: sub-frame, zero, multi-frame and capped stalls). Every
render frame pans/zooms the camera, picks a unit, updates selection and builds the
draw list, and fails if the snapshot changed. Version 2 snapshots identify RNG
state by its seed and draw count, which uniquely
determine the implementation mt19937 stream; they avoid standard-library-specific
engine insertion text. This does not establish WC3 RNG compatibility. Snapshot
hashes are compared at
every whole simulated second and at the end; applied commands and acceptance
must also match. With `--live`, the live client's own checkpoints are compared too.
Exit 0 only if all are identical. CTest runs it on the retained recording
(`client_replay_0001`, `client_replay_0002`, using verified portable v2 checkpoints).
`session_tests` covers equal-time ordering, live versus
replay equality frame by frame, validation and presentation isolation.

## Pre-registered expectations (before the retained run)

Committed before `results/client-v1/live-0001.*` was recorded. A non-retained trial
run of the same script on the same machine was used to debug the screenshot path.

1. In the smoke run, the selected Footman moves toward each right-click point, `S`
   halts it part-way, and a right-click plus `S` in one render frame produces two
   commands with the same time, the stop having the later sequence, after which
   the Footman stays idle.
2. All three render schedules and the live checkpoints are identical to the
   headless replay at every checkpoint (exact bytes; no tolerance).
3. Existing movement, 32 collision fixtures and P1 gates are unchanged.

## Smoke procedure

Build (macOS ARM64; raylib 5.5 is found or fetched by CMake into the build tree):

```sh
cmake -S . -B build-client -G Ninja -DCMAKE_BUILD_TYPE=Release -DWC3_CLIENT=ON
cmake --build build-client --target wc3client wc3replay
```

**Manual (physical mouse/keyboard):** run `build-client/wc3client --record
local/client/manual --screenshots local/client/shots`. Left-click the middle
Footman (green ring appears, HUD shows `selected: Footman 1`), right-click north of
it (green X, it turns and walks; HUD order `move`), press `S` part-way (it halts,
order `none`). Pan with arrows or middle-drag, zoom with the wheel or `+`/`-`;
click empty ground to deselect. `F12` saves a screenshot; `Esc` quits and writes
the recording. Then `build-client/wc3replay local/client/manual.rec --live
local/client/manual.checkpoints` must print `PASS`.

**Scripted:** `wc3client --smoke tools/client/smoke-v1.txt --screenshots DIR --record
BASE` performs the same steps. It posts Cocoa `NSEvent`s into the client's own event
queue, so they travel Cocoa → GLFW → raylib → `Controller` exactly like physical
input (no accessibility permission needed, nothing posted to other applications).
Targets are aimed through the live camera (`@N` = Footman N's body). The HUD labels
such runs `SMOKE RUN`. GLFW finds no monitor while the display sleeps; wake it
first (`caffeinate -u -t 120`).

## Results

[Evidence](../results/client-v1/README.md). Run 0002 met expectation 1: select,
move, a part-way stop, and an equal-time move+stop (2.905 s, sequences 4 and 5)
after which Footman 1 stayed idle. Run 0001 did **not** show a part-way stop:
exporting video frames stalled rendering and the pacer cap stretched each scripted
wait, so the unit arrived first. That was a scripting/evidence problem, not a
simulation difference. Expectation 2 held for both runs: 30 Hz, 60 Hz, irregular
and live-client checkpoints are identical to the headless replay (23 and 7
checkpoints). Expectation 3 held: native ARM64 Release `tools/run_ci.py --archive` passes.

**Limits.** The screenshots come from scripted Cocoa events, not hand-operated hardware.
They are macOS ARM64 only; no Windows/Linux window was run. Within one render frame,
input order is fixed (left, right, `S`). No render interpolation is used (units
draw at the latest 5 ms frame). Box/group selection, path display, formations,
assets, combat and audio are out of scope.

**Portable snapshot revision.** The original hosted Linux jobs failed only the two
live-client comparisons, at time zero: their render schedules matched headless,
and all protected gates passed. `std::mt19937` insertion text differs between
libc++ and libstdc++. Snapshot/checkpoint v2 encodes the seed and number of draws
instead. The original `.checkpoints` and replay reports remain unchanged. Each
`.portable.checkpoints` is derived only after reconstructing and verifying every
original live hash on macOS/libc++; [migration reports and reproduction](../results/client-v1/README.md#portable-snapshot-revision)
retain both digests. These are verified format conversions, not fresh live runs.
Legacy checkpoint files are explicitly rejected by the v2 replay reader. The
client now records v2. Native validation passes; revised hosted CI is pending the
controller. No simulation mechanics or fixture tolerances changed.

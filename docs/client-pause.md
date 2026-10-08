# Client pause and diagnostics overlay (issue #38)

Milestone 1 follow-up ([roadmap](next-roadmap.md#follow-up-client-increments)).
**Question (P3):** can a player pause and resume the Footman scene, inspect and
queue orders while paused, and read optional diagnostics, without paused wall time
or presentation changing simulation outcomes?

This is client pacing/presentation only. Nothing here measures or claims WC3's own
pause semantics; no WC3 capture is involved.

## Pause rules

- **Space** toggles pause. Pause lives in `client::Pacer` (`paused`, `resuming`);
  it is not a `Session` command and never reaches the recording. Headless replay
  needs no pause event: `wc3-command-recording 1`, `wc3-checkpoints 2` and
  `wc3-routes 1` are unchanged.
- **Input poll order** within one render is fixed: left button (press/motion/release),
  right click, `S`, Space, F3, camera. Commands are stamped with the simulation time
  at the poll, so their position relative to Space does not change their stamps.
  Pause/resume take effect at that render's pacing step.
- **Pausing render:** simulates nothing and drops its own wall interval (at most one
  render interval, e.g. ~16.7 ms at 60 Hz). A command issued in the same poll as the
  pause therefore stays pending, like any command issued while paused.
- **Paused renders:** `frames_for` returns 0 and discards the elapsed time, however long.
- **Resume render:** its interval was spent paused, so it is also discarded and
  simulates nothing. Simulation restarts with the next render's own interval: no
  catch-up burst.
- **Fractional remainder:** the sub-frame `carry_us` is kept unchanged across the
  pause and continues afterwards, so running wall time is paced exactly as if the
  paused interval had been cut out. Repeated toggles within one render net out
  (an odd count pauses); resume-then-pause stays paused; resume while running is a no-op.
- **While paused:** selection, box/shift gestures, camera pan/zoom, route inspection,
  F3 and screenshots all work. Move/stop submit ordinary `Session` commands at the
  frozen time with increasing sequences. They stay pending (HUD `queued`, route
  `pending`, banner `N orders queued; applied on resume`) and apply in sequence
  through `Session::advance_frame` at the first resumed frame.

## Diagnostics overlay

**F3** toggles the overlay (hidden at start). `client::diagnostics` builds its lines
from `const Session&`, `const Controller&` and the caller's FPS/pause state: simulation
time and frame, PAUSED/running, render FPS, submitted/applied/pending command counts,
last command, each selected unit's order, route state and pending command, and the
shared-target limitation. It sits bottom-left above the controls; 14 px below 1100
window points wide, 16 px otherwise.

With diagnostics hidden the player HUD keeps the selection with each unit's order
(and `queued`), the focus unit's route state, destination/route/ring feedback, the
`PAUSED` banner with the queued count, and two lines of controls. When more than one
unit is selected an orange line states **every unit gets the same target; WC3
group assignment/formations are unmeasured, a likely P3 difference** (issue #36).

Supported window sizes for legibility: the default 1280×720 and 960×540
(`wc3client --window 960x540`).

## Checks

- `session_tests`: pacer pause with a sub-frame remainder, 1000 long paused intervals,
  resume discard, no catch-up, repeated toggles; a paused two-unit move then stop
  queued at equal time across 40 paused renders with camera/selection changes and
  diagnostics on/off (world, time and applied count unchanged), application in
  sequence at the first resumed frame, the group idle where it froze, and recording
  replay without any pause event.
- `wc3replay` adds `render-30hz-paused`, `render-60hz-paused` and
  `render-irregular-paused` for every recording: the named schedules with renders
  5–13 of every 37 paused and render 14 resuming, each frozen render reporting
  2.5 s of wall time. Frozen renders must simulate nothing and leave carry, time,
  applied commands and snapshot unchanged; all checkpoints, applied commands and
  acceptance must equal headless. Every render also builds diagnostics both ways.
- `wc3replay --observations` checks a smoke run's `observe` lines: the session
  rebuilt from the commands submitted by then, simulated to the observed time, must
  reproduce its applied and pending counts and snapshot digest; consecutive paused
  observations must share time, applied count and digest, with nondecreasing pending.

## PAU-0001 pre-registered smoke expectations

Permanent ID PAU-0001, checked unused in the repository and issues; no retail
capture. Script [`tools/client/smoke-pause.txt`](../tools/client/smoke-pause.txt),
seed 1, native macOS ARM64 Release client, scripted Cocoa events (not physical
input). Run 0001 at 1280×720 and run 0002 at 960×540, same script. Two non-retained
trial runs (one per size) were used to debug the overlay layout before this commit.

1. Box selection picks Footmen 0 and 1; a right-click moves both (sequences 1–2,
   one time). Space pauses part-way; every paused observation (start, diagnostics on,
   after camera/selection changes, after queuing, before resume) shows the same
   simulation time, applied count 2 and snapshot digest over more than 80 renders.
2. While paused: panning/zooming and selecting Footman 2 alone, then 0+1 again,
   changes no simulation state. A right-click and `S` queue moves then stops for
   0 and 1 at the frozen time, sequences 3–6; pending goes 0 → 4, applied stays 2.
   Screenshots show the PAUSED banner, `queued` markers and pending route with
   diagnostics on and off.
3. Resume: the resume render simulates nothing; a few renders later all four queued
   commands are applied (applied 6, pending 0) and 0 and 1 are idle where they froze.
   No catch-up: the first running observation is within a few frames of the frozen time.
4. A new move (sequences 7–8) is stopped part-way (9–10); the run continues long
   enough after resuming that all commands are applied before final evidence.
5. `wc3replay --live --routes --observations` matches headless, the 30 Hz/60 Hz/
   irregular schedules and their paused variants, all live checkpoints, displayed
   routes and observations exactly. Text is legible and non-overlapping in both
   overlay states at both sizes. Existing movement/collision/P1 gates and retained
   client recordings pass with unchanged references and tolerances.

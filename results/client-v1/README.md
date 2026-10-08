# Client v1 evidence (issue #31)

Design, procedure and pre-registered expectations: [docs/client-v1.md](../../docs/client-v1.md)
(committed in `a3bcd6d` before these runs). Placeholder geometry: interaction only,
no Warcraft III visual fidelity; no WC3 capture is involved.

**Environment.** Apple M4 Mac, macOS (Darwin 27.0.0) ARM64, AppleClang Release,
raylib 5.5 (CMake FetchContent, SHA-256 `aea98ecf…e258e`), window 1280×720 points
on a 2× display. `wc3client --smoke tools/client/smoke-v1.txt`: Cocoa `NSEvent`s posted to
the client's own queue (Cocoa → GLFW → raylib → `Controller`), aimed through the live
camera. These are **scripted OS-level events, not hand-operated hardware**; the manual
procedure in the design doc covers physical input. The display had to be woken
(`caffeinate -u`) because GLFW reports no monitor while it sleeps.

| Run | Files | Render | Sim end | Commands (equal-time) | Notes |
|---|---|---|---|---|---|
| 0001 | `live-0001.*`, `screenshots-0001/`, `smoke-0001.mp4` | ~12 fps (every other frame exported as PNG for the video) | 21.985 s | 6 (2) | Stalls kept the 20-frame pacer cap engaged, so each scripted wait covered more simulation: Footman 1 had **already arrived** (0, 631.76) before `S`, so this run does **not** show a part-way stop. Retained as a heavy-stall replay case. |
| 0002 | `live-0002.*`, `screenshots-0002/` | 61–79 fps (no frame export) | 5.275 s | 6 (2) | Shows every expected behaviour; the primary visual evidence. |

Run 0002 screenshots: `02` Footman 1 selected (green ring) → `03` moving north to the
green X → `04` `S` at 1.350 s, halted part-way at (0.00, 240.29), order `none` →
`05` moving to (420, 320) → `06` right-click plus `S` in one render frame, both at
2.905 s (sequence 4 move, 5 stop): it stays at (218.56, 282.50), order `none` →
`07` Footman 0 selected and moving after arrow-key pan, wheel and `+` zoom → `08` an
empty-ground click clears the selection.

## Replay comparisons

`build-dev/wc3replay live-000N.rec --live live-000N.checkpoints --json replay-000N.json`
(also CTest `client_replay_0001/0002`). Exact SHA-256 of `World::snapshot()` at every
whole second and at the end; no tolerance.

| Run | Schedule | Render frames | Checkpoints | Result |
|---|---|---|---|---|
| 0001 | headless | – (4397 sim frames) | 23 | reference |
| 0001 | 30 Hz / 60 Hz / irregular | 660 / 1320 / 1076 | 23 each | **identical** |
| 0001 | live client (recorded while playing) | – | 23 | **identical** |
| 0002 | headless | – (1055 sim frames) | 7 | reference |
| 0002 | 30 Hz / 60 Hz / irregular | 159 / 317 / 258 | 7 each | **identical** |
| 0002 | live client | – | 7 | **identical** |

Every render frame of the scheduled replays also panned/zoomed, picked, selected and
built the draw list, with an unchanged snapshot (`presentation_checks` in the JSON).
Applied commands and acceptance matched the headless run.

**Negative controls** (not retained): changing one hex digit of the 1 s live
checkpoint reports `live-client: DIFFERS at 1000000`; delaying run 0002's stop
by one 5 ms frame (1.350 → 1.355 s) reports `DIFFERS at 2000000`; both exit 1.

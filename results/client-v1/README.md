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

`build-dev/wc3replay live-000N.rec --live live-000N.portable.checkpoints --json replay-portable-000N.json`
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

## Portable snapshot revision

The original PR head `0e6e7df98c20449fbf18ebff5670ab732def96fe` failed
[Linux GCC and Clang CI](https://github.com/galitianu/warcraft-re/actions/runs/37796034274):
`client_replay_0001/0002` first differ from the live client at **0 µs**, while
30 Hz, 60 Hz and irregular schedules all match headless. All protected movement,
32 collision and reviewed P1 gates pass. The aggregate fails because those two
CTest cases fail. macOS and Windows jobs pass.

The defect is in evidence serialization, with no observed WC3 gameplay difference:
`Random::state()` used standard-library engine insertion text. libc++ writes 624
MT words; libstdc++ also writes its cursor. Snapshot v2 instead records the seed
and consumed draw count, which uniquely define the full implementation mt19937
stream. RNG output and simulation mechanics are unchanged. A regression test pins
standard outputs, copy/draw-count behavior and detection of RNG consumption in a
world snapshot. Checkpoint files declare `wc3-checkpoints 2`; the reader rejects
legacy v1 instead of treating old digests as current. This serialization defect
is not a deferred P1 WC3 observation or a tolerance exception.

**Original evidence remains unchanged.** `live-000N.checkpoints`, `live-000N.rec`,
`replay-000N.json`, screenshots and video are retained. The migration helper
replays the same recording on the original macOS ARM64/libc++ scope, reconstructs
v1 bytes (old RNG insertion text and no v2 prefix), and requires **every original
live hash to match** before writing a portable checkpoint file for those same
states. It also requires the RNG to remain unconsumed, as in these recordings.
This verifies the complete original state, not just positions or order labels.
No live or WC3 recapture occurred. Portable files are derived evidence:

- [Run 0001 migration](migration-0001.json): all 23 original digests verified.
- [Run 0002 migration](migration-0002.json): all 7 original digests verified.
- [Run 0001 portable replay](replay-portable-0001.json) and
  [run 0002 portable replay](replay-portable-0002.json): every named schedule and
  converted live checkpoint identical, with exact SHA-256 comparison.

Reproduce from a native libc++ build (the helper deliberately refuses to migrate
on a library whose original snapshot bytes differ):

```sh
/usr/bin/clang++ -std=c++20 -Isrc -Itools/wc3test tools/client/migrate_checkpoints.cpp \
  build-dev/libmovement_cases.a build-dev/libwc3world.a -o local/client-migrate
local/client-migrate results/client-v1/live-0001.rec results/client-v1/live-0001.checkpoints \
  local/run-0001.portable.checkpoints > local/migration-0001.json
local/client-migrate results/client-v1/live-0002.rec results/client-v1/live-0002.checkpoints \
  local/run-0002.portable.checkpoints > local/migration-0002.json
```

The emitted bytes reproduce the committed migration reports and portable files.
Negative controls: tampering with a legacy hash causes migration to exit 1 before
creating an output; tampering with a portable hash or delaying run 0002's stop by
5 ms causes replay to exit 1. Native ARM64 Release CTest passes 6/6; the full
archival compatibility gate passes. The optional raylib client rebuilds with v2
recording output. New-head Linux/Windows and aggregate verification remain with
the controller's hosted CI gate; no cross-platform pass is claimed here.

# Pause and diagnostics evidence — PAU-0001 / issue #38

Design and predictions in [client-pause.md](../../docs/client-pause.md), committed
before these runs in `5d68241`. No WC3 capture is involved; nothing here measures
WC3 pause semantics.

## Retained runs

- Build: clean `5d68241`, native Release `-DWC3_CLIENT=ON`, Apple clang 21.0.0
  (clang-2100.3.34.2), CMake 4.4.4, Ninja, raylib 5.5 fetched by CMake. Binary SHA-256:
  `e3c648427b305b6bf5c7701d3d246e30a64fcc29e54adbe26aedf6bfafd05407`.
- Environment: macOS 27.0.1 (26A434), arm64, Retina (2× framebuffer). Local Mac
  desktop, not the Windows oracle VM. **Input is scripted Cocoa events** posted into
  the client's own queue ([script](../../tools/client/smoke-pause.txt)), not physical input.
- Run 0001, 1280×720 points: `build-client/wc3client --smoke tools/client/smoke-pause.txt
  --screenshots results/client-pause/screenshots-0001 --record results/client-pause/pause-0001`.
- Run 0002, 960×540 points: the same with `--window 960x540` and `-0002` paths.
- Per run: recording (`.rec`), live checkpoints, displayed routes, pause observations,
  stdout (`.log`), replay report (`replay-*.json`) and screenshots.

Run 0001 commands (run 0002 is the same sequence at 515000/715000/970000/1305000 µs):

| Simulation µs | Sequences | Units | Order | When |
|---|---|---|---|---|
| 555000 | 1–2 | 0, 1 | move (100.001167, 549.985168) | running |
| 770000 | 3–4 | 0, 1 | move (-299.993134, 399.973511) | **paused** |
| 770000 | 5–6 | 0, 1 | stop | **paused** |
| 960000 | 7–8 | 0, 1 | move (299.991486, 599.954651) | after resume |
| 1325000 | 9–10 | 0, 1 | stop (part-way) | running |

Target offsets from the scripted aims come from screen picking, not a WC3 difference.

## Pause observations

Run 0001 ([observations](pause-0001.observations)); columns are render frame,
state, simulation µs, submitted, applied, pending:

| Observation | Render | State | Sim µs | Submitted | Applied | Pending | Digest |
|---|---|---|---|---|---|---|---|
| paused-start | 74 | paused | 770000 | 2 | 2 | 0 | `f8fd43b1…` |
| diagnostics-on | 77 | paused | 770000 | 2 | 2 | 0 | `f8fd43b1…` |
| camera-selection | 99 | paused | 770000 | 2 | 2 | 0 | `f8fd43b1…` |
| queued | 123 | paused | 770000 | 6 | 2 | 4 | `f8fd43b1…` |
| before-resume | 157 | paused | 770000 | 6 | 2 | 4 | `f8fd43b1…` |
| resumed | 160 | running | 795000 | 6 | 6 | 0 | `42595787…` |
| final | 278 | running | 1980000 | 10 | 10 | 0 | `c11e67de…` |

The snapshot digest, time and applied count are identical across 83 paused renders
(74–157), including after the four queued commands. Space was processed at render
158 (resume render: no frames), so renders 159–160 simulated only 5 frames (25 ms)
after more than 80 frozen renders (the overlay showed 61–361 fps while paused): no catch-up. The live route log shows 02-moving was
drawn at 770000 µs, the same time as every paused frame, so the pausing render
simulated nothing. Run 0002 shows the same pattern at 715000 µs (renders 74–157 frozen;
resumed 735000 µs, applied 6, pending 0).

## Screenshot inspection

Run 0001 (1280×720): all 11 inspected. Run 0002 (960×540): 03, 04, 05, 06, 07, 09 and
11 inspected (both overlay states, paused and running); 01, 02, 08 and 10 were not
individually inspected.

| Screenshot | Observed |
|---|---|
| 02-moving | 0 and 1 ringed and moving, Footman 0's cyan route to the shared X, controls `Space pause` |
| 03-paused | PAUSED banner `no orders queued`, same frame as 02, route still shown, controls `Space resume` |
| 04-paused-diagnostics | panel bottom-left: `sim 0.770 s frame 154 PAUSED`, `submitted 2, applied 2, pending 0`, both units `move, route planned` |
| 05-paused-camera-selection | camera panned (units shifted right); only Footman 2 selected, `route none`; time still 0.770 s |
| 06-paused-queued | `(move, queued)` for 0 and 1, route `pending (no computed path yet)`, banner `4 orders queued; applied on resume`, panel `submitted 6, applied 2, pending 4`, `command pending` per unit |
| 07-paused-queued-hidden | overlay hidden; banner, queued markers, rings, X and shared-target line remain |
| 08-resumed | banner gone; 0 and 1 `(none)` idle where they froze (equal-time move then stop) |
| 09-new-move | 0 and 1 moving north-east, new route and X |
| 10-stopped | 0 and 1 idle part-way, route none |
| 11-later-diagnostics | panel `running`, `submitted 10, applied 10, pending 0`, both `order none` |

Text is legible and non-overlapping in both overlay states at both sizes (14 px
overlay at 960×540). The scripted `scroll 2` produced no zoom change discernible in
the screenshots; camera usability while paused is shown by the pan only. Zoom while
paused is exercised headlessly for world isolation, not visually confirmed here. Trial runs before `5d68241` were used only to
debug layout and are not retained.

## Verification

`wc3replay pause-000N.rec --live … --routes … --observations … --json replay-000N.json`:
PASS for both runs. Headless, 30 Hz, 60 Hz, irregular, the three paused variants
(3–5 pauses, 30–50 frozen renders each at 2.5 s reported wall time) and the live
client agree at every checkpoint, with identical applied commands and acceptance;
all 10 displayed routes and all 7 observations reproduce exactly. CTest gates
`client_pause_0001` and `client_pause_0002` retain these checks. The paused schedule
variants also pass on the earlier client-v1, route and selection recordings.

## Limits

Scripted input on macOS ARM64 only; no physical-input session and no Windows/Linux
window. Pause is a client pacing feature; WC3's own pause semantics are not measured
or claimed. Group orders still give every unit the same point (WC3 assignment and
formations unmeasured, likely P3). Placeholder geometry shows interaction only.

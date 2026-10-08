# Client route display evidence (issue #34)

Design and pre-registered expectations: [docs/client-route.md](../../docs/client-route.md)
(committed in `b6d5979`/`d72b4cb`, before this run). Placeholder geometry; no WC3
capture is involved and no Warcraft III visual fidelity is claimed.

## Run 0001 (retained)

- **Build:** `wc3client` at commit `d72b4cb` (clean tree), Release, `-DWC3_CLIENT=ON`,
  raylib 5.5 fetched by CMake; Apple clang 21.0.0, CMake 4.4.4. Binary SHA-256
  `1d807da6bf64a71a30c4be12d122710472fcd15d94f3c8615327d3e8659fcfaa` (local build).
- **Environment:** macOS 27.0.1 (26A434), arm64, 2560×1440 framebuffer, vsync.
- **Input:** scripted, not physical: `wc3client --smoke tools/client/smoke-route.txt
  --screenshots DIR --record route-0001` posts Cocoa `NSEvent`s into the client's own
  queue (Cocoa → GLFW → raylib → `Controller`). The HUD labels it `SMOKE RUN`.
- **Files:** [`route-0001.rec`](route-0001.rec) (commands), [`.checkpoints`](route-0001.checkpoints)
  (live SHA-256 of `World::snapshot()` v2 each simulated second and at the end),
  [`.routes`](route-0001.routes) (the selected route displayed with each screenshot),
  [`.log`](route-0001.log) (client stdout), [`replay-0001.json`](replay-0001.json),
  [`screenshots-0001/`](screenshots-0001).

Command stream (simulation µs, sequence, unit, order):

| Time | Seq | Unit | Order | Purpose |
|---|---|---|---|---|
| 400000 | 1 | 2 | move (450.007, 300.018) | unobstructed |
| 2210000 | 2 | 0 | move (200.001, −0.012) | straight line crosses idle Footman 1 |
| 2745000 | 3 | 0 | move (−99.998, 399.974) | redirect while moving |
| 3075000 | 4 | 0 | stop | part-way stop |
| 3225000 | 5 | 0 | move (−299.993, 499.984) | move, then deselect |

At most two units moved at once (Footman 2 had arrived before Footman 0's orders).
Live checkpoints: 0, 1, 2, 3, 4 s and 4.57 s (end).

## Screenshots and displayed routes

Each row is the route line the client logged as drawn (`route-0001.routes`).

| Shot | Sim time | Displayed route | Seen in the image |
|---|---|---|---|
| [02-unobstructed](screenshots-0001/02-unobstructed.png) | 0.570 s | Footman 2 `planned`, 1 waypoint: (450.007, 300.018) | straight cyan segment to the green X |
| [03-arrived](screenshots-0001/03-arrived.png) | 2.065 s | `none` | no route; Footman 2 idle at (440.15, 288.61), order none (inside the 16-unit stop radius) |
| [04-detour](screenshots-0001/04-detour.png) | 2.325 s | Footman 0 `planned`, 12 waypoints | cyan route bends south of Footman 1 along y = −48 to the X at (200, 0) |
| [05-detour-later](screenshots-0001/05-detour-later.png) | 2.595 s | `planned`, 8 waypoints | passed waypoints are gone; same southern line, unit leaving the start |
| [06-redirected](screenshots-0001/06-redirected.png) | 2.880 s | `planned`, 1 waypoint: (−99.998, 399.974) | single segment north to the new X; nothing of the old route remains |
| [07-stopped](screenshots-0001/07-stopped.png) | 3.225 s | `none` | unit idle part-way at (−73.52, 42.56), no route or X |
| [08-moving-again](screenshots-0001/08-moving-again.png) | 3.415 s | `planned`, 1 waypoint | straight segment north-west |
| [09-deselected](screenshots-0001/09-deselected.png) | 3.510 s | no selection, nothing logged | no ring, route or X while Footman 0 still moves |

The detour images were checked against the logged waypoints: the drawn polyline
starts at the unit and follows the cell-centre waypoints (−144, 16), (−112, 16),
(−80, −16), then (−48 … 176, −48) and (200.001, −0.012), not the straight line
through Footman 1. `wc3replay --routes` independently confirms every logged route
equals the headless model's route view at that time.

**Route changes.** The model can drop and replan a route while passing a blocker
(a headless trial of the same layout replanned about 0.59 s after the order and
showed `pending` for a few frames). In this run the redirect came 0.535 s after
the detour order, so no replan appears in a screenshot; the displayed route may
change during play and is a current plan, not a promise.

**Same-time submission.** `07-stopped` was drawn at 3.225 s; the next move (seq 5)
was submitted in a later render frame at the same simulation time. The routes log
records 4 commands known at that screenshot, and the replay reproduces `none`.

## Replay

```sh
build-client/wc3replay results/client-route/route-0001.rec \
  --live results/client-route/route-0001.checkpoints \
  --routes results/client-route/route-0001.routes --json replay-0001.json
```

PASS: 30 Hz, 60 Hz and irregular render schedules and the live checkpoints are
identical to headless at all 6 checkpoints, applied commands and acceptance match,
and all 7 displayed routes are identical. Every render frame built every unit's
route view and the selected route twice without changing the snapshot (route view
counts per schedule are in the JSON; no partial route occurs in this run, which
`session_tests` covers headlessly). CTest runs this as `client_route_0001`.

A non-retained trial on the same machine preceded this run (see the design doc).

## Limits

Scripted Cocoa events, not hand-operated hardware; macOS ARM64 only. A partial
route was not shown live (covered headlessly). No render interpolation. The route
is footman-v4's plan; WC3 does not display paths and this claims nothing about it.

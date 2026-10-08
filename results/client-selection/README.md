# Multiple selection evidence — SEL-0001 / issue #36

Design and predictions in [client-selection.md](../../docs/client-selection.md),
committed before this run in `42e66ff`; test correction in `20e79d4` changes no
client behavior. No WC3 capture is involved.

## Retained run 0001

- Build: clean `20e79d4`, native Release `-DWC3_CLIENT=ON`, Apple clang 21.0.0
  (clang-2100.3.34.2), CMake 4.4.4, raylib 5.5 fetched by CMake. Binary SHA-256:
  `cc363869bd81c5b1a526f5737c642fb8c12272ddbb2dd66a375ebde63ccaf117`.
- Environment: macOS 27.0.1 (26A434), arm64, 1280×720 window points,
  2560×1440 framebuffer. Input is scripted Cocoa events into this app's own queue,
  not physical input. This uses the local Mac desktop, not the Windows oracle VM.
- Command:
  `build-client/wc3client --smoke tools/client/smoke-selection.txt --screenshots
  results/client-selection/screenshots-0001 --record results/client-selection/selection-0001`.
- [Recording](selection-0001.rec), [live checkpoints](selection-0001.checkpoints),
  [displayed routes](selection-0001.routes), [stdout](selection-0001.log),
  [replay report](replay-0001.json), [screenshots](screenshots-0001/).

| Simulation µs | Sequence | Unit | Order |
|---|---|---|---|
| 640000 | 1 | 0 | move (100.001167, 549.985168) |
| 640000 | 2 | 1 | same move target |
| 640000 | 3 | 2 | same move target |
| 1050000 | 4 | 0 | stop |
| 1050000 | 5 | 2 | stop |

The exact target float32 bits are retained in the recording. Screen picking
introduces the displayed offset from the intended smoke aim (100,550); this is
client aiming, not an observed WC3 difference. Simulation end: 2760000 µs.

## Screenshot inspection

| Screenshot | Observed |
|---|---|
| [02-box-outline](screenshots-0001/02-box-outline.png) | held green outline covers all three bodies; selection commits on release |
| [03-selected](screenshots-0001/03-selected.png) | three green rings, all three IDs in HUD, route focus 0 |
| [04-group-move](screenshots-0001/04-group-move.png) | three moving orders, three rings, shared destination X and Footman 0's cyan route |
| [05-shift-removed](screenshots-0001/05-shift-removed.png) | Footman 1 has no ring; selected 0 and 2 still move |
| [06-group-stopped](screenshots-0001/06-group-stopped.png) | 0 and 2 idle part-way, route none and destination X gone; 1 continues north |
| [07-later](screenshots-0001/07-later.png) | 0 and 2 remain in place; 1 has advanced toward the shared target |

All images inspected. The HUD states the shared-point placeholder, unmeasured WC3
assignment and likely P3 difference. No group/formation or visual compatibility is
claimed. Stop occurs before units meet; no three-unit retail verdict is inferred.

## Verification

`wc3replay selection-0001.rec --live selection-0001.checkpoints --routes
selection-0001.routes --json replay-0001.json`: PASS. Headless, 30 Hz, 60 Hz,
irregular and live-client hashes match at all four checkpoints (0, 1 s, 2 s,
2.760 s). All five displayed routes match exactly. Applied commands and acceptance
also match across render schedules. `client_selection_0001` retains this CI gate.
The replay exercises shift selection and box gestures while checking snapshot
isolation each render frame; session tests cover the precise gesture rules and
equal-time move then stop for two units.

Native client CTest passes 8/8. Default headless native ARM64 Release
`python3 tools/run_ci.py --build build-ci --compiler /usr/bin/clang++ --config
Release --archive` passes, including movement 10/10, all 32 two-unit collision
fixtures, historical regression gates, archived capture validation and the known
P1 gates. This validates committed captures; it performs no fresh WC3 runs.
Existing fixtures/tolerances and recordings remain unchanged. Final clean-head
verification is recorded in the dispatch receipt; hosted CI remains the
controller's gate.

## Limits and next action

Scripted input, macOS ARM64 only; no physical-input play session or Windows/Linux
window tested. Three-unit movement and shared-target assignment are model behavior;
WC3 group targets/formations are unmeasured (likely P3, needs a future experiment).
Placeholder geometry establishes interaction only. Milestone 1 is not complete;
next client work is a bounded pause/diagnostic-overlay increment. Independent
review and hosted CI/integration belong to the dispatcher.

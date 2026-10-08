# Client multiple selection (issue #36)

**Question (P3):** can box and shift selection control several Footmen through
ordered per-unit commands without presentation changing simulation?

## Rules and boundary

`Controller` owns a sorted unique vector of unit indices, with no World ownership.
A press records screen coordinates and shift state. Euclidean displacement strictly
greater than 5 pixels latches a box gesture until release (even if the pointer
returns); exactly 5 pixels is a click. Selection commits on release. Plain clicks
use the existing nearest pick sphere, equal-distance ties favor the lowest index;
empty ground deselects. Shift-click toggles a hit, and empty shift-click preserves.
Plain boxes replace; shift-boxes union. Reversed corners work, boundary contact
counts, and zero-area boxes are empty. Box selection intersects the same 36-unit
pick spheres (centred halfway up the body) with the camera's infinite perspective
selection frustum, testing its interior, faces, edges and apex. It reads const
World through `wc3view`; screen rays/projection and gesture handling need no raylib.

Right-click and S submit one existing Session command per selected index ascending,
with the same simulation time and consecutive sequences. Recording format and
footman-v4 are unchanged. **Every unit gets the same target: a placeholder.
WC3 group target assignment/formations are unmeasured; likely difference P3,
not established, requiring a future WC3 experiment. No group or formation
compatibility is claimed.** Three-unit interactions are model behavior; the
protected retail pathing scope is 32 two-unit fixtures (issue #32 is separate).

All selected units have rings, destination X feedback and individual order names
in the HUD. Only the lowest selected index shows its read-only computed route.
Stop/arrival remove destinations and routes; deselection removes selected feedback.
The drag outline appears while the gesture is held. Geometry is placeholder only.

## SEL-0001 pre-registered smoke expectations

Permanent ID SEL-0001 was checked against repository IDs and current issue #36;
no retail capture is involved. Commit this design/script before retaining the run.
Script: `tools/client/smoke-selection.txt`, seed 1, three-Footman scene, native
macOS ARM64 client; scripted Cocoa events, not physical input.

1. A box covers all three bodies; the held outline is visible in 02-box-outline.
2. 03-selected shows three rings. Right-click issues moves for 0, 1, 2 at one
   time, sequences 1–3, to the same ground point near (100,550).
3. 04-group-move shows three moving orders and the lowest-index route.
4. Shift-click removes Footman 1; 05-shift-removed shows rings for 0 and 2 only.
5. S stops 0 and 2 part-way, sequences 4–5 at one time; 06-group-stopped clears
   their destination/route feedback. Footman 1 continues its existing move.
6. `wc3replay --live --routes` matches headless, 30 Hz/60 Hz/irregular schedules,
   all live checkpoints and displayed routes exactly. Headless gesture tests
   cover threshold/ties/union/body intersection, snapshot isolation and two-unit
   equal-time move then stop. Existing references and tolerances stay unchanged.

## Results

[SEL-0001 retained run 0001](../results/client-selection/README.md) meets expectations
1–5: the outline covers all three Footmen, three rings appear, all three move,
shift removes Footman 1, and the two remaining selected units stop part-way while
Footman 1 continues. The shared-target X overlaps by design; the HUD lists each
selected unit's current order and the cyan route belongs to Footman 0.
`wc3replay` matches all four live checkpoints and five displayed routes exactly
under all named schedules. The native Release client and default headless build
pass their CTests; native archival CI results are recorded with the evidence.

Limits: scripted Cocoa input only, macOS ARM64; no physical-input session or other
window platform tested. Shared targets and three-unit interactions are model
behavior, not WC3 compatibility. Milestone 1 remains open: pause and diagnostic
overlay are the next scoped client increments.

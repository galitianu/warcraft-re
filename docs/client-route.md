# Client: selected route display (issue #34)

Milestone 1's path-display gate ([roadmap](next-roadmap.md#follow-up-client-increments)),
extending [client v1](client-v1.md). **Question (P3):** can a player see the selected
Footman's currently planned route around another Footman, rather than a straight
destination line that crosses the blocker, while presentation leaves the measured
world unchanged?

This shows footman-v4's own plan as model feedback. It does **not** claim that WC3
displays paths, and a displayed plan does not promise where the unit will walk: the
model replans as blockers move. Placeholder geometry claims no visual fidelity.

## Boundary

- `wc3::Unit` exposes its existing plan read-only: `route()`, `route_index()` (the
  waypoint being steered for) and `route_partial()`. `Session::pending_for(unit)`
  reports a command due now but not yet applied (live input before the next frame;
  later scheduled replay commands do not count). Nothing else was added to the
  simulation; the route algorithm and command semantics are unchanged.
- `client::route_view(session, unit)` (in `wc3view`, no raylib) copies that plan:
  - `pending`: a command for the unit is due but unapplied, or its move has no plan
    yet (plans are made at the unit's next 30 ms update, or after a dropped route's
    replan wait). No path is shown: the old route would be stale.
  - `planned` / `partial`: the unit's displayed position, then the remaining
    waypoints from the cursor in traversal order. A partial route ends where the
    plan ends, short of a blocked target; no connection to the destination is drawn.
  - `none`: no move order is being carried out (idle, stopped, arrived), whatever
    inactive route data remains.
  `selected_route` gives the selected unit's view; deselection yields `none`.
- Building a view never plans, steps or mutates route state; the world is `const`.
- The client draws the route as a cyan polyline with waypoint dots, separate from
  the green destination X, an orange ring at a partial route's end, and a HUD line
  `route: STATE, N waypoints left`. The old straight unit→destination line is gone.
- With each screenshot the client appends the displayed route to `BASE.routes`
  (`wc3-routes 1`): `screenshot NAME SUBMITTED`, then (with a selection) one canonical
  `route TIME UNIT STATE N X Y ...` line in float32 bits. SUBMITTED counts commands
  submitted when it was drawn: a later render frame can submit a command at the same
  simulation time, which the client had not seen. `wc3replay REC --routes BASE.routes`
  rebuilds each such session headlessly (those commands, simulated to TIME) and
  requires the displayed route to equal its route view exactly.

## Checks

- `session_tests`: idle units have no route; an unapplied move, and an applied move
  awaiting its plan, are `pending` with no points; a detour around the idle Footman 1
  copies the world's waypoints from the cursor, starts at the unit, ends at the target
  and avoids the blocker; while a plan stands, remaining waypoints only drop from the
  front; redirect shows `pending` until the new plan, which ends at the new target;
  stop, arrival and deselection clear the feedback; a blocked target gives a
  `partial` route whose end differs from the target; 100 repeated view constructions
  leave the snapshot unchanged.
- `wc3replay`, every render schedule (30 Hz, 60 Hz, irregular): each render frame
  builds every unit's route view and the selected route twice, checks each copies the
  world's plan, and fails if the snapshot changed. Its JSON reports counts per state.

## Pre-registered expectations (committed before the retained run)

A non-retained trial on the same machine debugged the procedure: its `03-arrived`
screenshot came before arrival (wait lengthened from 110 to 170 render frames), and
its route log could not express a move submitted at a screenshot's own simulation
time in a later render frame (now recorded as SUBMITTED). Its detour image already
showed the route passing south of Footman 1.

Smoke script [`tools/client/smoke-route.txt`](../tools/client/smoke-route.txt) in the
three-Footman scene, at most two units moving, scripted Cocoa input (as client v1).

1. `02-unobstructed`: Footman 2 moving to (450, 300) shows `planned, 1 waypoints left`,
   a straight route to its destination. `03-arrived`: route `none`.
2. `04-detour`/`05-detour-later`: Footman 0 ordered to (200, 0) shows a `planned` route
   with several waypoints passing south of the idle Footman 1 rather than the straight
   line through it, ending at the destination X. The model may drop and replan the
   route while passing Footman 1 (headless trial: about 0.59 s after the order); if it
   does, a screenshot can show `pending` and this is reported, not hidden.
3. `06-redirected`: the route ends at the new destination (-100, 400); no part of the
   old route remains. `07-stopped`: route `none`, unit idle part-way.
4. `08-moving-again` shows a route; `09-deselected` shows none while the unit moves.
5. `wc3replay --live --routes` is PASS: 30 Hz, 60 Hz, irregular and live checkpoints
   identical to headless, and every logged displayed route identical to the replay's.
6. Existing movement, 32 collision fixtures, client recordings and P1 gates unchanged.

## Results

[Evidence](../results/client-route/README.md), run 0001, scripted Cocoa input on
macOS 27.0.1 arm64. Expectations 1, 3, 4 and 5 held: the unobstructed move showed a
straight one-waypoint route and cleared on arrival; the redirect replaced the route
with one ending at (−100, 400); the part-way stop and deselection cleared it; the
replay matched headless under all schedules, the 6 live checkpoints and all 7
displayed routes, exactly. Expectation 2 held: the detour route passed south of the
idle Footman 1 to the destination, following the model's waypoints; no replan fell
inside a screenshot in this run (one occurs in headless trials about 0.59 s after
the order), so a live route change is possible but was not shown. Expectation 6
held: native ARM64 Release `tools/run_ci.py --archive` passes with movement, 32
collision and P1 gates unchanged, CTest 7/7 including the two retained client-v1
recordings.

**Limits.** Scripted, not physical, input; macOS ARM64 only. No partial route was
displayed live (headless tests cover it). The route is model feedback, not
Warcraft visual fidelity or a WC3 behavior claim.

Multiple selection now uses the lowest selected unit index for route focus; see
[issue #36](client-selection.md). All selected units retain individual order and
destination feedback. The retained single-selection evidence above is unchanged.

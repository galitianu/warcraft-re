# HUM-0001: physical-input client validation preparation

Issue #44, P3 interaction gate; no new WC3 mismatch claimed. HUM-0001 was
unused in the repository and GitHub issue search before this design. The design
was committed (`c663358`) before the two sessions recorded below.

## Prediction and acceptance

On the integrated macOS ARM64 Release client, physical mouse/keyboard input should
exercise the existing controls below, visibly including zoom. The actual recording
must replay exactly against live checkpoints under headless, 30 Hz, 60 Hz,
irregular and all three paused schedules. Retained screenshot route logs must
also match. A replay pass cannot substitute for a missing/failed interaction.
Existing client CTests and native archival CI must pass without fixture/tolerance
changes. No WC3 capture, visual-fidelity or formation claim is made.

## Prepared procedure (one 1280×720 window, flat three-Footman scene)

From this worktree, after building:

```sh
build-client/wc3client --window 1280x720 --record local/client-human/human-0001 --screenshots local/client-human/shots
```

Use physical input only; no `--smoke`, UI automation or synthetic input. Press
F12 (Fn-F12 if needed) at each useful state; screenshots contain only the client.
While paused, screenshots share simulation-time filenames: take only one combined
paused-state screenshot to avoid overwriting it, or preserve each file separately
before taking another. Do not generate scripted-only observation records.

1. Click the middle Footman. Right-click distant ground, capture its route and
   destination with F12, then press S part-way and capture the stopped state.
2. Drag a box around the three Footmen; capture the selection. Shift-click one
   to remove it and again to add it; capture each state. Right-click a distant
   point for a group move, then S part-way; capture move and stop.
3. Pan using arrows or middle-drag. Capture before and after visibly zooming with
   the wheel; also try +/- and report which worked. Click empty ground to deselect.
4. Select a group and move it. Press Space part-way. While paused, right-click
   a new destination, then press S. Toggle F3 on and capture the paused banner,
   queued count and diagnostics. Toggle F3 off, resume with Space, then capture
   the stopped group. Allow a second to run before Esc saves the session.
5. Report actual input device/method, each omitted or failed step, wheel and +/-
   results, and subjective responsiveness/readability separately from artifacts.

After the human session:

```sh
build-client/wc3replay local/client-human/human-0001.rec --live local/client-human/human-0001.checkpoints --routes local/client-human/human-0001.routes --json local/client-human/replay.json
```

Inspect screenshots, retain suitable evidence and the operator report, and assess
each interaction explicitly. Physical input and operator availability are required;
if absent, preserve preparation and return BLOCKED. Milestone 1 remains open.

## Preparation verification / handoff (16 October 2026)

Source `c66335858b4ac873fed03d3679a221e8abb063f3` includes current main
`d9adfa63c302e8308748741c9da8ea9e35a48f8d`. The retained
[preparation identity](preparation.json) was rechecked against the actual ARM64
binary and OS. Rebuild required no work; client CTest passed 10/10. Native
AppleClang ARM64 Release `tools/run_ci.py --archive` exited 0: CI PASS,
155 Python tests passed, protected movement/collision and known P1 gates held,
and MOV-0023's four known P3 compatibility failures remained explicitly gated.
Full local report: `build-ci/ci/reports/result.json`; its digest is in the identity.
No simulation source, reference or tolerance changed. Hosted CI remains with
the controller; Windows is disabled/unobserved.

**BLOCKED:** operator availability was requested through the question tool but
no human session was supplied during this stage. No physical-input recording,
live checkpoints, screenshots, operator observations or human replay result
exists. None of the requested human interactions, including visible zoom, is
claimed observed. This is an unmet P3 interaction-validation gate, not a newly
observed product defect. Milestone 1 remains open. The exact next action is to
arrange the operator's availability, launch the command above, follow the
procedure and retain/inspect the real artifacts before replay and assessment.

## Sessions (18 October 2026)

Operator: the project owner, at the Mac mini (macOS 27.0.1, arm64), physical
mouse/trackpad and keyboard. No `--smoke`, UI automation or synthetic events.
Binary rebuilt from `da8cb5b` with the prepared options; its SHA-256 equals
[preparation.json](preparation.json) (`e3c64842…`). Window 1280×720 points
(2560×1440 Retina screenshots). The first launch attempt crashed (exit 139,
`GLFW: Failed to determine Monitor`) while the screen was locked; after unlocking,
both sessions ran normally. That crash is outside this gate and not investigated.

| Session | Commands | Stops | End | Checkpoints | Displayed routes | Screenshots |
|---|---|---|---|---|---|---|
| [human-0001](human-0001.rec) | 31 | 0 | 34.82 s | 36 | 0 | none taken |
| [human-0002](human-0002.rec) | 32 | 7 | 277.77 s | 279 | 7 | 20 taken, 7 retained |

`wc3replay --live … --routes … --observations …` ([0001](replay-0001.json),
[0002](replay-0002.json)): headless, 30 Hz, 60 Hz, irregular and the three paused
schedules are **IDENTICAL** to the live client's checkpoints in both sessions;
session 0002's seven displayed routes match. Both are CTest gates
(`client_human_0001/0002`). The empty observation files are correct: observations
are only recorded by scripted runs.

### Interactions demonstrated by artifacts

- **Single selection, move, part-way stop:** 0002 commands 1–2; screenshots
  [01](screenshots-0002/01-single-route-189245000.png) (ring, cyan route,
  destination) and [02](screenshots-0002/02-single-stopped-199315000.png) (order none).
  Session 0001 also has four single-unit moves/redirects of Footman 1.
- **Group move and stop:** many three-unit equal-time moves in both sessions;
  two three-unit stops in 0002 (commands 21–26). Screenshots
  [06](screenshots-0002/06-group-selected-diagnostics-271340000.png) and
  [07](screenshots-0002/07-group-diagnostics-later-272975000.png) show three
  selected rings and per-unit orders.
- **Empty-ground deselection:** [03](screenshots-0002/03-deselected-211360000.png).
- **Visible zoom:** [04](screenshots-0002/04-zoomed-in-213700000.png) and
  [05](screenshots-0002/05-zoomed-out-224560000.png). The operator reports both
  the wheel and +/- zoomed visibly (the scripted wheel had not).
- **F3 diagnostics:** shown in 06/07 (time, running, FPS, command counts, per-unit
  order/route). F3 off is visible in later screenshots without the panel.

### Not demonstrated

- **Space pause with a queued move then stop:** no retained screenshot shows the
  PAUSED banner, and neither recording has a move and stop issued at one frozen
  time. Pause pacing/queueing remains covered only by scripted PAU-0001 and tests.
- **Shift-click remove/add and box drag as such:** selection is not recorded and
  no screenshot isolates those states; only the resulting three-unit selections
  (06/07) are shown.
- **Pan:** no before/after pan screenshot pair was retained.

Operator report: "looks great"; no responsiveness or readability problem reported.
No new difference from WC3 is observed; the shared-target group behavior visible in
07 (one unit idle, two still moving near the point) is the known MOV-0023/MOV-0024
**P3** difference.

### Assessment

Physical mouse/keyboard input drives selection, single and group move/stop, route
and destination feedback, deselection, visible zoom and F3, and the real command
streams replay exactly under every render schedule. Milestone 1's interaction gate
is met for those controls; physical pause/queueing is the one listed control not
shown with physical input and remains scripted-only evidence. No visual fidelity
or WC3 group formation is claimed.

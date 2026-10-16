# HUM-0001: physical-input client validation preparation

Issue #44, P3 interaction gate; no new WC3 mismatch claimed. HUM-0001 was
unused in the repository and GitHub issue search before this design. No session
has yet been observed. This design must be committed before any retained session.

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

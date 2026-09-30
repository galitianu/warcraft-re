# Efficient WC3 map authoring and capture for agents

Lessons from Phase 0 (the first MOV-0002 map, about 23 minutes of editor work for
one map) and Phase 1 (15 maps; about one minute each once the steps were scripted, plus ~45 s for three fresh-process captures). Read this with
[phase-1-procedure.md](phase-1-procedure.md) before touching World Editor.

## What costs time, and what to do instead

| Slow or failing approach | What works |
|---|---|
| Asking Cua for the accessibility tree of World Editor windows (times out after 4 s) | Always pass `"include_accessibility_tree":false`; read the screenshot |
| Background clicks and Ctrl/Alt hotkeys (silently ignored or `background_unavailable`) | `"delivery_mode":"foreground"` for clicks and modifier keys; plain keys (F4, Enter) work via the default route |
| Clicking a newly opened window before any screenshot of it | Take `get_window_state` of *that* window first; click coordinates are mapped through its latest screenshot's scale. Without it, clicks land ~12% up-left |
| Double-clicking a tree item "to be sure" | Single click. A second click opens the in-place rename box and the paste goes into the item name |
| `invoke_menu` for nested items (14 s, often "not found") | WM_COMMAND via [tools/editor-menu.ps1](../tools/editor-menu.ps1): Save Map = 4, Save As = 5, Test Map = 14, Convert to Custom Text = 276, Variables = 282. Push it with `--to 'C:\Users\rdpipe'`; plain `rdpipe push` puts it in `C:\Users\Public\rdpipe` |
| Typing JASS or opening maps through File → Open | `clipboard_write` (CRLF) + foreground Ctrl+A / Ctrl+V; start `World Editor.exe -loadfile "<map>"` |
| Creating each map from scratch (new map, variable, trigger conversion) | Copy an already authored map on Windows, open the copy, replace the trigger text, Save (the name already ends in `.w3m`, so there is no Save As dialog and no `.w3x.w3m` name) |
| Save As with a `.w3x` name for a Scenario map | The editor appends `.w3m`; type a `.w3m` name if Save As is needed |
| Putting shared code in the map header | The editor makes the map require the expansion (new map type and game data). Concatenate library + case in the one custom-text trigger |
| Matching the editor window title exactly | Long titles are truncated (`.../JASS-0001-p020.w3]`) and unsaved ones end in ` *]`; match on the prefix and label |
| Discovering JASS syntax errors at World Editor save | Run [pjass](https://github.com/lep/pjass) locally with extracted `common.j`/`Blizzard.j` first (Homebrew bison is needed to build it) |
| Trusting that a paste landed | `tools/check_map.py` on the pulled map: exact trigger text, empty header, `war3map.j` contents, map format |

Dialogs seen when saving the Phase 0-derived map: only the default-map-name
**Reminder** (press Enter). If the **"requires the expansion"** warning appears,
cancel it: something was put in the map header. Phase 0 also saw two warnings about
creating a new map; those don't occur when a copy of an existing map is edited.

## Capture loop

- One `rdpipe ps` per step (stop old PID, delete and confirm output absent, `Start-Process`
  with `-loadfile`, poll for END + `endfunction`, `rdpipe pull`). A 5-second
  experiment costs ~12–15 s per fresh process. See [tools/capture_runs.py](../tools/capture_runs.py).
- Kill only the PID you started. Poll for completion by content, never by file
  existence or the in-game completion message.
- PreloadGen also records files the game loads after `PreloadGenStart` (unit models,
  icons). Keep them out of the observation payload rather than rejecting the file.
- Take the desktop lease (`RDPIPE_HOLDER=...; rdpipe lease acquire --ttl 1800`) and
  renew it per map in long batches; exec/ps/push/pull are not gated by it.
- Run long batches in the background and watch progress lines, including
  failure lines, instead of sleeping.

## Order of work that avoided rework

1. Write every case file and run pjass on library + case before opening the editor.
2. Author one map interactively with a screenshot after each step, then script
   exactly those steps and verify every saved map with `check_map.py`.
3. Capture the reproduction case (MOV-0002-r2) and compare it with the old evidence
   before authoring or capturing the rest; a library bug found later would affect every map.
4. Capture the timing case before interpreting movement timing.
5. Parse with a strict parser and test it on altered temporary copies; never edit retained files.

## Measurement traps found so far

- `TimerGetElapsed` resolution depends on the timer's **duration**: a 1000 s clock
  reports steps of ~6.1e-5 s (float32 near 1000); a 10 s clock is ~1e-6 s. Choose
  a short clock that still outlasts the experiment when timing matters.
- `R2SW(value, 1, 9)` prints 9 decimals, but its last digits are not the exact
  float value (for example 2.699707008 where the float is 2.69970703125).
- Different sampling periods can disagree at the *same* clock reading: when a unit
  update is due at that instant, one callback can see the state just before it and
  another the state just after. Compare state sequences, not only equal-time samples.
  See [phase-1-results.md](phase-1-results.md).
- Movement at 0.02 s sampling aliases facing updates, which occur about every 0.03 s.
  Don't read a cadence off a single period.

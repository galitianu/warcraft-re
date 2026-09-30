# Phase 1: authoring, capture and parsing procedure

How the Phase 1 library maps were made and how a later session can run one, retrieve
its new output and inspect the parsed observations. Experiment definitions are in
[phase-1-experiments.md](phase-1-experiments.md); results are in
[phase-1-results.md](phase-1-results.md). Run `rdpipe guide` first.

## Sources and shared instrumentation

- [oracle/jass/lib/oracle-v1.j](../oracle/jass/lib/oracle-v1.j): the shared library.
  It provides begin/end markers, stable unit names, samples and ordered action/event
  logs (`OracleBegin`, `OracleWatchUnit`, `OracleRun`, `OracleSampleAt`,
  `OracleOrderPoint`, `OracleOrderImmediate`, `OracleEvent`, `OracleEnd`).
  Output goes through native PreloadGen functions only.
- `oracle/jass/<map>.j`: one case file per map. It holds the setup (units, speeds)
  and a hook that runs the case's actions on a given callback.

**How the library is included:** each map has exactly one custom-text trigger,
Melee Initialization. Its complete text is the library file, then one newline, then
the case file. The map header (Custom Script Code) stays **empty**. When the
library was first pasted into the header, World Editor warned *"This map now requires
the expansion because: Custom script code has been specified"*. That save was
cancelled. An expansion map would change the map type and game data from Phase 0's
Reign of Chaos `.w3m` (w3i format 18). Setup lives only in the case file.

Record format (`@O|sequence|KIND|...`):

```text
BEGIN|<id>|wc3-1.29.2-9231-x86|map=<label>|lib=oracle-v1|time_unit=seconds|numeric_format=R2SW_6|clock_duration=<s>
WATCH|<name>|type=<UnitId2String>|speed=<GetUnitMoveSpeed>|default_speed=<GetUnitDefaultMoveSpeed>
SETUP|<case description, key=value fields>
RUN|requested_period=<s>|callbacks=<n>
TICK|<elapsed>|<callback>                         one per callback, 0..n
SAMPLE|<elapsed>|<name>|<x>|<y>|<facing>|<order>  one per watched unit per callback
ACTION|<elapsed>|<name>|<order>|[<x>|<y>|]accepted=<0|1>
EVENT|<elapsed>|<kind>|<key=value>...
END|<id>|map=<label>|callbacks=<n>
```

Callback 0 is taken immediately after the clock starts, before the periodic timer.
Within a callback the order is always TICK, SAMPLEs in WATCH order, then the hook's
ACTION/EVENT records. SAMPLE keeps Phase 0's field layout.

Check syntax before touching World Editor. [pjass](https://github.com/lep/pjass) builds
on macOS with Homebrew bison (`PATH=/opt/homebrew/opt/bison/bin:$PATH make`).
Blizzard's `common.j`/`Blizzard.j` come extracted from the installed MPQs and are
not committed:

```sh
{ printf 'globals\n hashtable udg_OracleState = null\n trigger gg_trg_Melee_Initialization = null\nendglobals\n'
  cat oracle/jass/lib/oracle-v1.j oracle/jass/MOV-0003.j; } > /tmp/check.j
pjass common.j Blizzard.j /tmp/check.j
```

## Authoring a map in World Editor

Every Phase 1 map starts from the committed Phase 0 map. That map is already a
World Editor-authored 64×64 Lordaeron Summer map. It has the `OracleState` hashtable
variable and a custom-text Melee Initialization trigger with Run on Map
Initialization unchecked. The steps, which [tools/we_author.py](../tools/we_author.py)
repeats through rdpipe:

1. On Windows, copy `Maps\Oracle\MOV-0002.w3m` to `Maps\Oracle\<label>.w3m`, then
   start `World Editor.exe -loadfile "<that path>"`. World Editor accepts `-loadfile`.
2. Press F4 for the Trigger Editor. Take a screenshot of that window, then click
   the Melee Initialization item once.
3. Put library + newline + case on the clipboard with CRLF line endings. Click in
   Trigger Functions, press Ctrl+A, then Ctrl+V. Use foreground delivery.
4. Save Map (Trigger Editor WM_COMMAND 4, via
   [tools/editor-menu.ps1](../tools/editor-menu.ps1) pushed to `C:\Users\rdpipe`).
   Accept the default-map-name Reminder. Any other dialog stops the procedure.
   Because the name already ends in `.w3m`, no Save As dialog appears.
5. Close World Editor, pull the map to `oracle-maps/<label>.w3m` (SHA-256-checked
   transfer), then verify it:

```sh
python3 -m venv local/venv && local/venv/bin/pip install mpyq   # once
local/venv/bin/python tools/check_map.py oracle-maps/MOV-0003.w3m oracle/jass/MOV-0003.j
```

`check_map.py` extracts `war3map.wct`, `war3map.j` and `war3map.w3i`. It requires:
the header section absent; exactly one custom-text trigger equal to library +
newline + case after CRLF→LF; the generated `war3map.j` contains that text and
never calls `RunInitializationTriggers`; w3i format 18. The trigger comment still says
"Default melee game initialization for all players", as in Phase 0. It is only a
comment in the generated script.

Two failed attempts show why the screenshot and checker matter. In both, the
checker failed and the maps were deleted and re-authored. The first click, sent
without a screenshot of the new window, landed on the category row: coordinates are
mapped through the latest screenshot's scale. The second, a double click, opened
the category rename box, and the paste went into the category name.

## Capturing runs

Push the map with `rdpipe push oracle-maps/<label>.w3m --to "Documents\Warcraft III\Maps\Oracle"`
if it is not already there. Then run from the repository root:

```sh
PYTHONPATH=tools python3 tools/capture_runs.py MOV-0003 --runs 3
```

For each run, [capture_runs.py](../tools/capture_runs.py) checks the remote map
hash against the committed map. It stops the previous run's game process,
deletes the old `CustomMapData\<label>.txt` and confirms it is gone. Then it starts a
fresh `Warcraft III.exe -loadfile`, waits for a new file containing END and the
closing `endfunction`, and pulls it unchanged to
`oracle/captures/wc3-1.29.2-9231-x86/<label>/run-NN.txt`. Last, it parses the file and
appends identities to `runs.json`. It refuses to overwrite a retained run. For the
committed Phase 1 runs, `runs.json` was folded into each directory's `manifest.json`,
together with map, library, case and environment hashes, the `check_map.py`
result and the parser's repeatability verdict. No
interaction with the game is needed or allowed during a run.

## Parsing and inspection

```sh
python3 tools/oracle_parse.py --map MOV-0003 --csv-dir /tmp/csv oracle/captures/wc3-1.29.2-9231-x86/MOV-0003/run-*.txt
python3 tools/summarize_phase1.py --csv-dir oracle/derived/wc3-1.29.2-9231-x86 MOV-0003
```

[oracle_parse.py](../tools/oracle_parse.py) (standard library only) checks the
PreloadFiles envelope and footer, experiment, map and build identity, and library,
time unit and numeric format. It also checks sequence continuity, callback
continuity, one SAMPLE per watched unit per callback, record shapes, that every
record in a callback has the same time, END's callback count, and that clock readings
never decrease. It reports equal-time callbacks instead of reordering them, and
keeps values as emitted strings. CSV rows follow sequence order.

WC3 itself adds `Preload` lines for files it loads after `PreloadGenStart`, such as
`units\human\Footman\Footman.mdx`. The parser keeps them as
`generated_preload_entries`, noting which record each follows. They are excluded
from the observation payload hash, as is the generated `PreloadEnd` footer.

Derived CSVs in [oracle/derived](../oracle/derived/) are regenerated from raw captures,
one copy per distinct observation payload.

# Phase 0: a repeatable WC3 → text capture

Completed 30 September 2026 for [issue #1](https://github.com/galitianu/warcraft-re/issues/1).

**Result:** the manually authored `MOV-0002` map starts its experiment automatically
after loading, writes complete text observations, and has been captured through
**20 fresh WC3 process starts**. All 20 `@O` observation payloads are identical.
Raw files are retained separately; their generated `PreloadEnd` footer can differ.

This proves the Phase 0 measurement/extraction capability for this experiment and
environment. There is no C++ implementation or engine compatibility verdict yet.

## Artifacts and identity

- [Map](../oracle-maps/MOV-0002.w3m), 19,009 bytes, SHA-256
  `bb67f103cc5c17507fcf63f4928799939f7875538e8ced6b9512b525c8d23efd`.
- [Hand-authored trigger](../oracle/jass/MOV-0002.j).
- [Game and environment identity](../oracle/environment/wc3-1.29.2-9231-x86.json).
- [Raw captures and verification](../oracle/captures/wc3-1.29.2-9231-x86/MOV-0002/).
- [Capture inspector](../tools/inspect_mov0002.py), Python standard library only.

Both installed copies' game/editor metadata reports **1.29.2.9231** and PE machine
`0x014c` (x86). Their executable and five MPQ archive hashes match between Mac and
Windows. The game's executable SHA-256 is
`a1950f17905b9cd7d5461d45e6723af36dda5304e12dba27a1fea85593b15f3f`.
Andrei confirmed that `9321` in the initial plan was a typo; the project now uses
`wc3-1.29.2-9231-x86`.

The working oracle is UTM 4.7.5, QEMU `virt` / aarch64 with hardware acceleration,
4,096 MiB configured RAM and UTM's automatic CPU count; Windows reports four logical
processors. Windows 11 Pro 25H2 is build 26200. UTM uses `virtio-ramfb-gl`; Windows
reports Red Hat VirtIO GPU DOD driver 22.7.38.43 and Microsoft Remote Display Adapter
10.0.26100.9278. Captures ran in the non-elevated `rdpipe` user's active RDP session,
1920×1080 at 96 dpi. Relevant metadata is committed; the VM image/configuration and
game installation remain local.

## How the map was authored

In the installed World Editor, create a **64×64** Lordaeron Summer map, initial Dirt,
cliff level 2, no water and no random height field. Its playable area is 52×52.
There are no placed terrain obstacles or imported assets. Save may generate the
single player starting location; this does not create melee units.

Open the Trigger Editor. Create one non-array GUI variable, **OracleState**, type
**Hashtable**, initial value None. Convert the default **Melee Initialization**
trigger to custom text and replace its entire contents with `oracle/jass/MOV-0002.j`.
Keep Enabled checked and **uncheck Run on Map Initialization**: the custom initializer
registers its own 0.5-second timer event. Leaving that checkbox on would start the
experiment twice. The original melee actions, including AI and victory checks, are
replaced entirely.

Save as **Warcraft III Scenario**, `MOV-0002.w3m`. The prototype was initially saved
as `MOV-0002.w3x.w3m` because this file type appended `.w3m`; its bytes were copied
unchanged to the clean `.w3m` name. Run 1 used the original editor Test Map launch;
runs 2–20 loaded the identically hashed clean filename. No map generator or scenario
schema was introduced.

The editor saved/validated the trigger successfully. Reading the map's `war3map.wct`
confirmed that it contains the authored JASS exactly after newline normalization.
Its generated `war3map.j` has the expected initializer, and its `main` does not
execute initialization actions a second time. Extracted Blizzard `common.j` and
`Blizzard.j` were used locally to check native declarations, and were not committed.

## Experiment

At the registered timer event, the trigger creates two normal, unmodified `hfoo`
Footmen belonging to player 0:

| Name | Start X/Y | Facing | Role |
|---|---|---|---|
| `u0` | 0 / 0 | 0° | Receives `move` to 1000 / 0 |
| `u1` | 0 / 384 | 0° | Stationary control |

The trigger sets normal game speed and locks it, fixes noon, disables fog/mask and
sets acquisition range to zero for both units. It takes the initial observations,
issues the movement order and logs whether the order was accepted. No RNG seed is
set, and neither unit receives user input.

A repeating timer requests **0.02 seconds** between callbacks, for 250 callbacks.
A separate 1,000-second, non-repeating timer supplies `TimerGetElapsed` readings,
with its start defining experiment time zero. Thus each unit has 251 observations
(initial plus 250 callbacks), through the reported elapsed time **5.000000 seconds**.
Every sample records X, Y, facing and current order. Integers and order IDs are exact
text; real values use `R2SW(value, 1, 6)`. This retains the game's emitted six-decimal
values, not unobserved internal float bits.

## Output transport

The installed script declarations expose `PreloadGenClear`, `PreloadGenStart`,
`Preload`, and `PreloadGenEnd`. The trigger sends one recognizable `@O|...` string
per observation to `Preload`; at completion it calls `PreloadGenEnd("MOV-0002.txt")`.
The actual output is a text `PreloadFiles` function containing those strings.

On this installation the relative output resolves to:

```text
C:\Users\rdpipe\Documents\Warcraft III\CustomMapData\MOV-0002.txt
```

**No registry edit, injected code, process hook, debugger or game modification was
needed.** `HKCU\Software\Blizzard Entertainment\Warcraft III\Allow Local Files`
was absent and was left absent. The output file is read as data; do not execute it
with `Preloader`. The completion screen message alone does not verify file creation.

## Reproduce a capture

Run `rdpipe guide` first and check `rdpipe status`. Take a desktop lease when sharing
the target. The commands below use this machine's recorded paths; adapt the user
profile and installation paths on another machine, and verify the game hash.

Create `Documents\Warcraft III\Maps\Oracle` if necessary, then transfer the committed
map into that directory with `rdpipe push oracle-maps/MOV-0002.w3m --to DIR`.
`rdpipe` verifies transferred bytes by SHA-256. Loading the map manually in WC3 or
using World Editor's Test Map is also sufficient.

Before **each** run, close the previous task-owned WC3 process and remove or archive
the previous output. Confirm that the output path is absent. This prevents accepting
a stale file. Launch a fresh process through `rdpipe ps`, using PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
$game = 'C:\Program Files (x86)\Warcraft III'
$map = 'C:\Users\rdpipe\Documents\Warcraft III\Maps\Oracle\MOV-0002.w3m'
$output = 'C:\Users\rdpipe\Documents\Warcraft III\CustomMapData\MOV-0002.txt'
if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output }
if (Test-Path -LiteralPath $output) { throw 'Old output remains' }
Start-Process -FilePath "$game\Warcraft III.exe" -WorkingDirectory $game `
    -ArgumentList @('-loadfile', ('"' + $map + '"')) -PassThru
```

The experiment requires no interaction after loading. Wait for a **new file** with
the `@O|505|END|MOV-0002|callbacks=250` record, plus the complete `PreloadEnd` and
`endfunction` envelope. Loading time and RDP frame arrival are not experiment time.
Do not click the terrain or issue orders during the capture. Retrieve each run to a
different local filename before starting the next:

```sh
rdpipe pull 'C:\Users\rdpipe\Documents\Warcraft III\CustomMapData\MOV-0002.txt' run-new.txt
python3 tools/inspect_mov0002.py run-new.txt
```

The inspector requires the expected experiment/build/setup, an accepted movement
order, 506 consecutive records, paired increasing timestamps, 251 samples per unit,
and the completion/footer envelope. It reports the stationary-control result and
the final moving state. It preserves the raw file, prints observations as emitted,
and fails incomplete or malformed captures. It is specific to this Phase 0 map;
it is not the future normalized trace format or C++ comparator.

## What was measured

All 20 captures contain **506 complete `@O` records**, with identical payloads.
The stationary control remains at `(0,384)`, facing 0°, current order 0. For `u0`:

| Observation | X | Y | Facing | Order |
|---|---|---|---|---|
| Initial | 0.000000 | 0.000000 | 0.000000 | 0 |
| First callback, t=0.020020 | 2.699707 | 0.014648 | 0.174245 | 851986 |
| Last callback, t=5.000000 | 988.133301 | 0.033203 | 0.388643 | 0 |

The reported callback intervals are **0.019958, 0.019959, 0.020019 and 0.020020
seconds**. These are differences between printed timer readings for the requested
period, not an independent determination of WC3's movement update quantum. Timer
precision and the selected decimal formatting limit what this experiment observes.
Small lateral/facing deviations and stopping short of 1000 are retained observations;
their causes and generality need separate experiments.

The generated footer varies between `PreloadEnd( 5.0 )` and `PreloadEnd( 5.1 )` in
these captures; it is separate from the `@O` experiment timestamps. Both full-file
and payload hashes are recorded, and no raw files were rounded, deduplicated or
rewritten to make them agree. Repeatability is established **under this recorded
setup**, not for arbitrary seeds, maps, UI paths or machines.

The inspector accepted the real captures and rejected five deliberately altered
temporary copies: truncation, a sequence gap, a wrong build identifier, a rejected
movement order and a malformed sample. The production CLI returned exit 1 for each control. No retained
capture was changed. Map and capture transfers passed `rdpipe`'s SHA-256 checks.

## Next

Phase 1: author a separate `MOV-0001` stationary experiment, extract the small shared
instrumentation, and grow a manual map library. The `u1` control in this map is not
a separately established `MOV-0001` case. A small timing experiment should vary
sampling requests before choosing any simulation quantum. Keep C++ bootstrap and
normalized comparison scoped to their later phases.

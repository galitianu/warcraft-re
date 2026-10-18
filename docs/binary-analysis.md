# Binary analysis of the reference executable

Adopted 18 October 2026 by the owner. Static analysis of the reference
executable is used to form **hypotheses** faster: where a mechanism lives, its
constants, branch structure and update order. It does not establish retail
behavior. A finding becomes accepted evidence only when a WC3 capture confirms a
prediction made from it before the capture was taken.

## Rules

- **Evidence rank.** WC3 observations → inferred model → binary analysis →
  Warsmash → other research. A disagreement between a capture and the binary is
  investigated, never resolved by trusting the decompiler.
- **Clean room.** The binary, the Ghidra project, exports, decompiled or
  disassembled code, and generated function reconstructions stay under the
  ignored `local/re/`. Do not commit or paste decompiled code into the repository,
  issues or PRs. Commit **specs**: prose behavior, constants, ordering and
  conditions, each with the function address that supports it, written so the C++
  can be implemented from the spec alone. Engine code is written from specs and
  checked against captures.
- **Experiments.** A spec that changes gameplay pre-registers a permanent
  experiment ID whose predictions come from the spec. Unconfirmed specs are
  labelled hypotheses.
- **Model usage.** Use ghidra-bridge (no model calls) from ordinary agent
  threads. ReAgent issues its own Claude/Codex requests outside the
  continuous-development quota policy; do not run it from dispatched workers
  unless the controller registers it.
- **Identity.** Record the binary hash with every finding. Addresses are only
  valid for the identity below.

## Reference binary

| Field | Value |
|---|---|
| Identity | `wc3-1.29.2-9231-x86` |
| Source | `C:\Program Files (x86)\Warcraft III\Warcraft III.exe` on the oracle VM |
| FileVersion | 1.29.2.9231, ProductVersion `1.29.2.9231 (9d2368a59e)` |
| Size | 14,854,632 bytes, PE32 i386 GUI |
| SHA-256 | `a1950f17905b9cd7d5461d45e6723af36dda5304e12dba27a1fea85593b15f3f` |
| Image base | `0x00400000`; `.text` `0x00401000`–`0x00E65941` |

The install ships no `Game.dll` or `Storm.dll`; game code is in this
executable. There are no symbols or PDB. Headless auto-analysis with the
decompiler took 200 s on this Mac (Mac16,10, 10 cores, 8 GB heap).

## Local setup (macOS ARM64)

Installed outside the repository:

- OpenJDK 21 (`/opt/homebrew/opt/openjdk@21`).
- Ghidra 12.1.4 in `~/tools/ghidra_12.1.4_PUBLIC`. The public release has no
  macOS ARM64 decompiler; build it once with
  `cd support/gradle && JAVA_HOME=/opt/homebrew/opt/openjdk@21 gradle buildNatives`.
  Without it, analysis silently runs without the decompiler.
- A venv at `~/tools/re-venv` with `ghidra-ai-bridge[headless]`, `pefile` and
  `capstone`.

Layout under `local/re/`: `bin/` (the executable), `ghidra/` (project
`war3-1.29.2-9231`), `export/` (bridge exports), `natives.tsv`,
`ghidra-bridge.yaml`.

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@21 GHIDRA_INSTALL_DIR=~/tools/ghidra_12.1.4_PUBLIC
cd local/re
rdpipe pull 'C:\Program Files (x86)\Warcraft III\Warcraft III.exe' bin/war3-1.29.2-9231.exe
shasum -a 256 bin/war3-1.29.2-9231.exe        # must match the table above
GHIDRA_HEADLESS_MAXMEM=8G "$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra war3-1.29.2-9231 \
  -import bin/war3-1.29.2-9231.exe -analysisTimeoutPerFile 10800
~/tools/re-venv/bin/python -I ../../tools/re/jass_natives.py bin/war3-1.29.2-9231.exe \
  --common-j ../War3x.mpq-common.j > natives.tsv
~/tools/re-venv/bin/python -I ../../tools/re/apply_natives.py natives.tsv --project-dir ghidra \
  --project-name war3-1.29.2-9231
~/tools/re-venv/bin/ghidra-bridge export all       # reads ./ghidra-bridge.yaml
~/tools/re-venv/bin/ghidra-bridge decompile jass_IssuePointOrder
```

## Anchor: the JASS native table

Every native is registered as `push signature; push name; push impl; call
0x008CCC80`. `tools/re/jass_natives.py` locates the register function from one
known name and decodes every call. A second table near `0x00CB9000` registers the
same names with one shared implementation, `0x00CBDA30`, and is excluded.

Result for this binary: 2,798 registrations, **1,399 real natives**, covering all
1,260 natives declared in `War3x.mpq` `common.j` plus 139 others not declared
there (not yet classified). Examples: `IssuePointOrder` `0x0049AC20`,
`SetUnitPosition` `0x004ABA00`, `UnitDamageTarget` `0x004AEF70`, `GetRandomInt`
`0x00494E40`. `apply_natives.py` names them `jass_<Name>` with the signature as
a plate comment; 196 of them had not been found by auto-analysis because they are
only pushed, never called. These named entry points lead into the order,
movement, combat and random-number code.

Use `pyghidra.open_project` with an absolute path. `open_program` with a project
location nests a new project inside it and silently imports a fresh, unanalyzed
copy.

## Class names (RTTI)

The executable keeps MSVC RTTI. `tools/re/rtti_vtables.py` recovers 3,883
vtables with class names, e.g. `CUnit` `0x00E9C504`, `CAbilityMove` `0x00F24FC8`,
`CMoveReq`, `MovementRequest`, `MovementGroup`, and the pathing library
`NIpse::CPrBehavior`, `NIpse::CLrPath`, `NIpse::CLrPathingSys`.

## Findings

Each finding is a hypothesis until its experiment passes. Addresses refer to the
identity above. Game constants come from `War3x.mpq` (SHA-256
`69fb8fd8aefe1657d75d53f970e20dbd9d9c23d42a3c2582cca4a97a16becfc7`).

### BIN-0001: move-order arrival and give-up (for #41 / MOV-0024)

Status: **hypothesis**, partly corroborated by footman-v4's measured constant.

1. `CAbilityMove`'s order dispatch (`0x00B65470`) sends `move` (`0xD0012`) to
   `0x00B686A0`, which expands it into a queue of internal sub-orders
   (go-to-point `0xD016B`–`0xD016E` and bookkeeping orders). Go-to-point
   (`0x00B6A010`) creates a pathing request (`0x007FF950`) with two callbacks:
   reached → `0xD0196` (`0x00B666F0`) and failed → `0xD0198` (`0x00BA8580`).
2. The request converts world coordinates to pathing cells by dividing by 32,
   after clamping to the map bounds. Its goal tolerance is
   `max(0.49 cells, order range / 32)`; a range of `FLT_MAX` means any distance.
   A plain move therefore arrives only within **0.49 cells = 15.68 units**,
   matching footman-v4's independently measured `waypoint_radius` (15.68).
3. The speed passed to the request is the unit speed clamped to
   `MinUnitSpeed`/`MaxUnitSpeed` (150/400 in `MiscGame.txt`).
4. `CloseEnoughRange` (100, `MiscData.txt`) is **not** the arrival rule: its only
   use found is the radius of a unit search in target-picking code
   (`0x00644000`).
5. The pathing library ends a request from `0x008AC3E0` through `0x008AD5A0` →
   `0x008B15A0`; a result flag (bit 17 of the result's flag word) selects failed
   instead of reached. The agent dispatch slot (`0x007F2B20`) maps library codes
   `0x6370266F`/`0x63702670` to failed and `0x63702661`/`0x706A7E65` to reached.
6. **Give-up rule.** For a finished result flagged failed (no complete path to
   the goal), `0x008AC3E0` replans instead of failing only if (a) more than one
   result is pending, (b) its per-agent tick counter is below 20, and (c) the
   squared distance between the agent's current position (affine-transformed by
   `0x00613110`) and a point stored in the result exceeds **256** (parsed from
   `"256.0"` at startup, `0x00ECACFC` → `0x01162BC4`). Otherwise the request
   fails and the move order ends; the counter resets when any result finishes.

Candidate rule for MOV-0024: when no complete path to an occupied goal exists,
the unit follows its partial route and, once within 16 units (if the transform
yields world units; 16 cells = 512 units if not) of the stored point, ends the
move order instead of replanning. footman-v4 replans indefinitely at the end of a
partial route, which matches the P3 difference observed in MOV-0023 a/b/c.

Open before freezing predictions: which point the result stores (partial-route
end or goal), the units of the transform, what "more than one result pending"
means for a single unit, and whether `0xD0198` clears the order immediately. The
MOV-0024 layouts (occupied by a blocked mover versus by an idle unit) separate
the reading of (c).

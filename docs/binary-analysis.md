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

## Findings

None accepted yet. Record each as a short spec with addresses, the experiment ID
that tests it, and its status.

# Progress

As of 30 September 2026.

**Current stage:** Phase 0 complete; Phase 1 is next.
**Retail observations:** 20 retained MOV-0002 captures, identical observation payloads.
**C++ compatibility:** unobserved; no new engine exists yet.
**First release:** v0.0.1 — one Footman's movement compared numerically with WC3.

The [plan](Warcraft-III-Reimplementation-Plan.md) is the detailed roadmap. GitHub
issues hold concrete work; this file records capabilities and the next action.
Repository: [galitianu/warcraft-re](https://github.com/galitianu/warcraft-re), private, main.

## Delivered

The [salvage assessment](docs/salvage.md) inspected the old workspace and sibling
engine without modifying them. The old C++ unit executable passed 58 checks, which
establish no retail gameplay compatibility. No old code, fixtures or agent machinery
was imported; the old repositories remain intact.

[Issue #1](https://github.com/galitianu/warcraft-re/issues/1)'s Phase 0 exit gate is met:
the [MOV-0002 map](oracle-maps/MOV-0002.w3m) runs automatically after loading and
yields complete, recoverable WC3 text. Its [JASS source](oracle/jass/MOV-0002.j),
[installation/VM identity](oracle/environment/wc3-1.29.2-9231-x86.json),
[20 raw captures](oracle/captures/wc3-1.29.2-9231-x86/MOV-0002/), and
[reproduction procedure](docs/phase-0-capture.md) are committed together.

Each fresh process start produced 506 complete records and 251 samples per unit
over five reported seconds. Observation payloads agree across all 20 runs; the
generated preload footer can vary. The stationary control stays unchanged.
The moving unit ends at X=988.133301, Y=0.033203, facing=0.388643, order=0, after an
accepted move order to (1000,0). These are observations of this setup, not universal rules.

Output extraction uses native PreloadGen functions. No local-file registry setting
was added. The Python inspector checks completeness/identity/order and rejects
truncation, sequence gaps, wrong builds and rejected movement orders.

**Correction:** both installed copies verify Warcraft III **1.29.2.9231**, x86.
Andrei confirmed 9321 was a typo; active documents and capture identities use 9231.

## Next task: Phase 1 — a small manual oracle library

Start with a separate MOV-0001 stationary case; this map's u1 control does not
substitute for that case. Extract the working log/sample functions into small
shared JASS instrumentation, then add narrow movement experiments manually.
Measure sampling behavior with varied timer requests before choosing a simulation quantum.

Grow toward the plan's approximately 10–20 manual maps with permanent IDs and
parseable outputs. Preserve map/source identity, raw capture and repeatability.
Do not introduce a scenario schema, generated maps or a full VM controller here.

**Still unresolved:** independent movement update cadence, precision beyond emitted
six-decimal values, seed effects, other setups and other-machine agreement.
The 20-run agreement is repeatability under the recorded setup. Normalized reference
contracts, a C++ world, numerical comparison and compatibility CI remain later work.

## Roadmap status

| Phase | Capability / acceptance evidence | Status |
|---|---|---|
| 0 | Automatic map experiment with reliably recoverable WC3 text | Complete — [evidence](docs/phase-0-capture.md) |
| 1 | Small manual map library with shared JASS instrumentation and parseable traces | Next |
| 2 | Native C++ headless equivalent and two numerically comparable traces | Planned |
| 3 | Normalized traces, explicit tolerances, first-divergence report | Planned |
| 4 | C++ compatibility CI against committed WC3 references | Planned |
| 5 | Declarative scenarios extracted from repeated manual tests | Planned |
| 6 | One scenario drives C++ and generates a runnable WC3 map | Planned |
| 7 | Reliable unattended VM capture, when manual work becomes costly | Planned |
| 8 | Microscopic tests, sweeps, and measured compatibility expansion | Planned |

Advance with actual artifacts and verification. Infrastructure checks are not gameplay passes.

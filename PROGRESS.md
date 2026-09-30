# Progress

As of 30 September 2026.

**Current stage:** startup assessment complete; Phase 0 is next.
**Retail compatibility:** unobserved. No WC3 reference capture exists in this repository.
**First release:** v0.0.1 — one Footman's movement compared numerically with WC3.

**Next work item:** [GitHub issue #1 — Phase 0: recover and repeat the first WC3
movement trace](https://github.com/galitianu/warcraft-re/issues/1).

The [plan](Warcraft-III-Reimplementation-Plan.md) is the detailed roadmap. This file
records demonstrated capabilities and the next task, not another copy of every
planned checkbox. GitHub issues hold active task discussion and acceptance evidence.

## Startup result

The old workspace and sibling engine were inspected without modifying them.
[The assessment](docs/salvage.md) names the useful sources and deferred imports.
The old C++ unit executable was built afresh on ARM macOS: **58 checks, 0 failures**.
Those checks do not establish retail gameplay compatibility. No old code, fixture,
agent hook, or task machinery has been imported.
The fresh private GitHub repository is
[galitianu/warcraft-re](https://github.com/galitianu/warcraft-re), with `main` as its
initial branch. The existing `galitianu/war3-workspace` repository remains intact.

## Next task: Phase 0 — recover the first WC3 movement trace

Do these in order in the already-working Windows 11 Pro ARM64 VM:

1. Record installed WC3 executable path, version/build, x86 architecture and SHA-256;
   record VM product, Windows build, resources, graphics settings and transfer route.
2. Manually author one tiny map with two Footmen and a timer. Reserve `MOV-0001`
   for stationary; use `MOV-0002` for straight movement.
3. Start the experiment automatically after loading. Issue movement programmatically
   and emit recognizable begin/end markers plus elapsed time, position and facing.
4. Prove a minimally invasive extraction route from WC3 to a recoverable text file.
   Record actual timestamp units and observation cadence; the plan's output is illustrative.
5. Repeat the experiment at least three times as an initial reliability check. Retain
   each raw output, the map/JASS source, identities, exact procedure, and observed
   differences. This small check does not replace later repeatability characterization.

**Exit gate:** another session can follow the documented procedure, load the map,
and reliably retrieve complete machine-readable observations. Manual loading and
file retrieval are acceptable. Automated process launch alone does not meet the gate.

**Unresolved:** installed game identity, actual output extraction mechanism, and
sampling/repeatability. `rdpipe status` reports a reachable Windows 11 ARM64 target;
that establishes access, not the installation or an oracle capture.

## Roadmap status

| Phase | Capability / acceptance evidence | Status |
|---|---|---|
| 0 | Automatic map experiment with reliably recoverable WC3 text | Next |
| 1 | Small manual map library with shared JASS instrumentation and parseable traces | Planned |
| 2 | Native C++ headless equivalent and two numerically comparable traces | Planned |
| 3 | Normalized traces, explicit tolerances, first-divergence report | Planned |
| 4 | C++ compatibility CI against committed WC3 references | Planned |
| 5 | Declarative scenarios extracted from repeated manual tests | Planned |
| 6 | One scenario drives C++ and generates a runnable WC3 map | Planned |
| 7 | Reliable unattended VM capture, when manual work becomes costly | Planned |
| 8 | Microscopic tests, sweeps, and measured compatibility expansion | Planned |

Advance a phase only with links to its actual artifacts and verification. Record
failures and unresolved behavior; infrastructure checks are not gameplay passes.

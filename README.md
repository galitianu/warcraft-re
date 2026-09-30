# Warcraft III reimplementation

A fresh C++ implementation, developed by measuring real Warcraft III and comparing
small behaviors. Raylib will provide the first renderer; compatibility work will
also run headlessly.

Repository: [galitianu/warcraft-re](https://github.com/galitianu/warcraft-re) (private).

**Target:** Warcraft III **1.29.2 (9231), x86 32-bit**
(`wc3-1.29.2-9231-x86`), running in the user's working Windows 11 Pro ARM64 VM.

**First release, v0.0.1:** one Footman moves, and its movement can be compared
numerically with the same experiment in WC3. The comparison can initially fail;
having trustworthy observations comes first.

Start with:

- [Implementation plan](Warcraft-III-Reimplementation-Plan.md): decisions, Phase 0–8
  sequence, and acceptance gates. The appendix contains older suggestions and
  example results, not completed work.
- [Progress](PROGRESS.md): current state and the next concrete action.
- [Agent guidance](AGENTS.md): scope, evidence, Windows access, and working rules.
- [Salvage assessment](docs/salvage.md): what the previous work actually contains
  and which pieces may help this plan.
- [Phase 0 capture](docs/phase-0-capture.md): the working map, real observations,
  measured limits, and text extraction procedure.

This repository holds the plan, a manually authored movement map, its JASS source,
and 20 retained WC3 captures with identical observation payloads. Phase 0 is complete.
The engine, oracle tooling, experiments, and eventual reference fixtures will grow
together here. C++ gameplay compatibility has not been demonstrated yet.

Use GitHub issues for concrete work and `PROGRESS.md` for the concise status. Keep
results linked to their experiments and commits. There is no separate agent harness
or task database to maintain here.

Windows access is available through `rdpipe`; run `rdpipe guide` before using it.
Next: Phase 1's small manual experiment library, starting with the separate stationary
`MOV-0001` case and shared JASS instrumentation.

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
- [Phase 1 results](docs/phase-1-results.md), [experiments](docs/phase-1-experiments.md)
  and [procedure](docs/phase-1-procedure.md): the manual oracle library.
- [Phase 2 results](docs/phase-2-results.md), [model hypotheses](docs/phase-2-model.md)
  and [build/reproduction](docs/phase-2-procedure.md): the native C++ headless world
  and all ten numerical movement comparisons.
- [Agent workflow notes](docs/agent-wc3-workflow.md): how to author and capture maps
  efficiently through rdpipe.

This repository holds the plan, 16 manually authored WC3 maps with their JASS,
shared oracle instrumentation, raw captures with identities, parsers and derived
CSVs, and a dependency-free C++20 simulation. Phases 0–2 are complete. The C++
stationary case passes; all nine movement cases have documented numerical failures
under unchanged provisional tolerances. The v0.0.1 comparison gate is met; no
release tag has been created.

Build and run without a window (CMake, system clang and Python standard library):

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/usr/bin/clang++
cmake --build build -j 4
ctest --test-dir build --output-on-failure
python3 tools/run_phase2.py --runner build/wc3test --out build/phase2 --reports build/phase2-reports
```

Use GitHub issues for concrete work and `PROGRESS.md` for the concise status. Keep
results linked to their experiments and commits. There is no separate agent harness
or task database to maintain here.

Windows access is available through `rdpipe`; run `rdpipe guide` before using it.
Next: Phase 3, the canonical trace and comparison contract, preserving the measured
differences and observation-phase limits.

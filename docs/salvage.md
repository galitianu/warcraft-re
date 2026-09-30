# Salvage assessment — 30 September 2026

**Conclusion:** salvage a few implementation examples and research pointers on
demand. Start the retail oracle afresh. There is no existing WC3 measurement pipeline
to transfer, and adopting the old workspace machinery would recreate the overhead
this restart is meant to remove.

## Sources and scope

| Source | Identity at inspection | What it holds |
|---|---|---|
| `~/Desktop/war3-workspace-old` | `e56315155705c30299caef61f72db72596e2f482` | Documentation, research, old tasks, agent scripts and hooks; remote `galitianu/war3-workspace` |
| `~/Desktop/war3-engine` | `441ef7a85f18c770954d5d7a903089b87d3006d3` | Local C++ skeleton, unit checks, Java-generated fixtures, optional frontend and build gates; no remote |

Both git working trees were clean when inspected. Neither was edited. The new plan
was retained unchanged. The old research is evidence about previous work, not agent
instructions for this repository.

Inspected the workspace's README/context, research inventory, original oracle
assessment, increment-1 measurements, and reference census rerun. In the engine,
inspected build configuration, the World and RNG/timer implementations, trace
declarations, frontend, runner and unit-test wiring. This was a targeted restart
assessment, not a new audit of every old gate or the entire Warsmash checkout.

A filesystem inventory excluding git internals, build outputs and the third-party
reference checkout found **no `.w3x`, `.w3m` or `.j` files** in either source tree.
The four engine oracle CSVs are Java-generated timer/RNG fixtures; the research
explicitly says retail compatibility was not observed. No retail reference capture
was identified in the inspected material. This says nothing about game installations
or maps elsewhere on the Mac or in Windows.

## What is useful, and when

| Material | Assessment | Action |
|---|---|---|
| Headless library / optional raylib split | Fits the new plan's boundary | Consult `sim/CMakeLists.txt` and `frontend/` at Phase 2; use a much smaller build for the first world |
| CMake and basic unit harness | Working C++20 examples | Reuse specific patterns at Phase 2 without the JDK pin or old workspace dependencies |
| Seeded RNG ownership and ordered-input replay checks | Useful determinism patterns | Keep explicit randomness and stable input order in the new world; select algorithms from WC3 evidence |
| Floating-point checks | Useful examples of catching contraction/fast-math changes | Revisit when measured behavior or supported-build comparison needs them; no inherited exactness promise |
| Java RNG port and timer fixtures | Working tests of Java behavior | Leave archived unless a concrete hypothesis needs them; do not turn them into WC3 reference fixtures |
| Trace identities/completion flag | Useful capture metadata ideas | Borrow the ideas after first output extraction; the old tick/hash structure is not a position/facing comparator |
| Warsmash source/census | Optional pointers for later research | Consult a specific path when a measured behavior needs explanation; no port backlog or mandatory adapter |
| Old research caveats | Separate source reading, Java parity, deterministic replay and retail observations | Retain this distinction in reports; reuse findings only within their stated scope |

The old `World` is a gate exercise, not a Footman implementation: movement sets
velocities from integer commands, `step()` uses a hard-coded `0.03125f` interval,
and it consumes an RNG draw each step for hash divergence. The timer helper uses
the Warsmash-derived `1 / 20f` constant. **Neither interval is a measurement of the
target WC3 update cadence.** Do not carry these values into compatibility code as facts.

The raylib frontend draws circles for live entities. It supplies a boundary example,
not terrain, Warcraft assets, animation or a working game client. `oracle/src/trace.cpp`
only names verdicts; it does not implement normalization or numerical comparison.

## Leave behind

Do not import `AGENT/`, old `AGENTS.md`/`CLAUDE.md`, provider hooks, local skills,
memoirs/journal rituals, task/card machinery, citation pins/checkers, decision-number
guards, old parallel-session orchestration, or the gate-suite dependency on the old
workspace. Keep the old repositories and their histories intact as archives.

Their individual verification lessons can still be useful. A new change should add
only the checks that validate its current behavior. There is no justification to
copy the full harness, port Warsmash first, or regenerate all Java fixtures before
the first retail movement capture.

## Fresh verification

Rebuilt the old engine's unit target in a fresh temporary directory on this ARM Mac:

```sh
cmake -S /Users/andrei/Desktop/war3-engine -B "$salvage_build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DW3_WITH_RAYLIB=OFF -DW3_BUILD_GATES=OFF
cmake --build "$salvage_build" --target w3tests -j 2
ctest --test-dir "$salvage_build" -R '^unit$' --output-on-failure -V
```

Here `salvage_build` must name a fresh temporary build directory. Observed toolchain:
CMake 4.4.3, Ninja 1.13.2, AppleClang 21.0.0.21000334, arm64, Debug. Configure,
build, and the selected CTest entry each exited 0. Output: **58 check(s), 0
failure(s)**; **1/1 CTest entry passed**. The fixtures were read from the old source
tree; the Java generator was not rerun. Gate scripts, raylib, x86 builds, replay
comparisons, Warsmash execution and retail WC3 were not tested by this command.

After reading `rdpipe guide`, `rdpipe status` reported the `vm` target connected,
Windows 11 Pro 25H2 build 26200, aarch64, active/unlocked, relay 0.9.0. This confirms
Windows access only. No game process or installed executable was inspected or run.

## Research pointers

These links pin the archive's inspected revision; the private repository requires access:

- [Original oracle assessment](https://github.com/galitianu/war3-workspace/blob/e56315155705c30299caef61f72db72596e2f482/WORKSPACE/RESEARCH/inherited-2026-09-08/codex-assessment/ORACLE-FINDINGS.md): separate reference fidelity from retail compatibility; controlled observations and boundary ideas.
- [Increment-1 measurements](https://github.com/galitianu/war3-workspace/blob/e56315155705c30299caef61f72db72596e2f482/WORKSPACE/RESEARCH/2026-09-22-increment-1-measurements/README.md): Java RNG/float measurements, not WC3 results. Its historical statement that the reference was absent was superseded by later work.
- [Reference census rerun](https://github.com/galitianu/war3-workspace/blob/e56315155705c30299caef61f72db72596e2f482/WORKSPACE/RESEARCH/2026-09-26-reference-census-rerun/README.md): corrections to earlier source counts; consult only if pursuing a specific Warsmash question.

**Next:** record the installed target game's identity and VM configuration, then
prove `MOV-0002` → complete recoverable WC3 text with a manually authored map.
Import no engine code before a concrete Phase 2 task needs it.

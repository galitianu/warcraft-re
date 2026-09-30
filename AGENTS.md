# Agent guidance

## Purpose and current priority

Build a C++ Warcraft III reimplementation whose behavior is checked against real
Warcraft III. Read `README.md`, `PROGRESS.md`, and the relevant section of
`Warcraft-III-Reimplementation-Plan.md` before starting work. The plan's corrected
decisions and Phase 0–8 sequence govern; Appendix A preserves historical proposals
and illustrative results, not current requirements or measurements.

The reference is **Warcraft III 1.29.2 (9231), x86 32-bit**, identified as
`wc3-1.29.2-9231-x86`. The user has run it successfully in a **Windows 11 Pro ARM64
VM**. Verify and record the installation when capturing evidence; do not reopen
platform selection or infer an x64 WC3 target from the guest OS.

Read the salvage assessment in `docs/salvage.md` and Phase 0's proven capture procedure
in `docs/phase-0-capture.md`. Phase 0 is complete; `PROGRESS.md` gives the current
next task. The first release, v0.0.1, is one Footman's movement compared numerically
with real WC3. An honest numerical mismatch is useful progress.

## Keep the project small

- Keep engine code, oracle tooling, experiments, and references in this repository.
- Work through demonstrated capabilities in the plan's order. Phase 0 does not need
  a VM automation framework, declarative scenarios, or generated maps.
- Build a tiny native ARM Mac headless C++ world when the first oracle experiment
  supports comparison. Keep raylib behind a thin boundary; simulation must not
  depend on renderer types, a window, or wall-clock timing.
- Centralize seeded randomness. Select algorithms from evidence; an old Java RNG
  implementation does not establish WC3's RNG.
- Defer arbitrary W3X loading, JASS interpretation, terrain/assets, networking,
  broad UI, and hypothetical graphics backends until a concrete milestone needs them.
- Add tooling or process only when it removes a demonstrated obstacle. Do not
  restore the old workspace's hooks, rituals, task system, or citation gates.

## Evidence and experiments

- Authority: WC3 observations → inferred model → optional Warsmash research →
  other research. Source reading and agreement with Java are hypotheses or separate
  implementation checks, not retail compatibility.
- Use permanent experiment IDs: `MOV-0001` is stationary, `MOV-0002` is straight
  movement. Never reuse an ID for a different question.
- Record exact game identity, map/source identity, environment, procedure, time
  units, sampling method, and repeatability alongside raw captures. Keep raw output
  and normalized references; do not invent observations or round away differences.
- Measure cadence and ordering. The old skeleton's timestep is not a measured WC3
  update interval. Preserve sequence order when timestamps coincide.
- Use explicit property tolerances and report the first divergence. Investigate
  failures rather than silently changing references or relaxing tolerances.
- Reference capture must come from WC3, independently of the C++ behavior being
  graded. Report passing, failing, and unobserved cases honestly with named scope.
- Ordinary CI will compare C++ output with committed WC3 fixtures; running original
  WC3 belongs to capture/research, not every commit.

## Windows access

You can use a Windows 11 machine through the **rdpipe CLI**. **Run `rdpipe guide`
first.** Use its documented commands for status, execution, UI, and file transfer.
Record which machine you reached and its architecture; availability alone does not
prove it is the selected oracle VM. Use a desktop lease if sharing the machine,
refresh UI state after changes, and verify transfers and retrieved results.
Before authoring or capturing maps, read `docs/agent-wc3-workflow.md`.

## Progress and delivery

`PROGRESS.md` is the concise repository status and next action. The plan contains
the detailed roadmap; GitHub issues track concrete active work. Keep their roles
clear and link evidence rather than maintaining duplicate detailed boards.

Before implementing an increment, identify its behavioral question and acceptance
gate. After work, update the status with actual results and links to artifacts.
Do not mark a gameplay milestone complete because infrastructure builds or its
unit tests pass. If blocked, record the precise missing capability and next experiment.

Use focused commits and check the staged diff. Run checks appropriate to the change
and state what was actually verified. Keep credentials, machine configuration,
build outputs, original game installations, and third-party checkouts out of git.
Preserve the old workspace and engine as read-only salvage sources; import only
specific useful pieces with provenance when the active phase needs them.

Finish with what changed, its commit(s), verification, any material limit, and the
exact next action. Avoid inventing another administrative system to track that work.

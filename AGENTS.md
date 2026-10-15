# Agent guidance

## Purpose and current priority

Build a faithful, playable C++ Warcraft III reimplementation whose behavior is
checked against real Warcraft III. Read `README.md`, `PROGRESS.md`, and the relevant
milestone in `docs/next-roadmap.md` before starting work. That roadmap governs new
development. `Warcraft-III-Reimplementation-Plan.md` records the delivered bootstrap
and its enduring evidence decisions; Appendix A is historical, not requirements
or measurements. Do not repeat completed bootstrap work.

The reference is **Warcraft III 1.29.2 (9231), x86 32-bit**, identified as
`wc3-1.29.2-9231-x86`. The user has run it successfully in a **Windows 11 Pro ARM64
VM**. Verify and record the installation when capturing evidence; do not reopen
platform selection or infer an x64 WC3 target from the guest OS.

Read the salvage assessment before consulting the archives, and Phase 0's proven
capture procedure before first capturing evidence. The movement comparison and
oracle bootstrap gates are delivered. The next destination is a playable Human
skirmish, developed through measured mechanics and an interactive raylib client
in parallel. `PROGRESS.md` records actual capabilities; GitHub issues define work.

## Keep the project small

- Keep engine code, oracle tooling, experiments, and references in this repository.
- Advance the next roadmap through demonstrated gameplay capabilities. Extend
  the existing scenario/capture/comparison loop only for a concrete experiment.
- Keep raylib behind a thin boundary; simulation must not
  depend on renderer types, a window, or wall-clock timing.
- Mouse/keyboard input produces ordered simulation commands. Headless replay and
  the client consume the same commands. Camera, selection, rendering, animation,
  and audio read simulation state/events and never determine gameplay outcomes.
- Centralize seeded randomness. Select algorithms from evidence; an old Java RNG
  implementation does not establish WC3's RNG.
- Add a small interactive client now, then the narrow terrain/asset support needed
  for a recognizable battlefield. Read original assets from a local installation;
  keep them out of git. Defer arbitrary W3X loading, broad JASS interpretation,
  networking, broad UI, and hypothetical graphics backends until their milestone.
- Add tooling or process only when it removes a demonstrated obstacle. Do not
  restore the old workspace's hooks, rituals, task system, or citation gates.

## Prioritize by what a player would notice

Rate every difference from WC3 by how noticeable it would be to a human player:

- **P3, obvious:** visible in normal play, such as wrong speed, path, timing a player can
  feel, collision, damage or order outcome.
- **P2, noticeable on inspection:** visible when watching closely or side by side, or
  changes the outcome of a plausible map script, such as a delay of a few frames or an
  offset of several game units.
- **P1, invisible in play:** measurable only with instrumentation. Examples: sub-frame
  ordering, ulp-level clock values, and sub-unit or sub-degree single-frame offsets.

Give the rating whenever you report an issue. Work on P3 before P2. Do not investigate
P1 differences further: document them with their evidence, gate them as known observed
differences, and return to them only when most comparable behavior is in place or they
block something more noticeable. Never hide a P1 difference by loosening a tolerance.

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

## Continuous BB development

Read `docs/continuous-development.md` when dispatched by this project's controller.
The controller owns scheduling, quota checks, provider alternation, retries,
independent review, and integration. Follow the assigned issue and stage; do not
spawn unregistered threads/subagents, create automations, change shared provider
settings, or take work assigned to another worker. All model work must remain
visible to the controller's quota policy.

Use the assigned isolated worktree. Never edit the shared project checkout or
another worker's files. Preserve work on interruption; a replacement thread may
continue in the same environment. Read git status, the issue, previous receipts,
and actual artifacts before resuming. Do not reset or discard an interrupted diff.
Do not create a durable goal or an independent retry loop that outlives your stage.

Before capture, acquire the existing rdpipe desktop lease. Lease contention means
wait/retry later, not killing another worker's editor/game. Numerical compatibility
and presentation checks are distinct; build success is neither kind of fidelity.
Keep P3 work ahead of P2 and leave known P1 differences deferred.

Implementation workers commit focused changes, run relevant checks, update concise
status, and open/update a PR. They do not merge their own work. Reviewers work in
a separate worktree at the exact PR head, reproduce important evidence, and report
PASS, CHANGES_REQUESTED, or BLOCKED with checks and limitations. A different thread
is mandatory; a different provider is preferred when quota permits. Changes after
review require a new review. Write the assigned JSON receipt atomically only when
its claims are supported; never claim a capture, test, commit, or PR exists without
verifying it. The dispatcher integrates only independently accepted, current-head
changes whose required CI passes under the configured merge policy.

CI runs on self-hosted runners: Linux x64 on `nas-pc`, macOS ARM64 on the Mac
mini. The owner temporarily disabled Windows/MSVC on 15 October 2026. Require all
four active build configurations and their comparison; do not claim a new Windows
pass from historical artifacts. See `docs/self-hosted-ci.md`. Never approve fork
workflows to execute untrusted code on these machines. Preserve fixture and
property tolerances through infrastructure changes.

Complete one bounded stage, write a useful handoff, and return. If blocked, record
the precise obstacle and partial work rather than trying unrelated features. Ask
through the question tool when a decision is genuinely the user's; do not invent
an answer or relax acceptance. The dispatcher can advance another eligible issue.
Finish required commands synchronously and write the receipt before returning;
an idle turn without a receipt is a failed stage. Do not wait for a background
notification or hosted CI. The controller owns the hosted CI wait and merge gate.

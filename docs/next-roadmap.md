# Playable Warcraft III roadmap

Adopted 8 October 2026. This governs work after the Phase 0–7 bootstrap and its
first measured collision increment. The original plan remains the bootstrap
record. Target: **Warcraft III 1.29.2 (9231), x86**, classic presentation, measured
on the selected Windows 11 Pro ARM64 VM. The destination is a faithful playable
reimplementation; the first integrated destination is a **Human skirmish**.

## Development order

Mechanics and the playable client advance together. Each milestone has measured
behavior, an interactive result, and explicit limits. GitHub issues split these
gates into bounded increments; they are the work queue, not this document.
Existing passing fixtures remain protected. Prioritize P3 before P2; defer P1.
Never infer broad fidelity from a fixture count or label a milestone complete
because its infrastructure builds.

| Milestone | Interactive result | Acceptance gate |
|---|---|---|
| 1 — Interactive Footman | Select units, move/stop, pan the camera, show orders and paths | Real input becomes ordered commands; replay yields the same headless state. Render rates cannot change simulation. Existing movement/collision gates pass. |
| 2 — Small battlefield | Groups navigate obstacles, acquire targets, attack and die | WC3 experiments establish multi-unit pathing, order interruption, attack timing, damage/armor and death; held-out predictions and playable scenarios exercise their interactions. |
| 3 — Recognizable Warcraft scene | Animated Footmen, terrain/textures, selection circles, health bars and basic audio | Fixed-camera images and action sequences compare with WC3; animation/audio follow simulation events; picking and camera behavior are verified. |
| 4 — Human base loop | Peasants gather, construct, train units and consume resources/food | Measured costs/timings/queues/cancellation/placement/worker interactions, plus a complete playable build sequence. |
| 5 — Human skirmish | Scoped Human roster, hero progression, representative abilities/items, fog/minimap | A complete match against a scripted opponent; measured component behavior, integration scenarios and an explicit roster/ability coverage list. |
| 6 — Broader compatibility | Other races, wider ability/item coverage, existing maps/scripts and multiplayer | Separate gates for each supported gameplay, format, scripting and network capability; long integrated scenarios and human playtests supplement microscopic evidence. |

Milestones 1–2 are actionable now. Later milestones are destinations; refine their
increments from demonstrated needs. Networking and arbitrary custom maps do not
block the first playable skirmish. Do not build a replacement graphics abstraction,
general engine framework, or complete map/JASS runtime in advance of those gates.

## Milestone 1: interactive Footman

### First client increment

Behavioral question: can actual player orders control the measured world without
rendering changing its results?

- Add an optional native ARM Mac raylib executable linked to `wc3world`. The
  default headless build and CI remain available without raylib or a window.
- Use a flat ground plane and simple geometry for units. Add camera pan/zoom,
  single-unit selection, selection feedback, right-click move and stop.
- Introduce only the command/state boundary the client actually needs. Commands
  record simulation time, stable sequence, entity and order/target. Preserve
  equal-time ordering. Record live commands and replay them headlessly.
- Wall-clock time schedules how much simulation work to perform; it does not
  become simulation state. Respect the existing measured movement cadence and
  exposure behavior. Rendering interpolation cannot mutate the world.
- Provide a deterministic replay check across different render schedules and
  a reproducible manual input smoke procedure with screenshots or video.

Gate: selected units visibly obey move/stop; recorded commands replay identically
under the named render schedules; existing numerical gates pass. State clearly
that placeholder geometry establishes interaction, not Warcraft visual fidelity.

### Follow-up client increments

Box selection, multiple selection, feedback for destinations/current orders,
pause and a readable diagnostic overlay. Measure group-order target assignment
before claiming formation compatibility; issuing the same point to every unit is
not evidence of WC3 group behavior. Remove diagnostic implementation details from
normal player flows as presentation becomes mature.

## Milestone 2: small battlefield

### First mechanics increment

Behavioral question: does the measured two-unit pathing mechanism predict three
or more units meeting, including blocker ordering and partial paths?

Pre-register a new permanent experiment ID after checking the repository and open
issues. Test three Footmen meeting at a point and several held-out arrangements,
with ordered creation/orders and preserved clocks. Capture fresh repeated WC3
runs. Grade the current model before fitting a change; record P3/P2/P1 differences.
Extend generator/observations only if the experiment demonstrates a missing need.

Gate: acceptance is specified before capture, raw evidence and independent
predictions are retained, player-visible differences are either corrected or
honestly reported, and all protected movement/collision fixtures pass. Expand to
larger groups only after this increment establishes the next concrete question.

### Subsequent mechanics increments

1. Static obstacles and blocked destinations, then mixed unit footprints when
   their evidence requires unit-type data.
2. A target-unit order and controlled melee attack: acquisition, approach/range,
   attack point, backswing, cooldown, interruption, life/damage/death event order.
3. Damage and armor interactions; isolate randomness where possible. Add life and
   relevant events to the trace contract and both adapters before claiming passes.
4. Ranged attacks/projectiles and mixed engagements; characterize necessary RNG
   streams separately. Seed ownership exists, but WC3's RNG is not yet established.

Each is split into microscopic issues and held-out tests. Do not hard-code captured
traces, treat decompiled/source behavior as experimental acceptance, or silently
alter references/tolerances. A failing numerical comparison can still be useful
evidence; completing a gameplay gate requires its stated behavior.

## Presentation and integration

The raylib client reads world state and presentation events. Camera, selection,
models, textures, animation and sound are outside simulation. Gameplay events
determine damage/death; animation is synchronized to those events.

Start milestone 3 with one Footman and one terrain set. Read original assets from
the user's installation and keep assets, conversion caches and installation paths
outside git. Add only needed archive/model/texture format support, with provenance
for any salvage examples. Use fixed cameras and timed action sequences against
WC3. Declare lighting/camera/platform limits and image tolerances explicitly;
avoid treating a raw screenshot metric as proof of complete visual compatibility.

Short human play sessions judge responsiveness/readability and overall resemblance.
Automated input replays, screenshots and long integration scenarios catch
regressions between those sessions. Original WC3 remains capture/research, not
a dependency of ordinary CI.

## Continuous execution

`docs/continuous-development.md` defines the BB dispatcher contract. Use one
mechanics lane and one client lane, bounded stages, isolated worktrees, independent
review and CI. The controller creates the next narrow issue only when the current
queue needs replenishing, following this roadmap. Credentials and runtime state
stay outside git. Quota waits resume automatically; blocked issues do not justify
unrelated scope or repeated experiments without a new question.

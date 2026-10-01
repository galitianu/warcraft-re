# Scenario v1

Defined for Phase 5 / [issue #12](https://github.com/galitianu/warcraft-re/issues/12).
A scenario describes **one movement experiment** independently of WC3, the C++
model and any reference. `wc3test --scenario` consumes it first; Phase 6 may later
generate JASS from it. Readiness audit and evidence:
[phase-5-scenarios.md](phase-5-scenarios.md). Parser and validation:
[Scenario.cpp](../tools/wc3test/Scenario.cpp). Migrated cases: [scenarios/](../scenarios/).

A scenario is **input**. It never defines a reference, its expected trace shape, a
tolerance or a result. The [canonical trace contract](trace-contract-v1.md) still
validates outputs against its own independent table of retained experiments, so a
description cannot redefine what MOV-0006 must look like. A scenario without an
independent retail fixture gets no retail compatibility verdict.

## Example

```yaml
# How do facing and displacement change when a moving unit is redirected by 90 degrees?
schema: wc3-scenario
version: 1
experiment: MOV-0006
map_revision: MOV-0006
units:
  - name: u0
    type: hfoo
    position: [0, 0]
    facing: 0
observe:
  period: 0.02
  callbacks: 250
  properties: [x, "y", facing, order]
actions:
  - at: 0
    unit: u0
    order: move
    target: [1000, 0]
  - at: 1.0
    unit: u0
    order: move
    offset: [0, 1000]
...
```

## Fields

Every field below is required unless marked optional. Unknown fields are errors.

| Field | Meaning |
|---|---|
| `schema` | `wc3-scenario`. |
| `version` | Integer `1`. Other versions fail with `unsupported scenario version`. |
| `experiment` | Permanent experiment ID, `[A-Z]{2,5}-NNNN` (MOV-0006). Never reused for another question. |
| `map_revision` | The experiment ID with optional `-suffix` parts (MOV-0002-r2): the specific setup/map revision. |
| `units` | 1–8 units, in **creation order, which is also watch order**. Every unit is watched. |
| `units[].name` | `[a-z][a-z0-9_]{0,15}`, unique. Retained experiments use `u0`, `u1`, … (the trace contract requires it). |
| `units[].type` | WC3 rawcode; v1 supports `hfoo` (Footman) only. |
| `units[].position` | `[x, y]` world units, each in [−4096, 4096] (the 64×64 oracle map). |
| `units[].facing` | Degrees in [0, 360). |
| `units[].move_speed` | Optional. The **requested** `SetUnitMoveSpeed` value, > 0 and ≤ 10000, applied right after that unit's creation. It is never pre-clamped: the world applies its own clamp, and WATCH speed records the result (100 → 150, 522 → 400). |
| `observe.period` | Requested sampler period in seconds. |
| `observe.callbacks` | Periodic callbacks after callback 0, 1–10000. |
| `observe.properties` | Exactly `[x, "y", facing, order]`, in that order. v1 samples all four for every unit. |
| `actions` | Ordered list, possibly `[]`. |
| `actions[].at` | Requested time in seconds; must be a callback time. |
| `actions[].unit` | Name of a declared unit. |
| `actions[].order` | `move` or `stop`. |
| `actions[].target` | `move` only: absolute `[x, y]` in [−4096, 4096]. |
| `actions[].offset` | `move` only, instead of `target`: `[dx, dy]` in [−8192, 8192], relative to the unit's position when the action executes. |

A `move` has exactly one of `target`/`offset`; `stop` has neither.

## Time, schedule and order

- Time is in **seconds**, parsed exactly into integer microseconds. Values that are
  not whole microseconds are rejected, never rounded.
- **Callback 0** is time zero: the oracle library starts its clock, samples every
  unit, then runs callback-0 actions. Callback *k* is requested at *k* × period.
  The run is **complete** after callback `callbacks`, with (callbacks + 1) TICKs.
- In each callback: TICK, then one SAMPLE per unit in watch order, then the
  actions whose `at` equals that callback's time, **in file order**. Samples
  therefore precede the callback's commands, and their effect can first appear
  in the next callback (current *sample-before-command* behavior).
- `at` must be a multiple of `period` and at most `callbacks × period`. Actions
  must be listed in non-decreasing `at`; equal times execute in file order.
  An action at the last callback is legal; its effect is unobserved.
- Requested times are labels of the sampler schedule. They do not establish a
  retail simulation quantum, and v1 says nothing about where WC3's sampler sits
  relative to its own update ([sampling order](footman-v4-results.md#sampling-order)
  remains unexplained).

## Numbers

Reals are unquoted decimals `-?(0|[1-9][0-9]*)(.[0-9]+)?`: at most 6 integer and
9 fractional digits; no exponent, `+`, `inf`, `nan` or hex. Each converts to the
**nearest float32, ties to even**, in exact integer arithmetic, so `707.106781`
equals the C++ literal `707.106781f` and the JASS real it stands for. Integers
are unquoted, without leading zeros. Out-of-range values fail rather than clamp.

Relative targets are evaluated from the **C++ world's own state** at execution,
never from reference coordinates: each nonzero offset component is added in
float32 (`p.x + dx`); a zero component copies the coordinate unchanged, exactly
as the JASS case uses `GetUnitX(u)` without an addition. A computed target outside
[−4096, 4096] fails the run.

## YAML subset

The files are ordinary YAML (Ruby's Psych reads all ten with the same meaning), but
v1 accepts only a strict subset, so no YAML library is needed and nothing is
interpreted differently by different parsers:

- printable ASCII only, LF line endings, a final newline, spaces (no tabs);
- block mappings and sequences; a key's sequence may start at the key's indentation;
  `- key: value` items; one-line flow sequences `[a, b]` of scalars;
- plain scalars of `[A-Za-z0-9_.+-]`, or the same characters in double quotes;
- `#` comments at line start or after a space;
- a required `...` document-end marker as the last content line, so truncation at
  any line boundary is an error. Comments may follow it.

Rejected: duplicate keys, anchors/aliases, tags, flow mappings, block scalars,
escapes, multiple documents and `---`, and unquoted words YAML 1.1 reads as
booleans or null (`y`, `n`, `yes`, `no`, `on`, `off`, `true`, `false`, `null`;
hence `"y"`). Errors name the line.

## Runner capability

Scenario validity is checked separately from what the current C++ runner can
represent. `wc3test` rejects, before writing anything:

- any period other than **0.02 s**: the canonical v1 C++ timing and footman-v4's
  library-clock prediction are defined only for the demonstrated period;
- schedules exceeding the trace contract's 50,000 records;
- duplicate experiments in one invocation (they would share output files).

Not in v1, because no C++ consumer needs them yet: events/aux clocks (JASS-0001
CLOCKS, MOV-0012 STATE), `SetUnitX/Y` after creation, other unit types or owners,
unwatched units, other orders, sampling variants of other periods, and parameter
matrices. Each is added with the experiment that needs it.

## Fixed environment and execution provenance

Every v1 scenario assumes the Phase 1 oracle environment: the 64×64 flat map,
units owned by Player(0) with acquisition range 0, normal locked game speed and
the oracle-v1 library ([phase-1-experiments.md](phase-1-experiments.md)).

**Model, seed, observation phase, compiler and build** are execution provenance,
chosen on the `wc3test` command line and recorded in the run identity — never
scenario semantics. A C++ seed does not establish retail RNG equivalence.

## Identity in run artifacts

`wc3test --scenario FILE_OR_DIR` (repeatable; a directory means its `*.yaml`
files sorted by name) writes the same files as the hard-coded runner. Additive
metadata, outside the observation payload:

- `identity.json` and each trace's `identity.build` list the run's cases from
  the scenarios, plus `scenarios: [{experiment, map_revision, path, sha256}]`;
- each trace's `provenance.scenario` is `{schema, version, path, sha256}` of the
  exact bytes parsed; `path` is as named on the command line, `/`-separated.

The SHA-256 identifies a scenario; editing even a comment changes it. Observation
payload hashes (scenario/units/time/records/completion) are unaffected by this
metadata, which is how migrated and hard-coded runs are compared.

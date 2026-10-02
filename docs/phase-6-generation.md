# Scenario-to-WC3 generation (Phase 6, issue #14)

## Behavioral question and gates

Does one scenario describe equivalent experiments in WC3 and C++? Generation is
checked against the unchanged, independent hand-written MOV-0001–MOV-0010 cases.
Retail reproduction needs three fresh processes per new map revision, exact
observation equality with the old capture, and the same scenario's C++ comparison
under the original trace contract and tolerances. Generated text alone has no
retail verdict.

## Route and supported input

[oracle_codegen](../tools/oracle_codegen/main.cpp) shares the C++ v1 parser with
`wc3test`. It reads only scenario bytes and the template bounds; no World is run
and no captures or references are consulted. [generate_oracle.py](../tools/generate_oracle.py)
checks the template's identity, calls it and writes LF-only JASS with a generation
manifest. The same bytes must equal [committed goldens](../oracle/generated/v1/)
on every CI configuration.

Packaging uses the proven copied `.w3m` -> one custom-text trigger -> World Editor
save -> [check_map.py](../tools/check_map.py) route. The header stays empty and
[oracle-v1](../oracle/jass/lib/oracle-v1.j) stays unchanged. No MPQ writer or new
packaging dependency is needed. `mpyq` is an authoring/checking dependency in the
local venv, never an ordinary-CI requirement. VM authoring/capture remains manual
through rdpipe; Phase 7 owns unattended VM orchestration.

The generator supports the demonstrated v1 20 ms sampler, Footmen, named watch
order, requested speed setters on a single unit, absolute moves, relative moves,
and stop. Literal tokens are emitted unchanged, including `707.106781`. A zero
relative component emits the bare getter. Negative offsets emit subtraction;
nonzero offsets are evaluated from WC3's own state at the action callback.
Actions sharing a callback run in file order. Bootstrap is the same single
0.5 s trigger as the controls. Every capture's SETUP contains the exact scenario
SHA-256 and ordered declared setup/actions; these are inputs, not predictions.

Reject unsupported periods, fractional CreateUnit positions (v1 cannot request
an observed setter), multi-unit speed-setter setups, expired clocks, oversized
record/SETUP counts, and coordinates outside the template's playable bounds.
CreateUnit placement at arbitrary integer positions is still unobserved: passing
validation does not establish a retail result. Relative displacement cannot exceed
the playable span; its final target depends on runtime state. Target clamping near
the bounds is unobserved, so only capture can validate such a setup.

[template-bounds.json](../oracle/template-bounds.json) records fields decoded from
the exact Phase 0 template's `war3map.w3i`/`war3map.w3e`: 65×65 terrain vertices at
(−4096,−4096), 52×52 playable tiles, complements 6/6/4/8. Playable bounds are
X [−3328,3328], Y [−3584,3072]. Terrain extents and playable bounds differ. The
editor's generated `SetCameraBounds` uses these same playable edges plus its
camera margins. Re-extraction (local venv only):

```sh
local/venv/bin/python tools/template_bounds.py oracle-maps/MOV-0002.w3m --out local/template-bounds.json
```

## Independent call audit

[audit_oracle.py](../tools/audit_oracle.py) compares ordered executable statements,
callback branches, API calls and literal arguments with `oracle/jass/<revision>.j`.
Those hand-written cases are never generated or edited. Function/local variable
names, comments and null cleanup are normalized; SETUP is separately reported as
metadata. Unknown executable statements/operators fail the audit.

All ten cases pass [the audit](../results/phase-6/generator-audit.json) and
[pjass](../results/phase-6/pjass.json). There is no unexplained API/callback/timer
order or argument difference. MOV-0002 creates both units before acquisition
setters, exactly as its control does. Multi-unit property setters are rejected
rather than extending that call-order finding. The other nine controls configure
their single unit directly after creation.

## Reproduce one flow

Read [agent-wc3-workflow.md](agent-wc3-workflow.md) and
[phase-1-procedure.md](phase-1-procedure.md); run `rdpipe guide`. Build normally.
The example packages the existing MOV-0006 scenario as the new `MOV-0006-g1`
revision. The original scenario file is never copied/edited to change its label.
A packaging revision is execution provenance, and the source scenario hash stays
identical on both sides.

```sh
python3 tools/generate_oracle.py --codegen build/oracle_codegen --scenario scenarios --check --out build/generated
python3 tools/audit_oracle.py --generated build/generated --out build/generator-audit.json
python3 tools/generate_oracle.py --codegen build/oracle_codegen --scenario scenarios/MOV-0006.yaml --map-revision MOV-0006-g1 --out local/MOV-0006-g1
```

Retain the generated case as `oracle/generated/maps/MOV-0006-g1.j` and its manifest
as `oracle/generated/maps/MOV-0006-g1-generation.json`. Never overwrite a retained
revision. Check pjass on library + case, with the extracted Blizzard scripts and
stub globals as in Phase 1. All scripts below run from the repository root:

```sh
export RDPIPE_HOLDER=issue-14
rdpipe --target vm lease acquire --ttl 1800
rdpipe --target vm ps - < tools/verify_oracle.ps1 > local/oracle-verification.json
rdpipe --target vm push tools/editor-menu.ps1 --to 'C:\Users\rdpipe'
python3 tools/we_author.py MOV-0006-g1 --case oracle/generated/maps/MOV-0006-g1.j
local/venv/bin/python tools/check_map.py oracle-maps/MOV-0006-g1.w3m oracle/generated/maps/MOV-0006-g1.j
python3 tools/capture_runs.py MOV-0006-g1 --runs 3
```

Retain the verification JSON under `oracle/environment/` as a new record. The
verification must show the selected `vm` machine, Windows ARM64, version
1.29.2.9231, x86 PE machine 0x014c and the hashes of all seven installed reference
files. Availability alone is insufficient. No game/editor/install/configuration
files are copied into git.

```sh
local/venv/bin/python tools/record_generated.py --map MOV-0006-g1 --generation oracle/generated/maps/MOV-0006-g1-generation.json --verification oracle/environment/phase-6-verification.json --codegen build/oracle_codegen
```

Repeat for MOV-0002-g1 (two units), MOV-0004-g1 (speed setter/clamp), and
MOV-0010-g1 (stop), renewing the lease. Capture each three times in fresh processes.
The four independent shapes are handwritten in `trace_contract.GENERATED_SHAPES`;
no scenario generates them. Raw files/manifest stay under their new labels.
Normalization reports exact ordered WATCH/RUN/TICK/SAMPLE/ACTION/EVENT equality
with the retained control, preserving numeric strings. BEGIN/END revision,
SETUP text, raw sequence numbers, Preload entries and footer are named metadata.
A mismatch remains a finding and keeps the gate open.

After all four captures exist, create the new canonical fixtures once:

```sh
python3 tools/run_generated.py --runner build/wc3test --out build/generated-loop --reports results/phase-6 --write-fixtures
```

Ordinary reruns omit `--write-fixtures`. The tool rejects overwriting fixtures.
The comparator allows the registered packaging revision only when it and the
C++ trace bind the same schema/version/path/scenario hash and independent shape.
It preserves all numeric tolerances and every record; there is no resampling,
reference tuning or scenario-derived expected output.

## Validation and handoff

On 2 October 2026 the selected VM was restored. A fresh
[installation verification](../oracle/environment/phase-6-verification.json)
records `WIN-5OII4GM1ENR`, Windows 11 Pro build 26200 ARM64, all seven matching
reference-file hashes, game/editor version 1.29.2.9231 and x86 PE machine 0x014c.
The editor's raw version resource is comma-separated; the verification preserves
that text and separately reads its numeric version fields.

Four new [editor-saved maps](../oracle-maps/) passed `check_map.py` and ran in
three fresh WC3 processes each. Their [raw captures/manifests](../oracle/captures/wc3-1.29.2-9231-x86/)
and four new [canonical fixtures](../oracle/canonical-generated/wc3-1.29.2-9231-x86/)
bind the unchanged original scenario bytes to generated case, saved map and verified
installation. All three raw files per revision are byte-identical. The
[full loop report](../results/phase-6/generated-loop.json) and
[summary](../results/phase-6/generated-loop.md) pass:

| Generated revision | Independent control | Ordered observation records | Fresh runs | C++ v4 |
|---|---|---:|---:|---|
| MOV-0002-g1 | MOV-0002-r2 | 757, exact equality | 3 identical | PASS |
| MOV-0004-g1 | MOV-0004 | 1205, exact equality | 3 identical | PASS |
| MOV-0006-g1 | MOV-0006 | 506, exact equality | 3 identical | PASS |
| MOV-0010-g1 | MOV-0010 | 506, exact equality | 3 identical | PASS |

No first observation divergence exists. Metadata changes are BEGIN/END map
revision, SETUP declaration/scenario hash and the preload map path. Raw record
sequence numbers remain equal. MOV-0010's transport footer changes from 5.0 to
5.1; its TICK clock strings remain exact. The other three footer values match
their controls. These metadata and transport details are retained in the report;
no observed record or numeric string is discarded or rounded.

[runner-before-after.json](../results/phase-6/runner-before-after.json) retains all
50 before/after observation hashes: every v1/v2/v2-before/v3/v4 payload stays
identical on native ARM64 AppleClang Release. The existing regression baselines,
Phase 2 archival migration, 45 raw Phase 1 runs and 15 canonical fixtures remain
unchanged. CI still grades every suite on the same committed scenario bytes and
checks generator goldens, control audit and downloaded cross-configuration hashes.
The [Phase 5 scenario-only main-push evidence](../results/phase-5/control-removed-main-verification/summary.md)
was downloaded and independently rechecked (five configurations PASS).

[Workflow 37001747756](https://github.com/galitianu/warcraft-re/actions/runs/37001747756)
passes all five configurations and the aggregate job at implementation `191f9ff`.
Downloaded evidence [rechecks locally](../results/phase-6/pr-verification/summary.md):
all generated JASS/manifest bytes and scenario inputs agree, every reviewed
regression baseline passes, and v4 is 10/10 on every configuration. CTest is 3/3
and Python 64/64 for that generator-only implementation. After retaining real
captures, native ARM64 AppleClang Release CI including `--archive` passes CTest
3/3, Python 65/65, the four generated comparisons and all existing gates.
CI downloads include the new fixtures, traces and full loop reports;
`summarize_ci.py` independently renormalizes retained WC3 evidence, checks exact
fixture bytes and regrades downloaded C++ traces. A forged PASS or updated hash
cannot hide a changed sample. The Phase 6 main-push gate awaits merging
[PR #16](https://github.com/galitianu/warcraft-re/pull/16).

Sampling order, retail simulation quantum, RNG/seed effects, other machines,
JASS literal conversion at untested values, and near-boundary clamping remain
unobserved or unresolved. The sampler/update-order work is split into
[issue #17](https://github.com/galitianu/warcraft-re/issues/17), as issue #14 permits
after reproduction passes. **MOV-0013** is reserved for that question; it has no
map or retail capture yet. It needs timing/state features outside v1 and a
before/after-proven runner extension. The existing v1/model timing stays unchanged.

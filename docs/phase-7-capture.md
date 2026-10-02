# Unattended oracle capture (Phase 7, issue #18)

## Question and acceptance

Can the proven v1 editor/capture procedure run from one invocation, with success
bound to complete, reproducible retail output? The independent controls are the
hand-authored MOV-0002-r2, MOV-0004, MOV-0006 and MOV-0010 maps and their retained
Phase 1 observations. No expected shape or observation comes from C++ output.

The entry point is [capture_oracle.py](../tools/capture_oracle.py). It reuses the
generator, CRLF paste/editor route, saved-map checker, fresh-process capture,
installation verifier, manifest builder, normalizer and unchanged comparator.
There is no map writer or VM management service.

## Preconditions and supported scope

- Local macOS host with UTM and `utmctl`, configured `rdpipe --target vm`, and the
  selected Windows 11 Pro ARM64 guest. Run `rdpipe guide` first. Read
  [agent workflow](agent-wc3-workflow.md) and [Phase 1 procedure](phase-1-procedure.md).
- Supply the selected VM's exact UUID from `utmctl list`. Its guest-agent IP must
  match the rdpipe target, and the guest machine name must match the retained
  installation-verification identity (or an explicitly supplied `--machine`).
  VM configuration, credentials and installations remain local.
- An active, unlocked, non-elevated rdpipe desktop at **1920×1080, 96 dpi**, with no
  running WC3 or World Editor process. World Editor retains its demonstrated
  maximized Trigger Editor layout. The command does not configure that layout.
- The verified **1.29.2.9231 x86** game/editor and five MPQs must match all seven
  recorded hashes. ARM64 describes Windows, not the WC3 target.
- Build `oracle_codegen` and `wc3test` normally. Install `mpyq` in a local venv.
  Supply the existing pjass executable and extracted, uncommitted `common.j` and
  `Blizzard.j`. No third-party checkout or game script is committed.
- Initially accept only the exact reviewed v1 bytes of `scenarios/MOV-0002.yaml`,
  `MOV-0004.yaml`, `MOV-0006.yaml` and `MOV-0010.yaml`. A new scenario or v2 timing
  needs its own independent definition and capture support. Parameter sweeps and
  collision remain Phase 8 work.

## Invocation and results

For example, choose a **previously unused** revision; this spelling is illustrative:

```sh
local/venv/bin/python tools/capture_oracle.py \
  --scenario scenarios/MOV-0006.yaml --map-revision MOV-0006-new \
  --runs 3 --out local/capture-MOV-0006-new \
  --vm "$ORACLE_UTM_UUID" \
  --pjass /path/to/pjass --common local/War3.mpq-common.j \
  --blizzard local/War3.mpq-Blizzard.j
```

From these preconditions one command generates/syntax-checks JASS, verifies the
VM/installation, acquires/renews the desktop lease, uploads a private template
copy, pastes **library + newline + case** into its single trigger, saves through
World Editor and retrieves the saved map. The LF→CRLF conversion is explicit.
`check_map.py` requires exact source, an empty header, w3i format 18 and no duplicate
initialization. Only the known default-map-name Reminder is accepted; an unexpected
save dialog stops the run and leaves its UI snapshot.

Each run checks the saved map hash, removes and confirms absence of old output,
starts a fresh WC3 process and waits for END **and** the PreloadEnd/endfunction
transport envelope. Retrieval checks the remote hash before and after transfer
and compares the local bytes. The strict parser validates sequence, identity,
callback/sample order and completion; incomplete output never counts as a run.
The command repeats installation/hash verification after capture.

A new output directory contains an evidence bundle with repo-relative source,
map and capture paths; complete raw files and manifests; `diagnostics/` with
command results, UI images, process receipts, transfer identities and a stage
journal; `candidate/<revision>.json`; exact `reproduction.json`; and
`comparison.json` from footman-v4 using the frozen, identical scenario bytes.
Equal-time sequence order and all retail numeric strings are retained.

Three runs are the default; 3–20 runs are accepted. Repeatability requires every
run to agree, and every ordered WATCH/RUN/TICK/SAMPLE/ACTION/EVENT observation must
equal the independent control for a passing reproduction. BEGIN/END revision,
SETUP declaration/hash, raw sequence numbers, generated Preload entries and
footer remain separately named metadata differences.

Exit **0** means validated, reproducing capture and passing C++ comparison;
**1** means a validated numerical/reproduction finding (raw evidence and candidate
retained); **2** means a failed stage. `report.json` is produced only after
validation and comparison. `canonical_promotion` is always false. Promotion into
a retained reference requires a separate explicit, reviewed action.

## Deadlines and recovery

Guest readiness has a 90 s default deadline, each game run 120 s, and the whole
command 900 s; override with `--guest-deadline`, `--run-deadline`,
`--total-deadline`. Individual command/UI waits are also bounded. Cleanup has
separate bounded attempts so the lease can be released after a deadline.

A stopped/suspended selected VM is started with utmctl. A started but unresponsive
guest fails with the last readiness error; it is never reset automatically.
Lease contention fails before authoring. Existing game/editor processes stop the
flow; the command never terminates them. It stops only invocation-owned PIDs after
checking executable path and process start identity. Guest-side launch receipts
allow cleanup after a lost launch response. A transport outage can prevent cleanup;
the retained receipt identifies what to check, and the 300 s lease TTL expires.

No resume is supported. The output directory, retained revisions and remote map
names are never overwritten. After a failure, inspect `diagnostics/journal.json`
and command/UI evidence, restore the documented preconditions and retry with a
new revision and output directory. Completed runs and rejected attempts stay with
the failed invocation. Changed scenarios/maps/installations cannot be silently
combined across attempts.

## Measured evidence

PR #16 is merged at `4af616eae354b15fbdc0ab94be5f24ec5fe40120`, and issue #14
is closed after its delivery gate. All five retained main-push artifact
configurations were regraded with that exact revision's tools; the
[recheck](../results/phase-7/prerequisite-verification/summary.md) passes. This
avoids interpreting its v1 generator metadata with later v2 source identities.

[The retained evidence](../results/phase-7/summary.json) covers four new revisions
and twelve fresh processes; all reproduce their controls exactly and all same-scenario
C++ comparisons pass. No canonical fixture is promoted.

| Revision | Runs | Additional interventions | Seconds | Reproduction / C++ |
|---|---|---|---|---|
| MOV-0002-g3 | 3 | 0 | 151.540 | PASS / PASS |
| MOV-0004-g3 | 3 | 0 | 165.733 | PASS / PASS |
| MOV-0006-g3 | 3 | 0 | 143.970 | PASS / PASS |
| MOV-0010-g3 | 3 | 0 | 149.060 | PASS / PASS |

Tool/source, installation, map and raw hashes, process start receipts, transfer
identities and stage timings are retained per bundle. Successful committed extracts
keep the pasted trigger, Reminder and saved-map screenshots; the original local
bundles retain all intermediate screenshots. Stopped-VM startup is covered locally,
not by stopping the shared working guest.
Other machines/seeds and retail RNG remain UNKNOWN. Existing P1 sampling-order
findings remain deferred under AGENTS.md; this work changes no model or tolerance.

[The measured operator baseline](../results/phase-7/manual-overhead.json) uses a separate `MOV-0002-manual7` map and three
fresh processes. An agent acting as operator submitted eight terminal groups,
including one local C++ path correction: **7 additional submissions**, **290.56 s**
from generation to lease release. Seven groups were planned. This includes
coordination latency and is not a controlled VM performance benchmark. The new
command requires one initial submission and **zero additional intervention**;
its measured elapsed times include both installation reads, transfer hashes,
additional UI refreshes, validation and C++ comparison.

[Failure evidence](../results/phase-7/failures.json) records three real checks:
a deliberately unavailable expected machine failed readiness in **3.17 s** with
no lease or process; another live holder caused contention failure in **0.99 s**;
a **0.1 s** game-output deadline failed at `capture-01` in **72.46 s total**, including
successful map authoring, retained diagnostics and cleanup. Both owned editor/game
processes were stopped, the lease released, and no result or candidate was emitted.
The selected running guest was never reset. Local tests additionally exercise an
unresponsive relay, stopped-VM startup, map/transfer mismatch, stale/incomplete
output, changed inputs, launch-response loss and failed cleanup.

The failed output directories retain every command result, stage and process
identity. The committed extracts retain the final relevant UI image; intermediate
screenshots remain in the original local bundles. No failure is counted as a fresh
repetition or a compatibility pass.

Offline regrading uses no VM or game installation:

```sh
python3 tools/regrade_capture.py --bundle results/phase-7/captures/MOV-0006-g3 \
  --runner build/wc3test --codegen build/oracle_codegen --out local/regrade-MOV-0006
```

Ordinary CI's required integrity test regenerates each case from frozen scenario
bytes, renormalizes every raw run, checks exact candidate/control reproduction,
checks fresh-process receipts and compares its own compiled C++ runner. It never
runs original WC3. Deleting any retained bundle fails the test.

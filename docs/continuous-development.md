# Continuous BB development

This repository owns its scheduling policy. **No global pool threshold,
concurrency limit, provider preference, account order or other project's thread
is changed.** The roadmap is `docs/next-roadmap.md`; GitHub issues are the queue;
`PROGRESS.md` summarizes demonstrated capabilities. Runtime JSON is only dispatch
bookkeeping and is stored outside the repository.

## Quota and provider policy

- Alternate the configured providers for each new worker thread. When the next
  provider is unavailable or at **80%** in any applicable usage window, use the
  other. When both are unavailable, continue cheap scheduled checks and resume
  model work automatically once BB reports usable allowance.
- Read `bb settings usage --machine <execution-host> --json`. Account-wide short
  and weekly windows and model-specific windows are checked. Missing/error,
  malformed or expired observations fail closed. Never assume usage became zero
  just because a reset time passed; require a new usable observation.
- The cutoff uses the selected provider login's **total reported account usage**.
  It is an admission/stop policy for this controller's workers, not a global
  restriction. Other BB work may continue past 80%; that usage can cause these
  workers to wait. The controller does not attempt to convert tokens into exact
  subscription percentages or attribute concurrent third-party usage to itself.
- Managed Claude/Codex threads use their own provider credentials through
  **thread-local Account Pooler bypass**. The controller creates an initial
  message scheduled for 2099, records its identity, sets bypass, rechecks quota,
  then explicitly dispatches that one message. This avoids a first-request race
  and avoids pool failover/credit fallback changing the account being measured.
  It does not alter any existing/manual thread or shared pool setting.
- Every minute, stop only registered workers whose provider becomes unavailable
  or reaches the cutoff. Cancel their queued/native BB retries so those cannot
  restart outside the controller policy. Preserve their worktree and continue the
  implementation in a fresh eligible-provider thread. Quota stops do not count
  as failed attempts. If both are spent, retain work until one becomes eligible.
- Re-read the registered thread after every stop. A successful stop command can
  leave it starting/active/stopping. Keep its slot, lane and worktree ownership
  while retrying that stop on later ticks, even if usage returns or issue scope
  changes. Grade receipts and release finished environments only after confirmed
  runtime release. Pending user decisions remain pending.
  Each launch records its original lane; editing issue metadata cannot release
  that lane before its worker stops. Legacy active launches without a recorded
  lane conservatively reserve both lanes until confirmed release.
- Provider choice is fixed for a BB thread. Alternation is between newly started
  threads, not changes to the provider within a thread. A handoff retains the
  implementation environment and points to the previous thread/artifacts.

**Measurement limit:** this is enforcement against reported usage, checked before
dispatch and every minute during work. Provider reporting can lag; already accepted
requests can carry usage above 80% before the next stop. BB's usage response does
not expose a per-request project reservation or an exact hard subscription cap.
The controller does not claim an exact 80.000% ceiling or enable paid usage. Local
provider login/authentication is required; the shared pool's credentials do not
establish that the local login works. Scope is the configured two local logins,
  not every account in the shared pool. Cursor (`acp-cursor`), if selected, uses
  its native login without pool bypass; it must expose valid usage windows through
  BB or it is kept ineligible. Cursor's available BB permission modes are
  accept-edits/full; dispatched Cursor workers use full in their isolated worktree.
  No global provider is enabled by installation.

## Work queue and stages

Eligible GitHub issues carry `war3:auto`, these three nonempty sections:

```markdown
## Question
One concrete behavioral or client question.

## Acceptance
Observable gate, evidence/checks required and named scope.

## Scope
Limits and dependencies; no unrelated features.

<!-- war3-dispatch {"lane":"mechanics","depends_on":[]} -->
```

Use `client` for the second lane. Dependencies are issue numbers and must be
closed before dispatch. Do not reuse an experiment ID as a job ID. The issue is
the scope authority; the dispatch marker just supplies execution metadata.
Removing the label or closing an unmerged issue stops its registered work and
retains the worktree. Changing the issue body invalidates the old stage's
acceptance and starts a fresh implementation handoff. Malformed issue metadata
is reported without stalling the other lane.

At most two workers run by default. Each lane has one in-flight increment.
Retained implementation work and review-requested revisions keep their lane
reserved during retry backoff; fresh issues cannot overtake that increment.
An explicitly parked issue releases its lane while retaining its partial work.
An implementation completes acceptance, commits, pushes and opens a ready PR with
`Closes #N` and `<!-- war3-job:N -->`. An independent reviewer starts in a separate
worktree at the immutable PR head, grades against the current main, reproduces
important checks, and posts a commit-bound GitHub COMMENT review. A separate
thread is required even when only one provider has quota; normal alternation
gives cross-provider review when both are eligible.
New worktrees refresh the base branch (or exact PR ref for review) before creation,
so later increments include previously merged work rather than a stale local main.

The controller verifies the receipt's run/stage/issue, actual clean worktree HEAD,
PR identity/head/base, and posted review. It requires all four active measured CI jobs and
the build-scope aggregate from `Primitive compatibility`; missing checks cannot
count as success. Every reported check must pass, the PR must be ready/mergeable,
and its head must include current main. A main/head change invalidates acceptance
or requires re-integration and a fresh independent review. Automatic merge, when
configured, uses a squash merge pinned to the reviewed head, never `--admin`.
Manual merge policy keeps accepted PRs awaiting the user's merge.
The five compatibility checks are a fixed minimum; optional runtime
`required_checks` only adds names from that workflow and cannot remove the minimum.
As of 15 October 2026, the owner temporarily disabled Windows/MSVC. macOS ARM64
Release/Debug run on the Mac mini; Linux x64 GCC Release/Clang Debug and the
comparison run on `nas-pc`. All are self-hosted; no GitHub-hosted fallback is used.
Windows remains unobserved for new heads. Restore its workflow entry, summary
requirement and controller minimum together when a Windows runner is available.
See [self-hosted CI](self-hosted-ci.md) for services and recovery.

When there is no unfinished runnable queue, a bounded planning worker uses the
earliest unfinished roadmap gates to create at most two narrow issues. It checks
existing issues and delivered evidence first. If all useful work needs a user
decision, or the roadmap is complete, it records that obstacle instead of creating
busywork. No new task board, long-running reasoning supervisor or subagents are
needed. The dispatcher owns all agent launches; workers cannot launch extra work.

## Receipts and recovery

The prompt assigns `local/dispatch/<run-id>.json` in the worker worktree (gitignored).
Write JSON to a temporary sibling and rename it atomically. Common fields:

```json
{
  "run_id": "the assigned run ID",
  "stage": "implement",
  "status": "PASS",
  "summary": "Actual behavior and demonstrated scope",
  "checks": ["The actual command and outcome"],
  "limitations": ["Material unobserved scope"],
  "issue": 30,
  "pr_number": 40,
  "head_sha": "full 40-character commit SHA"
}
```

An implementation PASS requires an actual clean committed head and existing ready
PR. Review adds `base_sha`, `review_id`, and `findings` (empty for PASS). Planning
adds `created_issues` (at most two actual verified issue numbers). Use BLOCKED for
missing capabilities/decisions, CHANGES_REQUESTED for specific fixes. Do not write
PASS for an acceptance gate the available observations cannot establish.
Complete required commands synchronously and write the receipt before returning.
An idle turn without a receipt is a failed stage; background notification waits
cannot keep it active. Workers report independently verified local results and
material limitations; the controller waits for hosted CI before integration.

Runtime state is atomic and process-locked. A persisted launch intent and unique
thread title reconcile a crash after BB accepted a spawn, preventing duplicate
workers. Three unsuccessful stages park an issue; quota waits do not. Stages have
a four-hour time limit. Preserve interrupted diffs and commits. Pending questions
are left pending; absence of an answer is never approval. Finished planning and
confirmed merged jobs release their registered threads/worktrees after receipts
are copied into runtime state. Partial/unmerged work is retained.

Transient CLI/GitHub/authentication failures are recorded and retried on later
ticks; launcher errors remain visible in BB automation output without triggering
its three-failure automatic pause. A separate five-minute health automation
reports changed obstacles and resumes only this controller's unexpectedly paused
schedule while configuration says enabled. It never starts model work directly,
never resumes an explicit configuration pause, and never touches the old review
automation or other projects. The server/host must be running to execute ticks.

## Install and operate

Run from the server-host project checkout in a BB thread. Keep configuration and
runtime outside git, for example in that thread's storage. The following is an
example; use the explicitly agreed provider pair and merge policy:

```sh
python3 tools/install_dispatch.py --providers claude-code codex \
  --state-dir /absolute/thread-storage/war3-continuous
```

Default installation creates **paused** controller/health schedules. `--activate`
enables them and `--auto-merge` authorizes routine accepted merges. Activation
checks that the bootstrap instructions exist on `origin/main`, so workers do not
start under obsolete guidance. Re-running updates only the saved two automation
IDs; private script snapshots are refreshed explicitly by installation.

```sh
python3 tools/dispatch.py inspect --config /absolute/runtime/config.json
python3 tools/dispatch.py tick --config /absolute/runtime/config.json
python3 tools/dispatch_health.py --config /absolute/runtime/config.json
python3 tools/dispatch.py resume-issue --issue 30 --config /absolute/runtime/config.json
python3 tools/dispatch.py resume-planning --config /absolute/runtime/config.json
```

`inspect` checks real admission without spawning/stopping anything. Resume an issue
or planning only after resolving its recorded obstacle. `state.json`, `health.json`
and the two automations' BB run output report actual execution. Credential values,
emails and account IDs are excluded from controller quota snapshots.

To pause deliberately, set `enabled` to `false` in the runtime config and execute
one tick to stop registered model work, then pause both saved automation IDs with
`bb automation pause <id> --project <project>`. To resume, reinstall with the chosen
flags or set enabled true and resume those two IDs. Do not merely pause the
controller while health still has an enabled policy: health will restore it.

Tests: `python3 -m unittest discover -s tools -p 'test_dispatch.py' -v`.
They use fake BB/GitHub responses and no real provider requests. Live installation
and captures need separately recorded evidence; passing controller tests are not
gameplay compatibility results.

# Continuous-development bootstrap verification

8 October 2026. BB CLI **0.45.0**, native ARM Mac. This verifies controller policy
and deployment plumbing, not new Warcraft gameplay or rendering fidelity.

- `python3 -m unittest discover -s tools -p 'test_dispatch*.py'`: **36/36 PASS**.
  Fakes exercise 80% short/weekly/family limits, missing/expired usage, alternating
  providers/fallback/reset resumption, preserved worktrees, pending questions,
  duplicate dispatch/crash recovery, changed issue scope, label removal, independent
  review/CI/head gates, paused installation and scoped health recovery.
- Full Python integrity suite: **126/126 PASS**.
- `python3 tools/run_ci.py --build build-continuous --compiler /usr/bin/clang++
  --config Release --archive`: **PASS**, CTest **3/3**, Python **121/121** at that
  run (five additional dispatcher controls were added afterward and passed in
  the full 126-test suite). Existing movement/collision gates and historical/P1
  observed-difference gates remain accepted. Build/logs remain outside git.
- [Live CLI smoke](cli-smoke.json): a real deferred pending thread was created,
  scoped pool bypass applied, then its one initial message was removed and its
  runtime stopped/archived. **Zero model requests** and no provisioned worktree.
- Real installation created only `auto_65ggaalon24` (minute controller) and
  `auto__bllxdvpplu` (five-minute health), both in this project and **paused**.
  Manual disabled-policy runs `arun_osdgvr4ihhq` and `arun_x28eha-kxio` finished
  exit 0, classified as silent skipped ticks. Updating installation retains the
  same IDs. Live admission preview reports measured local login usage without
  account identifiers. Shared pool threshold remains **0.98**.

Runtime configuration/state/script snapshots are in BB thread storage, outside
git. The paused provisional pair is Claude Code/Codex; Cursor is also supported
when BB exposes valid local usage windows. The final pair, activation and merge
policy await the user's requested clarification. No continuous product workers
have started, no new captures ran, no renderer was implemented, and hosted CI for
this change is not established by the local checks.

The cutoff is against reported usage before dispatch and each minute while
working. Reporting lag/in-flight requests can overshoot; this is not an exact
per-request 80.000% cap. Original assets/installations and credentials remain out
of git. See [the controller contract](../../docs/continuous-development.md).

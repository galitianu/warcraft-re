# Continuous-development bootstrap verification

8 October 2026. BB CLI **0.45.0**, native ARM Mac. This verifies controller policy
and deployment plumbing, not new Warcraft gameplay or rendering fidelity.

- `python3 -m unittest discover -s tools -p 'test_dispatch*.py'`: **50/50 PASS**.
  Fakes exercise 80% short/weekly/family limits, missing/expired usage, alternating
  providers/fallback/reset resumption, preserved worktrees, pending questions,
  duplicate dispatch/crash recovery, changed issue scope, label removal, independent
  review/CI/head gates, paused installation and scoped health recovery.
- Full Python integrity suite: **140/140 PASS**.
- `python3 tools/run_ci.py --build build-continuous --compiler /usr/bin/clang++
  --config Release --archive`: **PASS**, CTest **3/3**, Python **140/140** after the
  independently requested controller fixes. Existing movement/collision gates and historical/P1
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
git. The user selected Claude Code/Codex, total account usage and automatic merges
after independent review and CI. Deployment follows [PR #30](https://github.com/galitianu/warcraft-re/pull/30);
the runtime's live enabled state/receipts record actual activation and execution.
The installation checks above started no continuous product workers, ran no new
captures and implemented no renderer. Hosted CI is separate from local checks.
The first independent review reproduced native archival CI (CTest 3/3, Python
126/126, protected MOV gates), but ended waiting for a background CI notification
without a receipt. The controller rejected it. Worker instructions now require
synchronous completion and receipts before returning; hosted CI waits belong to
the controller. A fresh exact-head review is required after this change.

The next review reproduced an unconfirmed-stop handoff at the CLI boundary
([finding](https://github.com/galitianu/warcraft-re/pull/30#pullrequestreview-5457766191)).
Stops now require fresh thread/runtime confirmation. Six new negative controls
cover quota/restart, changed scope/lane ownership, timeout, idle receipt grading,
cleanup and active/starting/runtime status. Unconfirmed stops retain their
slot/worktree and retry on later ticks; quota stops still do not count as failure.
These controls use a fake CLI; no real subscription exhaustion or failed
interrupt is claimed. Deployment still requires fresh exact-head review and CI.

A later review found that retry backoff released a retained increment's lane
([finding](https://github.com/galitianu/warcraft-re/pull/30#pullrequestreview-5457925530)).
Retained revisions now reserve that lane until completion or explicit parking,
while the other lane continues. Three additional controls cover unsuccessful
implementation backoff, CHANGES_REQUESTED revisions and review quota handoffs
preserving the implementation predecessor. Native archival CI passes at 135 tests;
fresh exact-head review and hosted CI remain the deployment gate.

[Another review](https://github.com/galitianu/warcraft-re/pull/30#pullrequestreview-5458053853)
found lane metadata could release the original lane before a stop, and config
could replace the required CI list with an empty list. Launches now retain their
original lane; legacy active launches with unknown assignments reserve both until
confirmed release. The six compatibility checks are always a minimum; optional
configuration can add checks. Five new controls exercise lane changes/restarts,
legacy state, empty/subset CI configuration, additional checks and malformed
config. Native archival CI passes at 140 tests; independent review and hosted CI
still gate activation.

The cutoff is against reported usage before dispatch and each minute while
working. Reporting lag/in-flight requests can overshoot; this is not an exact
per-request 80.000% cap. Original assets/installations and credentials remain out
of git. See [the controller contract](../../docs/continuous-development.md).

# Self-hosted compatibility CI

Owner decision, 15 October 2026: Linux x64 executes on `nas-pc`; macOS ARM64
executes on the Mac mini. Windows/MSVC is temporarily disabled. The active gate
requires AppleClang Release/Debug, GCC Release, Clang Debug, and **Compare measured
build scopes**, all under the unchanged `Primitive compatibility` workflow name.
Missing or failed active checks still prevent integration. These infrastructure
changes establish no new WC3 gameplay compatibility.

The workflow uses repository-scoped labels `war3-ci,war3-linux` and
`war3-ci,war3-mac`, in addition to GitHub's OS/architecture labels. It has no
GitHub-hosted fallback. One runner per machine bounds concurrency. Linux uses
Ubuntu's Python 3.12, CMake, Ninja, GCC and Clang. macOS uses the system
AppleClang and Homebrew CMake/Ninja/Python 3.12. The Mac runner's private `.path`
prepends Homebrew's Python 3.12 `libexec/bin`; the user's normal Python selection
is unchanged. A preflight rejects a different Python minor version. GitHub's
setup-python action is not used: its macOS package assumes `/Users/runner`.

The repository is public at installation time. Fork pull requests are excluded
from these jobs, and approval is required for **all external contributors**.
Never approve untrusted fork workflow execution. Checkout does not persist its
GitHub token. The Linux service runs as the separate `war3-ci` user without sudo
or Docker membership; it cannot read the BB user's home. Runner credentials,
service files, workspaces and machine configuration remain outside git.

## Services

Linux runner: `war3-nas-pc-linux`, installed at `/opt/war3-ci/runner`, owned by
`war3-ci`. GitHub's `svc.sh` installs a systemd service which starts at boot:

```sh
cd /opt/war3-ci/runner
sudo ./svc.sh status
sudo ./svc.sh start
sudo ./svc.sh stop
```

Mac runner: `war3-andreis-mini-mac`, installed in this controller's private BB
thread storage under `war3-ci/runner-mac`. Its launchd user service starts when
the user logs in. Run `./svc.sh status|start|stop` from that directory. The Mac
must be awake and logged in; Linux must be online. GitHub's runner application
updates itself. GitHub Actions still supplies scheduling and artifact storage;
self-hosting removes the dependency on GitHub-hosted compute minutes.

The Mac's container VM is not used for CI. WC3/rdpipe and its Windows VM remain
capture tools; routine CI does not run the original game.

The owner also requested a Claude worker on `nas-pc`. Its existing local Claude
login is used without transferring credentials. The private controller's
`review_hosts` override directs Claude reviews to an isolated Linux worktree,
checks usage on that machine, and retrieves its receipt and actual git state
through BB. This is distinct from the unprivileged GitHub runner account.
GitHub-authenticated CLI operations use the Mac through machine-scoped BB
terminals; the Linux agent does not receive the Mac's GitHub token.

## Evidence and scope

Every active job builds and executes its native architecture and retains the
existing evidence bundle. The comparison clears previous downloaded evidence
before downloading the current run's artifacts. It requires all four active
configurations, regrades their traces and reports Windows as disabled/unobserved.
No fixture, comparator tolerance or observed gameplay failure is relaxed.

For historical five-configuration artifacts, explicitly pass
`--include-windows` to `tools/summarize_ci.py`. This requires all five; it does
not enable Windows in the live workflow. To restore live Windows coverage,
provision a Windows x64/MSVC runner, restore the workflow matrix entry, restore
the default summary requirement, and add its check back to `dispatch.CHECKS`
together. Independently review that migration.

## Recovery

Check repository Settings → Actions → Runners for both online runners. A queued
job with no matching runner is an infrastructure block, not a numerical pass.
Read actual job logs before retrying. Restart only the affected runner service;
never cancel unrelated BB threads or another project's jobs.

After a workflow change reaches main, an already-open PR must integrate that
main and receive a fresh independent review. Re-running an old workflow uses its
old runner labels and does not migrate it. Resume a parked dispatcher issue only
after its recorded obstacle is resolved. Refresh the controller's private
`dispatch.py` snapshot when deploying a reviewed gate-policy change; source
edits alone do not change the installed scheduler.

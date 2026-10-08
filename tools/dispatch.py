#!/usr/bin/env python3
"""Project-scoped BB development controller. No shared BB settings are mutated.

GitHub issues are the queue. JSON here is execution bookkeeping, not a task DB.
Run `tick` from a BB script automation; `inspect` is read-only admission preview.
"""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'war3:auto'
MARKER = re.compile(r'<!--\s*war3-dispatch\s+(\{.*?\})\s*-->', re.S)
SHA = re.compile(r'^[0-9a-f]{40}$')
LIVE = {'pending', 'starting', 'active', 'stopping'}
CHECKS = ['macOS ARM64 AppleClang Release', 'macOS ARM64 AppleClang Debug',
          'Linux x64 GCC Release', 'Linux x64 Clang Debug',
          'Windows x64 MSVC Release', 'Compare measured build scopes']


class ControlError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ControlError(message)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)


def stamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, 'reset time has no timezone')
        return parsed.timestamp()
    except (ValueError, AttributeError, TypeError) as error:
        raise ControlError('invalid quota reset time') from error


def quota_gate(report, now, threshold=80, families=()):
    """Fail closed for unknown/expired data; no reset is invented from the clock."""
    if not isinstance(report, dict) or report.get('status') != 'ok':
        return {'eligible': False, 'reason': 'usage unavailable'}
    windows = report.get('windows')
    if not isinstance(windows, list) or not windows:
        return {'eligible': False, 'reason': 'no measured usage windows'}
    if not all(isinstance(w, dict) for w in windows):
        return {'eligible': False, 'reason': 'invalid usage windows'}
    selected = [w for w in windows if not w.get('model') or not families or
                str(w['model']).lower() in families]
    if not selected or not any(not w.get('model') for w in selected):
        return {'eligible': False, 'reason': 'no account-wide usage window'}
    measured = []
    try:
        for window in selected:
            used = window.get('usedPercent')
            require(type(used) in (int, float) and math.isfinite(used) and 0 <= used <= 100,
                    'invalid usage percentage')
            reset = stamp(window.get('resetsAt'))
            require(reset > now, 'usage window expired; await a fresh observation')
            measured.append({'kind': window.get('kind'), 'used_percent': used,
                             'resets_at': window['resetsAt'], 'model': window.get('model')})
    except ControlError as error:
        return {'eligible': False, 'reason': str(error)}
    return {'eligible': all(w['used_percent'] < threshold for w in measured),
            'reason': 'below cutoff' if all(w['used_percent'] < threshold for w in measured)
                      else '80% cutoff reached', 'windows': measured}


def choose_provider(providers, preferred, gates):
    order = [preferred] + [p for p in providers if p != preferred]
    return next((p for p in order if gates.get(p, {}).get('eligible')), None)


def issue_spec(issue):
    matches = MARKER.findall(issue.get('body') or '')
    require(len(matches) == 1, f"issue #{issue['number']}: one dispatch marker required")
    try:
        spec = json.loads(matches[0])
    except ValueError as error:
        raise ControlError('invalid issue dispatch JSON') from error
    require(isinstance(spec, dict) and set(spec) == {'lane', 'depends_on'},
            'dispatch marker needs lane and depends_on only')
    require(spec['lane'] in {'mechanics', 'client'}, 'invalid lane')
    require(isinstance(spec['depends_on'], list) and all(type(n) is int and n > 0
            for n in spec['depends_on']), 'invalid issue dependencies')
    require(issue['number'] not in spec['depends_on'], 'issue depends on itself')
    for heading in ('## Question', '## Acceptance', '## Scope'):
        require(heading in issue['body'], f'issue needs {heading}')
        require(issue['body'].split(heading, 1)[1].split('\n## ', 1)[0].strip(),
                f'empty {heading}')
    return spec


def issue_digest(issue):
    return hashlib.sha256(issue['body'].encode('utf-8')).hexdigest()


def validate_config(config):
    required = {'project', 'machine', 'repository', 'checkout', 'state_dir', 'providers',
                'auto_merge', 'enabled', 'max_workers', 'threshold_percent', 'base_branch'}
    require(required <= set(config), f'missing config: {sorted(required - set(config))}')
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', config['repository']), 'invalid repository')
    require(len(config['providers']) == 2 and len(set(config['providers'])) == 2,
            'configure exactly two distinct alternating providers')
    require(set(config['providers']) <= {'claude-code', 'codex', 'acp-cursor'},
            'configure a provider with measurable BB subscription usage')
    require(config['threshold_percent'] == 80, 'this project uses an 80% cutoff')
    require(type(config['max_workers']) is int and 1 <= config['max_workers'] <= 3,
            'max_workers must be 1..3')
    require(type(config['enabled']) is bool and type(config['auto_merge']) is bool,
            'enabled and auto_merge must be boolean')
    if 'required_checks' in config:
        require(isinstance(config['required_checks'], list) and
                all(isinstance(name, str) and name.strip() for name in config['required_checks']),
                'additional required_checks must be a list of nonempty names')
    for key in ('checkout', 'state_dir'):
        require(Path(config[key]).is_absolute(), f'{key} must be absolute')
    require(Path(config['checkout']).is_dir(), 'checkout does not exist')
    require(not Path(config['state_dir']).resolve().is_relative_to(Path(config['checkout']).resolve()),
            'runtime state must live outside the checkout')
    require(re.fullmatch(r'[\w./-]+', config['base_branch']), 'invalid base branch')
    return config


class CLI:
    def __init__(self, checkout):
        self.checkout = checkout
        self.bb_path = os.environ.get('BB_CLI') or 'bb'

    def call(self, args, *, input_text=None, accepted=(0,), timeout=45, json_output=True,
             allowed_errors=()):
        command = [self.bb_path if args[0] == 'bb' else args[0], *args[1:]]
        if json_output:
            command.append('--json')
        try:
            result = subprocess.run(command, cwd=self.checkout, input=input_text, text=True,
                                    capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ControlError(f'{args[0]} {args[1]} failed: {type(error).__name__}') from error
        # Do not echo stdout: quota results contain account identities, and failed
        # CLI tools may include secret configuration in their diagnostics.
        if not json_output:
            require(result.returncode in accepted,
                    f'{args[0]} {args[1]} exited {result.returncode}; inspect CLI diagnostics')
            return result.stdout
        try:
            value = json.loads(result.stdout)
        except ValueError as error:
            raise ControlError(f'{args[0]} {args[1]} returned invalid JSON') from error
        if isinstance(value, dict) and value.get('ok') is False:
            if value.get('error', {}).get('code') in allowed_errors:
                return value
            raise ControlError(f'{args[0]} {args[1]} rejected request')
        require(result.returncode in accepted,
                f'{args[0]} {args[1]} exited {result.returncode}; inspect CLI diagnostics')
        return value

    def bb(self, *args, **kwargs):
        return self.call(['bb', *args], **kwargs)

    def gh(self, *args, **kwargs):
        return self.call(['gh', *args], **kwargs)

    def api(self, endpoint):
        return self.gh('api', endpoint, json_output=False)

    def git(self, path, *args):
        try:
            result = subprocess.run(['git', '-C', str(path), *args], text=True,
                                    capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ControlError('worktree verification unavailable') from error
        require(result.returncode == 0, 'worktree git verification failed')
        return result.stdout.strip()


class Dispatcher:
    def __init__(self, config, state, cli, save, now=None):
        self.c, self.s, self.cli, self.save = config, state, cli, save
        self.now = time.time() if now is None else now
        self.events = []
        self.root = Path(config['state_dir'])
        self.repo = config['repository']

    def event(self, message):
        self.events.append(message)

    def persist(self):
        self.save(self.s)

    def gates(self):
        try:
            reports = self.cli.bb('settings', 'usage', '--machine', self.c['machine'])
        except ControlError:
            reports = {}  # Unknown usage stops only registered workers.
        if not isinstance(reports, dict):
            reports = {}
        gates = {p: quota_gate(reports.get(p), self.now, self.c['threshold_percent'],
                             tuple(self.c.get('quota_families', {}).get(p, [])))
                 for p in self.c['providers']}
        self.s['quota'] = gates  # Deliberately excludes emails and account keys.
        self.s['last_tick_at'] = self.now
        return gates

    def thread(self, launch):
        result = self.cli.bb('thread', 'show', launch['thread'])
        thread, environment = result['thread'], result.get('environment')
        require(thread['projectId'] == self.c['project'] and
                thread['providerId'] == launch['provider'] and
                thread['title'] == launch['title'], 'registered thread identity changed')
        if not environment and thread['status'] in {'pending', 'starting'}:
            return thread
        require(environment and environment['hostId'] == self.c['machine'] and
                environment['projectId'] == self.c['project'], 'registered environment changed')
        if launch.get('environment'):
            require(environment['id'] == launch['environment'], 'worktree identity changed')
        launch['environment'] = environment['id']
        launch['path'] = environment.get('path')
        if launch['stage'] == 'implement':
            # Preserve the environment even if the stage never writes a usable
            # receipt (crash, timeout, dirty tree, authentication interruption).
            self.s['jobs'][str(launch['issue'])].update(
                environment=environment['id'], previous_thread=launch['thread'])
        # show returns the stored thread; list also supplies the derived pending
        # interaction flag. An unanswered question must not look like a failed,
        # idle stage and cause another worker to be dispatched.
        rows = self.cli.bb('thread', 'list', '--project', self.c['project'],
                           '--environment', environment['id'])
        thread['hasPendingInteraction'] = any(t['id'] == launch['thread'] and
                                              t.get('hasPendingInteraction') for t in rows)
        self.persist()
        return thread

    def cancel_queue(self, launch):
        self.cli.bb('provider-retry', 'cancel', launch['thread'], allowed_errors=('no_pending_retry',))
        for queued in self.cli.bb('thread', 'queue', 'list', launch['thread']):
            self.cli.bb('thread', 'queue', 'delete', launch['thread'], queued['id'])

    def stop(self, launch):
        self.thread(launch)  # Recheck ownership immediately before every stop.
        self.cancel_queue(launch)
        self.cli.bb('thread', 'stop', launch['thread'])
        thread = self.thread(launch)  # A successful CLI call can leave stopping.
        executing = {'starting', 'active', 'stopping'}
        confirmed = (thread['status'] not in executing and
                     (thread.get('runtime') or {}).get('displayStatus') not in executing)
        if not confirmed:
            self.event(f"Stop unconfirmed for {launch['thread']}; ownership retained.")
        return confirmed

    def request_stop(self, launch, action):
        if action == 'cleanup':
            launch['stop_prior_state'] = launch['state']
            launch['state'] = 'running'  # Keep its slot until runtime release.
        launch['stop_action'] = action
        self.persist()  # Preserve the reason across failed interrupts/restarts.
        return self.complete_stop(launch)

    def complete_stop(self, launch):
        if not self.stop(launch):
            return False
        action = launch['stop_action']
        if action == 'cleanup':
            # Keep the action durable if archive fails after runtime release.
            self.cli.bb('thread', 'archive', launch['thread'])
        launch.pop('stop_action')
        if action == 'receipt':
            self.finish_receipt(launch)
        elif action == 'timeout':
            launch['state'] = 'failed'
            self.stage_failure(launch, ['Stage time limit; inspect partial work.'])
        elif action == 'cleanup':
            launch['state'] = launch.pop('stop_prior_state')
            launch['settled'] = True
        else:
            require(action in {'quota', 'park'}, 'unknown stop disposition')
            launch['state'] = 'quota_paused' if action == 'quota' else 'cancelled'
            if action == 'quota':
                self.event(f"Stopped registered worker {launch['thread']} at quota/unavailability; work retained.")
        self.persist()
        return True

    def prompt(self, launch):
        stage, number = launch['stage'], launch.get('issue')
        receipt = f"local/dispatch/{launch['token']}.json"
        common = f"""You are a registered worker of the Warcraft III continuous dispatcher.
Read AGENTS.md, README.md, PROGRESS.md, docs/next-roadmap.md and
docs/continuous-development.md. Follow the assigned bounded stage only.
Do not spawn threads/subagents, create goals/automations, change BB settings,
or merge. Use the question tool for genuine user decisions. Preserve all partial
work if interrupted; the controller handles quota waits and provider handoffs.
Repository: {self.repo}. Stage: {stage}. Run ID: {launch['token']}.
Write your final JSON receipt atomically to {receipt} (outside git), then return.
Receipt common fields: run_id, stage, status, summary, checks (array of strings),
limitations (array of strings). Status is PASS, CHANGES_REQUESTED, or BLOCKED.
Verify every assertion. Include material limitations, not invented passes.
Complete required tool commands synchronously. Do not end a turn waiting for a
background task/notification: idle means the stage ended, and no receipt means
failure. Write the supported receipt before returning. Do not wait for hosted CI;
the controller checks it after independent review and before integration.
"""
        if stage == 'plan':
            return common + f"""
GitHub issues are the sole queue. Inspect open/closed issues and merged PRs.
Plan at most TWO narrow, useful next increments, one per lane if needed, from the
earliest unfinished milestone. Keep P3 ahead of P2; defer P1. Do not repeat delivered
work or duplicate open issues. New issues must have ## Question, ## Acceptance,
## Scope (including limits), and exactly one marker:
<!-- war3-dispatch {{"lane":"mechanics" or "client","depends_on":[issue numbers]}} -->
Use the existing {LABEL} label. Dependencies must be genuinely required.
Create issues with gh issue create --body-file, then retrieve and validate them.
Product changes are outside this stage. Receipt adds created_issues (array of
actual new issue numbers). If the roadmap's gates are met, or a user decision
blocks all useful work, report BLOCKED with evidence; never invent busywork.
"""
        job = self.s['jobs'][str(number)]
        extra = f"\nIssue #{number}: retrieve its current body with gh issue view.\n"
        if launch.get('previous_thread'):
            extra += (f"Continue work from @thread:{launch['previous_thread']}. Read its output, "
                      "git status, prior receipts and actual artifacts; do not discard work.\n")
        if stage == 'implement':
            return common + extra + f"""
Implement the issue through its acceptance gate in this isolated worktree.
If this is a revision, resolve these recorded findings: {json.dumps(job.get('findings', []))}
Use permanent, previously unused experiment IDs; commit predictions/design before
capture. Use the existing oracle/CI tools, and the rdpipe lease for all capture.
Keep native/headless builds independent of the renderer. Run relevant checks;
update PROGRESS.md concisely and document actual scope/evidence.
Commit focused changes, push this worktree's branch and open/update ONE PR targeting
{self.c['base_branch']}. Include `Closes #{number}` and the exact marker
<!-- war3-job:{number} --> in its body. Never merge it. When updating a PR, integrate
the current origin/{self.c['base_branch']} without discarding changes; all acceptance
and CI must still hold on the new head. Set a ready PR only after local checks pass.
PASS receipt adds issue (number), pr_number (integer), head_sha (full commit SHA).
BLOCKED includes issue and specific missing capability/decision/partial work.
"""
        return common + extra + f"""
Independently review PR #{job['pr']} at EXACT head {job['head']} against base
{launch['base_sha']}. Your worktree starts at the PR head; verify it. Read the full
diff and acceptance/evidence, run appropriate independent checks, and identify
P3/P2/P1 differences. Do not modify product code or fix the author's branch.
Confirm genuine WC3 provenance, held-out predictions where needed, no relaxed
tolerances, appropriate client input/replay evidence, and protected gates.
If the PR changes, report BLOCKED; a stale approval is unusable.
Post one COMMENT review bound to that exact commit with findings/validation and
marker <!-- war3-review:{launch['token']} -->, using gh api --input with a JSON file.
This is a COMMENT, not a GitHub approval by the PR author's own account.
PASS requires acceptance demonstrated with no unresolved blocking findings.
Receipt adds issue, pr_number, head_sha, base_sha, review_id (actual GitHub review
ID), and findings (array of strings; empty only when no blocking issues remain).
Report CHANGES_REQUESTED for concrete fixes or BLOCKED for missing information.
"""

    def launch(self, stage, provider, *, number=None, environment=None, base_sha=None,
               previous_thread=None):
        if not environment:
            ref = (f"refs/pull/{self.s['jobs'][str(number)]['pr']}/head" if stage == 'review'
                   else self.c['base_branch'])
            self.cli.git(self.c['checkout'], 'fetch', 'origin', ref)
        token = uuid.uuid4().hex
        title = f'[war3-auto:{token}] {stage}' + (f' #{number}' if number else '')
        launch = {'token': token, 'title': title, 'stage': stage, 'provider': provider,
                  'issue': number, 'environment': environment, 'base_sha': base_sha,
                  'previous_thread': previous_thread, 'created_at': self.now,
                  'state': 'intent'}
        if number:
            launch['issue_sha'] = self.s['jobs'][str(number)].get('body_sha')
            launch['lane'] = self.s['jobs'][str(number)]['lane']
        self.s['launches'][token] = launch
        if number:
            self.s['jobs'][str(number)].update(
                state='reviewing' if stage == 'review' else 'implementing', launch=token)
        self.persist()  # Intent survives a crash/timeout after BB accepted spawn.
        args = ['thread', 'spawn', '--project', self.c['project'], '--provider', provider,
                '--title', title, '--prompt-file', '-', '--permission-mode',
                'full' if provider == 'acp-cursor' else 'auto',
                '--send-at', '2099-01-01T00:00:00Z']
        if environment:
            args += ['--environment', environment]
        else:
            ref = self.s['jobs'][str(number)]['head'] if stage == 'review' else f"origin/{self.c['base_branch']}"
            args += ['--machine', self.c['machine'], '--new-environment', 'worktree',
                     '--base-branch', ref]
        if self.c.get('models', {}).get(provider):
            args += ['--model', self.c['models'][provider]]
        # Spawn deferred: no provider request can run before thread-local bypass.
        # Dispatch only after identity, bypass and quota have been checked again.
        created = self.cli.bb(*args, input_text=self.prompt(launch), timeout=90)
        launch['thread'] = created['id']
        launch['state'] = 'pending_bypass'
        self.persist()
        self.start_pending(launch)
        return launch

    def start_pending(self, launch):
        # A deferred pending thread has no environment until dispatch.
        result = self.cli.bb('thread', 'show', launch['thread'])['thread']
        require(result['projectId'] == self.c['project'] and
                result['providerId'] == launch['provider'] and result['title'] == launch['title'],
                'pending thread identity mismatch')
        if launch['provider'] in {'claude-code', 'codex'}:
            self.cli.bb('pool', 'bypass', launch['thread'])
        gates = self.gates()
        if not self.c['enabled'] or not gates[launch['provider']]['eligible']:
            self.request_stop(launch, 'quota')
            return
        rows = self.cli.bb('thread', 'queue', 'list', launch['thread'])
        require(len(rows) == 1, 'expected one deferred initial message')
        # Persist before send; a crash after acceptance must never resend it.
        launch['state'] = 'running'
        self.s['next_provider'] = next(p for p in self.c['providers'] if p != launch['provider'])
        self.persist()
        self.cli.bb('thread', 'queue', 'send', launch['thread'], rows[0]['id'])
        self.event(f"Started {launch['stage']} {launch['thread']} with {launch['provider']}.")

    def recover_intents(self):
        intents = [l for l in self.s['launches'].values() if l['state'] == 'intent']
        if not intents:
            return
        threads = self.cli.bb('thread', 'list', '--project', self.c['project'], '--include-hidden')
        for launch in intents:
            found = [t for t in threads if t['projectId'] == self.c['project'] and
                     t.get('title') == launch['title']]
            require(len(found) <= 1, 'duplicate dispatch token; manual reconciliation needed')
            if found:
                launch.update(thread=found[0]['id'], state='pending_bypass')
            else:
                # Unknown spawn outcome: do not manufacture a second request. A
                # later tick may discover it; after an hour, surface the obstacle.
                if self.now - launch['created_at'] > 3600:
                    launch['state'] = 'blocked'
                    if launch['issue']:
                        self.s['jobs'][str(launch['issue'])].update(state='blocked', findings=[
                            'Spawn outcome unresolved; inspect BB before resuming the issue.'])
                    self.event('Unresolved spawn intent; inspect BB before clearing it.')
            self.persist()

    def receipt(self, launch):
        if not launch.get('path'):
            return None
        # All selected workers are on this server-host checkout's machine.
        path = Path(launch['path']) / 'local' / 'dispatch' / f"{launch['token']}.json"
        if not path.exists():
            return None
        require(path.stat().st_size <= 65536, 'oversized worker receipt')
        try:
            result = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise ControlError('invalid worker receipt') from error
        require(isinstance(result, dict) and result.get('run_id') == launch['token'] and
                result.get('stage') == launch['stage'], 'receipt run/stage mismatch')
        require(result.get('status') in {'PASS', 'CHANGES_REQUESTED', 'BLOCKED'},
                'invalid receipt status')
        require(isinstance(result.get('summary'), str) and result['summary'].strip(),
                'receipt summary missing')
        for name in ('checks', 'limitations'):
            require(isinstance(result.get(name), list) and
                    all(isinstance(v, str) for v in result[name]), f'invalid {name}')
        if launch['stage'] != 'plan':
            require(result.get('issue') == launch['issue'], 'receipt issue mismatch')
        if result['status'] == 'PASS' and launch['stage'] != 'plan':
            require(type(result.get('pr_number')) is int and result['pr_number'] > 0,
                    'receipt PR missing')
            require(isinstance(result.get('head_sha'), str) and SHA.fullmatch(result['head_sha']),
                    'receipt commit missing')
            require(bool(result['checks']), 'PASS must name verification actually performed')
            require(self.cli.git(launch['path'], 'rev-parse', 'HEAD') == result['head_sha'],
                    'receipt commit is not the actual worktree HEAD')
            require(not self.cli.git(launch['path'], 'status', '--porcelain', '--untracked-files=normal'),
                    'PASS worktree has uncommitted files')
        return result

    def pr(self, number):
        return json.loads(self.cli.api(f'repos/{self.repo}/pulls/{number}'))

    def base(self):
        ref = json.loads(self.cli.api(f"repos/{self.repo}/git/ref/heads/{self.c['base_branch']}"))
        return ref['object']['sha']

    def accept_receipt(self, launch, result):
        if launch['stage'] == 'plan':
            created = result.get('created_issues', [])
            require(isinstance(created, list) and len(created) <= 2 and
                    all(type(n) is int and n > 0 for n in created), 'invalid planned issues')
            for number in created:
                issue = self.cli.gh('issue', 'view', str(number), '--repo', self.repo,
                                    '--json', 'number,title,body,labels,state', json_output=False)
                issue = json.loads(issue)
                issue_spec(issue)
                require(LABEL in {l['name'] for l in issue['labels']}, 'planned issue not eligible')
            if result['status'] != 'PASS' or not created:
                self.s['planning_blocked'] = result['summary']
            self.s['last_plan_at'] = self.now
        else:
            job = self.s['jobs'][str(launch['issue'])]
            if result['status'] == 'BLOCKED':
                job.update(state='blocked', findings=[result['summary']])
            elif result['status'] == 'CHANGES_REQUESTED':
                self.failure(job, result.get('findings') or [result['summary']])
            else:
                pr = self.pr(result['pr_number'])
                require(pr['state'] == 'open' and not pr['draft'] and
                        pr['base']['ref'] == self.c['base_branch'] and
                        pr['head']['repo']['full_name'].lower() == self.repo.lower() and
                        pr['head']['sha'] == result['head_sha'] and
                        f"<!-- war3-job:{launch['issue']} -->" in (pr['body'] or ''),
                        'PR is stale or outside this job/repository/base')
                if launch['stage'] == 'implement':
                    job.update(state='review_ready', pr=pr['number'], head=pr['head']['sha'],
                               environment=launch['environment'], author_thread=launch['thread'])
                else:
                    require(job['pr'] == result['pr_number'] and job['head'] == result['head_sha'],
                            'review targets another job/head')
                    require(result.get('base_sha') == launch['base_sha'] and
                            result.get('findings') == [], 'PASS review needs current base and no findings')
                    require(type(result.get('review_id')) is int, 'GitHub review ID missing')
                    review = json.loads(self.cli.api(
                        f"repos/{self.repo}/pulls/{job['pr']}/reviews/{result['review_id']}"))
                    require(review['commit_id'] == job['head'] and review['state'] == 'COMMENTED' and
                            f"<!-- war3-review:{launch['token']} -->" in (review['body'] or ''),
                            'independent review not posted at the graded commit')
                    require(launch['thread'] != job['author_thread'], 'author cannot review own stage')
                    job.update(state='integration_ready', review=result,
                               reviewed_base=launch['base_sha'])
            job['last_receipt'] = result
        launch.update(state='finished', receipt=result)
        self.persist()
        self.event(f"Finished {launch['stage']} {launch['thread']}: {result['status']}.")

    def settle_finished(self):
        for launch in self.s['launches'].values():
            done_job = launch.get('issue') and self.s['jobs'][str(launch['issue'])]['state'] == 'done'
            done_plan = launch['stage'] == 'plan' and launch['state'] == 'finished'
            if not launch.get('settled') and launch['state'] not in {'running', 'intent', 'pending_bypass'}:
                if done_job or done_plan:
                    # Receipt is already copied to controller storage; confirmed
                    # merged work/finished planning can release its worktree.
                    if not launch.get('thread'):
                        continue
                    # Deferred quota stops may never have provisioned a worktree.
                    # Cleanup still checks the exact registered thread identity.
                    thread = self.cli.bb('thread', 'show', launch['thread'])['thread']
                    require(thread['projectId'] == self.c['project'] and
                            thread['providerId'] == launch['provider'] and
                            thread['title'] == launch['title'], 'cleanup identity changed')
                    self.request_stop(launch, 'cleanup')

    def failure(self, job, findings):
        job['attempts'] = job.get('attempts', 0) + 1
        job['findings'] = findings
        job['state'] = 'blocked' if job['attempts'] >= 3 else 'implement_ready'
        job['retry_after'] = self.now + min(1800, 120 * 2 ** job['attempts'])

    def park(self, job, reason):
        job.update(state='blocked', findings=[reason])
        self.persist()
        for launch in self.s['launches'].values():
            if launch['issue'] == job['issue'] and launch['state'] in {'running', 'pending_bypass'}:
                self.request_stop(launch, 'park')
                if launch['stage'] == 'implement':
                    job['environment'] = launch.get('environment')
                    job['previous_thread'] = launch['thread']
        self.persist()

    def stage_failure(self, launch, findings):
        if launch['issue']:
            self.failure(self.s['jobs'][str(launch['issue'])], findings)
        else:
            self.s['last_plan_at'] = self.now
            self.s['plan_failures'] = self.s.get('plan_failures', 0) + 1
            if self.s['plan_failures'] >= 3:
                self.s['planning_blocked'] = 'Three planning stages failed; inspect worker output.'

    def finish_receipt(self, launch):
        try:
            result = self.receipt(launch)
            if result:
                self.accept_receipt(launch, result)
                return
        except ControlError as error:
            self.event(f"Rejected receipt from {launch['thread']}: {error}.")
        launch['state'] = 'failed'
        self.stage_failure(launch, ['Previous stage ended without a valid receipt; inspect partial work.'])
        self.persist()

    def reconcile(self, gates):
        self.recover_intents()
        for launch in list(self.s['launches'].values()):
            if launch.get('stop_action'):
                self.complete_stop(launch)
                continue  # No grading or handoff while a stop is unconfirmed.
            if launch['state'] == 'pending_bypass':
                self.start_pending(launch)
            if launch['state'] != 'running':
                continue
            thread = self.thread(launch)
            if thread.get('hasPendingInteraction'):
                continue  # No model work; keep the user's unanswered decision pending.
            if thread['status'] == 'pending':
                # A CLI timeout after queue-send acceptance must not strand the
                # initial deferred message. Retry the EXISTING queue row only;
                # never create another input. Check quota before touching it.
                rows = self.cli.bb('thread', 'queue', 'list', launch['thread'])
                if rows and self.c['enabled'] and gates[launch['provider']]['eligible']:
                    require(len(rows) == 1, 'unexpected pending worker messages')
                    self.cli.bb('thread', 'queue', 'send', launch['thread'], rows[0]['id'])
                    continue
            if thread['status'] not in LIVE:
                # Provider-retry rows may outlive an errored turn. Cancel them
                # before another stage is allowed to use this worktree.
                self.request_stop(launch, 'receipt')
            elif not self.c['enabled'] or not gates[launch['provider']]['eligible']:
                self.request_stop(launch, 'quota')
            elif self.now - launch['created_at'] > self.c.get('stage_timeout_seconds', 14400):
                self.request_stop(launch, 'timeout')
        # Quota stops do not count as unsuccessful attempts.
        for launch in self.s['launches'].values():
            if launch['state'] == 'quota_paused':
                if launch['issue']:
                    job = self.s['jobs'][str(launch['issue'])]
                    job['state'] = 'review_ready' if launch['stage'] == 'review' else 'implement_ready'
                    if launch['stage'] == 'implement':
                        job['previous_thread'] = launch['thread']
                launch['state'] = 'retained'
                self.persist()

    def integration(self, job):
        pr = self.pr(job['pr'])
        if pr.get('merged'):
            job['state'] = 'done'
            self.persist()
            return
        if pr['state'] != 'open':
            job.update(state='blocked', findings=['PR closed without merge.'])
            self.persist()
            return
        if pr['head']['sha'] != job['head']:
            job.update(state='implement_ready', findings=['PR head changed after review; verify and resubmit.'])
            self.persist()
            return
        current_base = self.base()
        comparison = json.loads(self.cli.api(f"repos/{self.repo}/compare/{current_base}...{job['head']}"))
        if comparison['merge_base_commit']['sha'] != current_base:
            job.update(state='implement_ready', findings=['Integrate current main and rerun acceptance/CI.'])
            self.persist()
            return
        if current_base != job['reviewed_base']:
            job['state'] = 'review_ready'
            self.persist()
            return
        checks = self.cli.gh('pr', 'checks', str(job['pr']), '--repo', self.repo,
                             '--json', 'name,state,bucket,workflow', accepted=(0, 1, 8),
                             json_output=False)
        checks = json.loads(checks)
        named = {c['name']: c for c in checks if c.get('workflow') == 'Primitive compatibility'}
        required = list(dict.fromkeys(CHECKS + self.c.get('required_checks', [])))
        if any(name not in named for name in required):
            return  # Absence of required checks is never success.
        if any(named[name]['bucket'] in {'fail', 'cancel'} for name in required):
            self.failure(job, ['Required CI failed/cancelled; inspect actual logs and fix.'])
            self.persist()
            return
        if any(c['bucket'] != 'pass' for c in checks):
            return
        if pr['draft'] or pr.get('mergeable') is not True or pr.get('mergeable_state') != 'clean':
            return
        if not self.c['auto_merge']:
            job['state'] = 'awaiting_merge'
            self.persist()
            self.event(f"PR #{job['pr']} independently accepted with passing CI; awaiting your merge.")
            return
        # Recheck both immutable head and moving base immediately before merge.
        latest = self.pr(job['pr'])
        if latest['head']['sha'] != job['head'] or self.base() != current_base:
            return
        self.cli.gh('pr', 'merge', str(job['pr']), '--repo', self.repo, '--squash',
                    '--match-head-commit', job['head'], json_output=False, timeout=60)
        merged = self.pr(job['pr'])
        require(merged.get('merged') is True, 'merge not confirmed')
        job.update(state='done', merge_commit=merged['merge_commit_sha'])
        self.persist()
        self.event(f"Merged accepted PR #{job['pr']} at {job['merge_commit']}.")

    def tick(self):
        gates = self.gates()
        self.reconcile(gates)
        if not self.c['enabled']:
            self.persist()
            return self.events
        issues = json.loads(self.cli.gh('issue', 'list', '--repo', self.repo, '--state', 'open',
                            '--label', LABEL, '--limit', '100', '--json', 'number,title,body,labels',
                            json_output=False))
        require(len(issues) < 100, 'issue queue exceeds bounded page; refine query before dispatch')
        open_numbers = {i['number'] for i in issues}
        for job in self.s['jobs'].values():
            if job['issue'] not in open_numbers and job['state'] not in {'done', 'blocked'}:
                if job.get('pr') and self.pr(job['pr']).get('merged'):
                    job['state'] = 'done'
                    self.persist()
                    continue
                self.park(job, 'Issue closed or auto label removed; partial work retained.')
        for issue in issues:
            key = str(issue['number'])
            try:
                spec = issue_spec(issue)
            except ControlError as error:
                self.s.setdefault('queue_errors', {})[key] = str(error)
                if key in self.s['jobs']:
                    self.park(self.s['jobs'][key], 'Issue metadata invalid; repair it before resumption.')
                continue  # One malformed issue must not stall the other lane.
            if key not in self.s['jobs']:
                self.s['jobs'][key] = {'issue': issue['number'], 'lane': spec['lane'],
                                      'depends_on': spec['depends_on'], 'state': 'implement_ready',
                                      'body_sha': issue_digest(issue)}
            elif self.s['jobs'][key].get('body_sha') not in {None, issue_digest(issue)}:
                job = self.s['jobs'][key]
                self.park(job, 'Issue scope changed; re-establish acceptance on the current issue.')
                job.update(state='implement_ready', body_sha=issue_digest(issue),
                           lane=spec['lane'], depends_on=spec['depends_on'])
            elif self.s['jobs'][key]['state'] == 'implement_ready':
                self.s['jobs'][key].update(lane=spec['lane'], depends_on=spec['depends_on'],
                                          body_sha=issue_digest(issue))
            self.s.get('queue_errors', {}).pop(key, None)
        for job in list(self.s['jobs'].values()):
            if job['state'] in {'integration_ready', 'awaiting_merge'}:
                self.integration(job)
        self.settle_finished()
        self.persist()
        running = [l for l in self.s['launches'].values() if l['state'] in
                   {'running', 'intent', 'pending_bypass'}]
        free = self.c['max_workers'] - len(running)
        active_issues = {l['issue'] for l in running}
        # Entire unfinished jobs occupy their lane, keeping core/client edits focused.
        occupied = {j['lane'] for j in self.s['jobs'].values() if j['state'] not in
                    {'done', 'blocked', 'implement_ready'}}
        for launch in running:
            if launch['issue']:
                # Mutable issue metadata cannot release the old worker's lane.
                # Legacy launches without an assignment reserve both until stop.
                occupied.update([launch['lane']] if launch.get('lane') in {'client', 'mechanics'}
                                else ['client', 'mechanics'])
        # A revision/backoff retains its increment's lane even between turns.
        # If recovering an older state with several retained jobs, drain the
        # oldest first; fresh issues cannot overtake retained work.
        reserved = {}
        for job in sorted(self.s['jobs'].values(), key=lambda j: j['issue']):
            if job['state'] == 'implement_ready' and any(job.get(k) for k in
                    ('pr', 'environment', 'previous_thread', 'attempts')):
                reserved.setdefault(job['lane'], job['issue'])
        eligible = []
        for job in self.s['jobs'].values():
            if (job['issue'] not in open_numbers or str(job['issue']) in self.s.get('queue_errors', {}) or
                    job['issue'] in active_issues or
                    job.get('retry_after', 0) > self.now):
                continue
            if job['state'] not in {'implement_ready', 'review_ready'}:
                continue
            if job['state'] == 'implement_ready' and (job['lane'] in occupied or
                    reserved.get(job['lane'], job['issue']) != job['issue']):
                continue
            dependencies_closed = True
            for dep in job['depends_on']:
                state = json.loads(self.cli.api(f'repos/{self.repo}/issues/{dep}'))['state']
                if state != 'closed':
                    dependencies_closed = False
            if dependencies_closed:
                eligible.append(job)
        eligible.sort(key=lambda j: (j['state'] != 'review_ready', j['issue']))
        for job in eligible:
            if free <= 0:
                break
            provider = choose_provider(self.c['providers'], self.s['next_provider'], gates)
            if provider is None:
                break
            if job['state'] == 'implement_ready' and job['lane'] in occupied:
                continue
            if job['state'] == 'review_ready':
                latest = self.pr(job['pr'])
                if latest['head']['sha'] != job['head']:
                    job.update(state='implement_ready', findings=['PR changed before review; refresh receipt.'])
                    self.persist()
                    continue
                base = self.base()
                launch = self.launch('review', provider, number=job['issue'], base_sha=base)
            else:
                launch = self.launch('implement', provider, number=job['issue'],
                                     environment=job.get('environment'),
                                     previous_thread=job.get('previous_thread'))
            job['state'] = 'reviewing' if launch['stage'] == 'review' else 'implementing'
            job['launch'] = launch['token']
            self.persist()
            occupied.add(job['lane'])
            free -= 1
        unfinished = [j for j in self.s['jobs'].values() if j['issue'] in open_numbers and
                      j['state'] not in {'done', 'blocked'}]
        if (not eligible and not running and not unfinished and free > 0 and
                not self.s.get('planning_blocked') and
                self.now - self.s.get('last_plan_at', 0) > 600):
            provider = choose_provider(self.c['providers'], self.s['next_provider'], gates)
            if provider:
                self.launch('plan', provider)
        self.persist()
        return self.events


def new_state(config):
    return {'version': 1, 'project': config['project'], 'repository': config['repository'],
            'next_provider': config['providers'][0], 'jobs': {}, 'launches': {}}


@contextlib.contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'controller.lock').open('a+b') as file:
        if os.name == 'nt':
            import msvcrt
            if file.tell() == 0:
                file.write(b'0')
                file.flush()
            file.seek(0)
            acquire = lambda: msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            acquire()
        except OSError:
            yield False
            return
        yield True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['tick', 'inspect', 'resume-issue', 'resume-planning'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--issue', type=int)
    args = parser.parse_args(argv)
    config = validate_config(json.loads(args.config.read_text(encoding='utf-8')))
    root = Path(config['state_dir'])
    cli = CLI(config['checkout'])
    if args.command == 'inspect':
        reports = cli.bb('settings', 'usage', '--machine', config['machine'])
        print(json.dumps({'enabled': config['enabled'], 'auto_merge': config['auto_merge'],
                          'project': config['project'], 'cutoff': 80,
                          'providers': {p: quota_gate(reports.get(p), time.time(), 80,
                              tuple(config.get('quota_families', {}).get(p, [])))
                              for p in config['providers']}}, indent=2))
        return 0
    with locked(root) as acquired:
        if not acquired:
            return 0
        path = root / 'state.json'
        state = json.loads(path.read_text()) if path.exists() else new_state(config)
        require(state['version'] == 1 and state['project'] == config['project'] and
                state['repository'] == config['repository'], 'runtime state identity mismatch')
        save = lambda s: atomic_json(path, s)
        if args.command == 'resume-issue':
            require(args.issue and str(args.issue) in state['jobs'], 'known --issue required')
            job = state['jobs'][str(args.issue)]
            require(job['state'] == 'blocked', 'only blocked issues need explicit resumption')
            job.update(state='implement_ready', attempts=0, retry_after=0)
            save(state)
            return 0
        if args.command == 'resume-planning':
            state.pop('planning_blocked', None)
            state.update(plan_failures=0, last_plan_at=0)
            save(state)
            return 0
        try:
            events = Dispatcher(config, state, cli, save).tick()
            state.pop('last_error', None)
            save(state)
            for event in events:
                print(event)
        except (ControlError, OSError, ValueError, KeyError, TypeError) as error:
            # Keep cron alive through transient failures; persist an observable
            # health record instead of triggering BB's three-failure auto-pause.
            state['last_error'] = {'at': time.time(), 'type': type(error).__name__, 'message': str(error)}
            save(state)
            print(f'Dispatcher waiting: {error}', file=sys.stderr)
        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ControlError, OSError, ValueError, KeyError, TypeError) as error:
        print(f'Dispatcher configuration error: {error}', file=sys.stderr)
        sys.exit(2)

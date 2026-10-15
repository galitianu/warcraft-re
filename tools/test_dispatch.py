"""Policy/lifecycle negative controls; these never launch an agent or touch GitHub."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

from dispatch import (CHECKS, CLI, ControlError, Dispatcher, choose_provider, issue_spec,
                      locked, new_state, quota_gate, validate_config)

NOW = 1791464400
HEAD = 'a' * 40
BASE = 'b' * 40


def usage(percent=0, reset='2026-10-09T12:00:00Z'):
    return {'status': 'ok', 'windows': [
        {'kind': 'five-hour', 'usedPercent': percent, 'resetsAt': reset},
        {'kind': 'weekly', 'usedPercent': 10, 'resetsAt': '2026-10-15T12:00:00Z'}]}


def issue(number=30, lane='client', depends=()):
    return {'number': number, 'title': 'Bounded issue', 'labels': [{'name': 'war3:auto'}],
            'body': '## Question\nCan orders replay?\n## Acceptance\nRecorded replay matches.\n'
                    '## Scope\nOne unit.\n<!-- war3-dispatch ' +
                    json.dumps({'lane': lane, 'depends_on': list(depends)}) + ' -->'}


class FakeCLI:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.reports = {'claude-code': usage(), 'codex': usage()}
        self.threads = {}
        self.queue = {}
        self.issues = []
        self.pr_data = {'number': 40, 'state': 'open', 'draft': False,
                        'base': {'ref': 'main'},
                        'head': {'sha': HEAD, 'repo': {'full_name': 'owner/warcraft'}},
                        'body': '<!-- war3-job:30 -->', 'merged': False,
                        'mergeable': True, 'mergeable_state': 'clean'}
        self.base_sha = BASE
        self.merge_base = BASE
        self.checks = [{'name': n, 'bucket': 'pass', 'workflow': 'Primitive compatibility'} for n in CHECKS]
        self.review = {'commit_id': HEAD, 'state': 'COMMENTED', 'body': '<!-- war3-review:test -->'}
        self.fail_usage = False
        self.fail_after_spawn = False
        self.dirty = False
        self.stop_status = 'idle'

    def bb(self, *args, **kwargs):
        self.calls.append(('bb', args, kwargs))
        if args[:2] == ('settings', 'usage'):
            if self.fail_usage:
                raise ControlError('collector offline')
            return copy.deepcopy(self.reports)
        if args[:2] == ('thread', 'spawn'):
            number = len(self.threads) + 1
            tid = f'thr_{number}'
            title = args[args.index('--title') + 1]
            provider = args[args.index('--provider') + 1]
            eid = args[args.index('--environment') + 1] if '--environment' in args else f'env_{number}'
            path = self.root / eid
            path.mkdir(exist_ok=True)
            self.threads[tid] = {'thread': {'id': tid, 'projectId': 'proj', 'providerId': provider,
                                           'title': title, 'status': 'pending'},
                                 'environment': {'id': eid, 'projectId': 'proj', 'hostId': 'host',
                                                 'path': str(path)}}
            self.queue[tid] = [{'id': 'queued_initial'}]
            if self.fail_after_spawn:
                self.fail_after_spawn = False
                raise ControlError('timeout after server accepted spawn')
            return {'id': tid}
        if args[:2] == ('thread', 'show'):
            return copy.deepcopy(self.threads[args[2]])
        if args[:2] == ('thread', 'list'):
            return [copy.deepcopy(v['thread']) for v in self.threads.values()]
        if args[:3] == ('thread', 'queue', 'list'):
            return copy.deepcopy(self.queue.get(args[3], []))
        if args[:3] == ('thread', 'queue', 'send'):
            self.queue[args[3]] = []
            self.threads[args[3]]['thread']['status'] = 'active'
            return {'delivery': 'sent'}
        if args[:3] == ('thread', 'queue', 'delete'):
            self.queue[args[3]] = []
            return {}
        if args[:2] == ('thread', 'stop'):
            self.threads[args[2]]['thread']['status'] = self.stop_status
            return {}
        if args[:2] == ('thread', 'archive'):
            return {}
        if args[0] in {'pool', 'provider-retry'}:
            return {}
        raise AssertionError(args)

    def gh(self, *args, **kwargs):
        self.calls.append(('gh', args, kwargs))
        if args[:2] == ('issue', 'list'):
            return json.dumps(self.issues)
        if args[:2] == ('pr', 'checks'):
            return json.dumps(self.checks)
        if args[:2] == ('pr', 'merge'):
            self.pr_data.update(merged=True, merge_commit_sha='c' * 40)
            return ''
        if args[:2] == ('issue', 'view'):
            return json.dumps(next(i for i in self.issues if str(i['number']) == args[2]))
        raise AssertionError(args)

    def api(self, endpoint):
        self.calls.append(('api', endpoint, {}))
        if '/reviews/' in endpoint:
            return json.dumps(self.review)
        if '/pulls/' in endpoint:
            return json.dumps(self.pr_data)
        if '/git/ref/' in endpoint:
            return json.dumps({'object': {'sha': self.base_sha}})
        if '/compare/' in endpoint:
            return json.dumps({'merge_base_commit': {'sha': self.merge_base}})
        if '/issues/' in endpoint:
            return json.dumps({'state': 'closed'})
        raise AssertionError(endpoint)

    def git(self, path, *args):
        if args[0] == 'fetch':
            return ''
        if args[:2] == ('rev-parse', 'HEAD'):
            return HEAD
        if args[0] == 'status':
            return ' M product.cpp' if self.dirty else ''
        raise AssertionError(args)


class QuotaTests(unittest.TestCase):
    def test_cutoff_every_window_and_alternation_fallback(self):
        for percent, expected in [(0, True), (79.99, True), (80, False), (100, False)]:
            self.assertEqual(quota_gate(usage(percent), NOW)['eligible'], expected)
        report = usage()
        report['windows'][1]['usedPercent'] = 80
        self.assertFalse(quota_gate(report, NOW)['eligible'])
        providers = ['claude-code', 'codex']
        gates = {p: quota_gate(usage(), NOW) for p in providers}
        self.assertEqual(choose_provider(providers, 'claude-code', gates), 'claude-code')
        gates['claude-code'] = quota_gate(usage(80), NOW)
        self.assertEqual(choose_provider(providers, 'claude-code', gates), 'codex')
        gates['codex'] = quota_gate(usage(80), NOW)
        self.assertIsNone(choose_provider(providers, 'claude-code', gates))

    def test_unknown_expired_invalid_usage_is_never_free_allowance(self):
        for report in [None, {}, {'status': 'error'}, {'status': 'ok', 'windows': []},
                       usage(reset='2026-10-07T12:00:00Z'), usage(float('nan')),
                       usage(-1), usage(True), usage(reset='tomorrow'),
                       {'status': 'ok', 'windows': [None]}]:
            with self.subTest(report=report):
                self.assertFalse(quota_gate(report, NOW)['eligible'])
        # A fresh observed window unlocks work, not the expired window's timestamp.
        self.assertTrue(quota_gate(usage(), NOW)['eligible'])

    def test_family_bucket_only_excludes_known_unrequested_family(self):
        report = usage()
        report['windows'].append({'model': 'opus', 'usedPercent': 80,
                                 'resetsAt': '2026-10-15T12:00:00Z'})
        self.assertFalse(quota_gate(report, NOW)['eligible'])
        self.assertFalse(quota_gate(report, NOW, families=('opus',))['eligible'])
        self.assertTrue(quota_gate(report, NOW, families=('sonnet',))['eligible'])


class CLIErrorTests(unittest.TestCase):
    def test_no_pending_native_retry_is_a_valid_noop(self):
        error = {'ok': False, 'error': {'code': 'no_pending_retry'}}
        with patch('dispatch.subprocess.run', return_value=CompletedProcess([], 1, json.dumps(error), '')):
            value = CLI('.').bb('provider-retry', 'cancel', 'owned',
                                allowed_errors=('no_pending_retry',))
        self.assertEqual(value, error)

    def test_authentication_errors_are_not_swallowed_as_missing_retries(self):
        error = {'ok': False, 'error': {'code': 'authentication_failed'}}
        with patch('dispatch.subprocess.run', return_value=CompletedProcess([], 1, json.dumps(error), '')):
            with self.assertRaises(ControlError):
                CLI('.').bb('provider-retry', 'cancel', 'owned', allowed_errors=('no_pending_retry',))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        checkout = self.root / 'checkout'
        checkout.mkdir()
        self.config = {'project': 'proj', 'machine': 'host', 'repository': 'owner/warcraft',
                       'checkout': str(checkout), 'state_dir': str(self.root / 'state'),
                       'providers': ['claude-code', 'codex'], 'enabled': True,
                       'auto_merge': True, 'threshold_percent': 80, 'max_workers': 2,
                       'base_branch': 'main'}
        self.state = new_state(self.config)
        self.cli = FakeCLI(self.root)
        self.saves = []
        self.d = Dispatcher(self.config, self.state, self.cli,
                            lambda s: self.saves.append(copy.deepcopy(s)), now=NOW)

    def job(self, **values):
        job = {'issue': 30, 'lane': 'client', 'depends_on': [], 'state': 'implement_ready',
               'pr': 40, 'head': HEAD, 'reviewed_base': BASE, 'author_thread': 'author'}
        job.update(values)
        self.state['jobs']['30'] = job
        return job

    def launch(self):
        self.job()
        return self.d.launch('implement', 'claude-code', number=30)

    def receipt(self, launch, **values):
        self.d.thread(launch)
        result = {'run_id': launch['token'], 'stage': launch['stage'], 'status': 'PASS',
                  'summary': 'Acceptance demonstrated', 'checks': ['Independent replay check passed'],
                  'limitations': [], 'issue': 30, 'pr_number': 40, 'head_sha': HEAD}
        result.update(values)
        path = Path(launch['path']) / 'local' / 'dispatch' / f"{launch['token']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result))
        self.cli.threads[launch['thread']]['thread']['status'] = 'idle'
        return result

    def test_deferred_spawn_bypass_before_any_model_request_and_persisted_alternation(self):
        launch = self.launch()
        actions = [args[:3] for name, args, _ in self.cli.calls if name == 'bb']
        self.assertLess(actions.index(('pool', 'bypass', launch['thread'])),
                        actions.index(('thread', 'queue', 'send')))
        spawn = next(args for name, args, _ in self.cli.calls if name == 'bb' and args[:2] == ('thread', 'spawn'))
        self.assertIn('2099-01-01T00:00:00Z', spawn)
        self.assertEqual(self.state['next_provider'], 'codex')
        self.assertEqual(self.state['jobs']['30']['state'], 'implementing')
        self.assertEqual(self.saves[0]['launches'][launch['token']]['state'], 'intent')
        self.assertFalse(any(name == 'bb' and args[:2] in [('pool', 'config'),
                             ('concurrency-limit', 'global')] for name, args, _ in self.cli.calls))

    def test_cursor_uses_its_native_account_without_shared_pool_mutation(self):
        self.config['providers'] = ['claude-code', 'acp-cursor']
        self.cli.reports['acp-cursor'] = usage()
        self.job()
        launch = self.d.launch('implement', 'acp-cursor', number=30)
        self.assertEqual(launch['state'], 'running')
        self.assertFalse(any(name == 'bb' and args[0] == 'pool' for name, args, _ in self.cli.calls))
        spawn = next(args for name, args, _ in self.cli.calls if name == 'bb' and args[:2] == ('thread', 'spawn'))
        self.assertEqual(spawn[spawn.index('--permission-mode') + 1], 'full')

    def test_crash_after_accepted_spawn_recovers_one_thread_without_duplicate_request(self):
        self.job()
        self.cli.fail_after_spawn = True
        with self.assertRaises(ControlError):
            self.d.launch('implement', 'claude-code', number=30)
        self.d.reconcile(self.d.gates())
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(len(self.state['launches']), 1)
        self.assertEqual(next(iter(self.state['launches'].values()))['state'], 'running')

    def test_duplicate_ticks_do_not_spawn_second_worker(self):
        self.cli.issues = [issue()]
        self.d.tick()
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)

    def test_unconfirmed_quota_stop_retains_ownership_until_confirmed_after_restart(self):
        self.cli.issues = [issue()]
        launch = self.launch()
        self.cli.reports['claude-code'] = usage(80)
        self.cli.stop_status = 'stopping'
        self.d.tick()
        self.assertEqual(launch['state'], 'running')
        self.assertEqual(launch['stop_action'], 'quota')
        self.assertEqual(self.state['jobs']['30']['state'], 'implementing')
        # A controller restart and refreshed allowance cannot bypass the old stop.
        self.d = Dispatcher(self.config, self.state, self.cli, lambda s: None, now=NOW + 60)
        self.cli.reports['claude-code'] = usage()
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(self.state['jobs']['30'].get('attempts', 0), 0)
        self.cli.stop_status = 'idle'
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 2)
        self.assertEqual(self.cli.threads['thr_2']['environment']['id'], 'env_1')
        self.assertEqual(self.cli.threads['thr_1']['thread']['status'], 'idle')
        self.assertEqual(self.state['jobs']['30'].get('attempts', 0), 0)

    def test_unconfirmed_scope_stop_reserves_lane_even_when_job_is_ready(self):
        self.cli.issues = [issue()]
        self.d.tick()
        launch = next(iter(self.state['launches'].values()))
        self.cli.stop_status = 'stopping'
        self.cli.issues[0]['body'] += '\nA revised acceptance gate.\n'
        self.cli.issues.append(issue(31))
        self.d.tick()
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(launch['stop_action'], 'park')
        self.cli.stop_status = 'idle'
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 2)
        self.assertEqual(self.cli.threads['thr_2']['environment']['id'], 'env_1')
        self.assertEqual(launch['state'], 'cancelled')

    def test_unconfirmed_timeout_does_not_count_failure_or_start_replacement(self):
        self.cli.issues = [issue()]
        launch = self.launch()
        self.d.now += 14401
        self.cli.stop_status = 'stopping'
        self.d.tick()
        self.assertEqual(launch['stop_action'], 'timeout')
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(self.state['jobs']['30'].get('attempts', 0), 0)
        self.cli.stop_status = 'idle'
        self.d.tick()
        self.assertEqual(launch['state'], 'failed')
        self.assertEqual(self.state['jobs']['30']['attempts'], 1)

    def test_idle_receipt_is_not_accepted_until_runtime_stop_is_confirmed(self):
        launch = self.launch()
        self.receipt(launch)
        self.cli.stop_status = 'stopping'
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['stop_action'], 'receipt')
        self.assertEqual(self.state['jobs']['30']['state'], 'implementing')
        self.assertNotIn('receipt', launch)
        self.cli.stop_status = 'idle'
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['state'], 'finished')
        self.assertEqual(self.state['jobs']['30']['state'], 'review_ready')

    def test_cleanup_keeps_slot_and_worktree_until_confirmed_stop(self):
        launch = self.launch()
        self.receipt(launch)
        self.d.reconcile(self.d.gates())
        self.state['jobs']['30']['state'] = 'done'
        self.cli.stop_status = 'stopping'
        self.d.settle_finished()
        self.assertEqual(launch['stop_action'], 'cleanup')
        self.assertEqual(launch['state'], 'running')
        self.assertFalse(any(args[:2] == ('thread', 'archive') for name, args, _ in self.cli.calls if name == 'bb'))
        self.cli.stop_status = 'idle'
        self.d.reconcile(self.d.gates())
        self.assertTrue(launch['settled'])
        self.assertEqual(launch['state'], 'finished')

    def test_active_starting_and_runtime_status_all_require_stop_confirmation(self):
        launch = self.launch()
        for status in ('active', 'starting', 'stopping'):
            with self.subTest(status=status):
                self.cli.stop_status = status
                self.assertFalse(self.d.stop(launch))
        self.cli.stop_status = 'idle'
        self.cli.threads[launch['thread']]['thread']['runtime'] = {'displayStatus': 'active'}
        self.assertFalse(self.d.stop(launch))
        self.cli.threads[launch['thread']]['thread']['runtime'] = {'displayStatus': 'idle'}
        self.assertTrue(self.d.stop(launch))

    def test_removed_label_stops_registered_work_and_retains_partial_work(self):
        self.cli.issues = [issue()]
        self.d.tick()
        self.cli.issues = []
        self.d.tick()
        self.assertEqual(self.cli.threads['thr_1']['thread']['status'], 'idle')
        self.assertEqual(self.state['jobs']['30']['state'], 'blocked')
        self.assertEqual(self.state['jobs']['30']['environment'], 'env_1')

    def test_changed_acceptance_invalidates_old_stage_and_continues_same_worktree(self):
        self.cli.issues = [issue()]
        self.d.tick()
        self.cli.issues[0]['body'] = self.cli.issues[0]['body'].replace('matches.', 'matches at 144 Hz.')
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 2)
        self.assertEqual(self.cli.threads['thr_1']['thread']['status'], 'idle')
        self.assertEqual(self.cli.threads['thr_2']['environment']['id'], 'env_1')

    def test_one_malformed_issue_does_not_stall_other_lane(self):
        self.cli.issues = [dict(issue(30), body='missing acceptance'), issue(31, lane='mechanics')]
        self.d.tick()
        self.assertIn('30', self.state['queue_errors'])
        self.assertEqual(len(self.cli.threads), 1)
        self.assertIn('#31', self.cli.threads['thr_1']['thread']['title'])

    def test_quota_stops_only_registered_worker_and_handoffs_same_worktree(self):
        self.cli.issues = [issue()]
        launch = self.launch()
        original_environment = self.cli.threads[launch['thread']]['environment']['id']
        self.cli.threads['unrelated'] = copy.deepcopy(self.cli.threads[launch['thread']])
        self.cli.threads['unrelated']['thread'].update(id='unrelated', projectId='another_project')
        self.cli.reports['claude-code'] = usage(80)
        self.d.tick()
        self.assertEqual(self.cli.threads['unrelated']['thread']['status'], 'active')
        replacement = [l for l in self.state['launches'].values() if l['state'] == 'running'][0]
        self.assertEqual(replacement['provider'], 'codex')
        self.assertEqual(replacement['environment'], original_environment)
        self.assertNotIn('attempts', self.state['jobs']['30'])

    def test_both_spent_wait_then_fresh_usage_resumes_without_user_action(self):
        self.cli.issues = [issue()]
        self.cli.reports = {p: usage(80) for p in self.config['providers']}
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 0)
        self.cli.reports['codex'] = usage(1)
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(next(iter(self.state['launches'].values()))['provider'], 'codex')

    def test_collector_failure_stops_owned_work_and_never_spawns(self):
        self.launch()
        self.cli.fail_usage = True
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)
        self.assertEqual(self.cli.threads['thr_1']['thread']['status'], 'idle')

    def test_wrong_project_identity_refuses_stop(self):
        launch = self.launch()
        self.cli.threads[launch['thread']]['thread']['projectId'] = 'unrelated'
        with self.assertRaises(ControlError):
            self.d.reconcile({p: {'eligible': False} for p in self.config['providers']})
        self.assertFalse(any(name == 'bb' and args[:2] == ('thread', 'stop')
                             for name, args, _ in self.cli.calls))

    def test_stale_worker_receipt_rejected_and_preserves_worktree_for_retry(self):
        launch = self.launch()
        self.receipt(launch, head_sha='d' * 40)
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['state'], 'failed')
        self.assertEqual(self.state['jobs']['30']['state'], 'implement_ready')
        self.assertEqual(self.state['jobs']['30']['attempts'], 1)
        self.assertEqual(self.state['jobs']['30']['environment'], 'env_1')
        self.assertEqual(self.state['jobs']['30']['previous_thread'], launch['thread'])

    def test_completed_receipt_moves_to_independent_review_before_quota_stop(self):
        launch = self.launch()
        self.receipt(launch)
        self.cli.queue[launch['thread']] = [{'id': 'native_retry'}]
        self.cli.reports['claude-code'] = usage(80)
        self.d.reconcile(self.d.gates())
        self.assertEqual(self.state['jobs']['30']['state'], 'review_ready')
        self.assertEqual(self.state['jobs']['30']['author_thread'], launch['thread'])
        self.assertEqual(self.cli.queue[launch['thread']], [])

    def test_dirty_worktree_cannot_be_accepted(self):
        launch = self.launch()
        self.receipt(launch)
        self.cli.dirty = True
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['state'], 'failed')
        self.assertEqual(self.state['jobs']['30']['state'], 'implement_ready')

    def test_review_checkout_is_head_while_receipt_grades_current_main(self):
        self.job(state='review_ready')
        self.cli.issues = [issue()]
        self.d.tick()
        launch = next(iter(self.state['launches'].values()))
        self.assertEqual(launch['base_sha'], BASE)
        spawn = next((args, kw) for name, args, kw in self.cli.calls
                     if name == 'bb' and args[:2] == ('thread', 'spawn'))
        self.assertEqual(spawn[0][spawn[0].index('--base-branch') + 1], HEAD)
        self.assertIn(f'against base\n{BASE}', spawn[1]['input_text'])

    def test_pending_user_question_is_preserved_without_retry(self):
        launch = self.launch()
        self.cli.threads[launch['thread']]['thread'].update(status='idle', hasPendingInteraction=True)
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['state'], 'running')
        self.assertNotIn('attempts', self.state['jobs']['30'])

    def test_three_unsuccessful_stages_park_issue(self):
        job = self.job()
        for _ in range(3):
            self.d.failure(job, ['Acceptance unresolved'])
        self.assertEqual(job['state'], 'blocked')

    def test_no_same_lane_concurrent_implementation(self):
        self.cli.issues = [issue(30), issue(31)]
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)

    def test_retained_implementation_reserves_lane_during_backoff(self):
        self.cli.issues = [issue(30), issue(31)]
        self.d.tick()
        launch = next(iter(self.state['launches'].values()))
        self.receipt(launch, head_sha='d' * 40)
        self.d.reconcile(self.d.gates())
        self.cli.issues.append(issue(32, lane='mechanics'))
        self.d.tick()
        running = [l['issue'] for l in self.state['launches'].values() if l['state'] == 'running']
        self.assertEqual(running, [32])  # Other lane continues; #31 cannot overtake.
        self.d.now = self.state['jobs']['30']['retry_after'] + 1
        self.d.tick()
        running = [l['issue'] for l in self.state['launches'].values() if l['state'] == 'running']
        self.assertEqual(running, [32, 30])
        self.assertEqual(self.cli.threads['thr_3']['environment']['id'], 'env_1')

    def test_changes_requested_reserves_lane_for_author_revision(self):
        self.cli.issues = [issue(30), issue(31)]
        self.job(state='review_ready', environment='author_env', previous_thread='author')
        launch = self.d.launch('review', 'claude-code', number=30, base_sha=BASE)
        self.receipt(launch, status='CHANGES_REQUESTED', findings=['Fix acceptance.'])
        self.d.reconcile(self.d.gates())
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 1)
        self.d.now = self.state['jobs']['30']['retry_after'] + 1
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 2)
        self.assertEqual(self.cli.threads['thr_2']['environment']['id'], 'author_env')
        self.assertEqual(self.state['jobs']['31']['state'], 'implement_ready')

    def test_review_quota_handoff_preserves_implementation_predecessor(self):
        job = self.job(state='review_ready', environment='author_env', previous_thread='author')
        launch = self.d.launch('review', 'claude-code', number=30, base_sha=BASE)
        self.cli.reports['claude-code'] = usage(80)
        self.d.reconcile(self.d.gates())
        self.assertEqual(launch['state'], 'retained')
        self.assertEqual(job['previous_thread'], 'author')
        self.assertEqual(job['environment'], 'author_env')
        self.assertEqual(job['state'], 'review_ready')

    def assert_changed_lane_waits_for_old_worker(self, legacy=False):
        self.cli.issues = [issue()]
        self.d.tick()
        launch = next(iter(self.state['launches'].values()))
        if legacy:
            launch.pop('lane')
        else:
            self.assertEqual(launch['lane'], 'client')
        self.cli.issues = [issue(30, lane='mechanics'), issue(31)]
        self.cli.stop_status = 'stopping'
        self.d.tick()
        self.state = json.loads(json.dumps(self.state))
        self.d = Dispatcher(self.config, self.state, self.cli, lambda s: None, now=NOW + 60)
        self.d.tick()
        self.assertEqual(self.state['jobs']['30']['lane'], 'mechanics')
        self.assertEqual(len(self.cli.threads), 1)
        self.cli.stop_status = 'idle'
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 3)
        self.assertEqual(self.cli.threads['thr_1']['thread']['status'], 'idle')
        self.assertEqual(self.cli.threads['thr_2']['environment']['id'], 'env_1')

    def test_changed_lane_reserves_original_assignment_until_stop(self):
        self.assert_changed_lane_waits_for_old_worker()

    def test_legacy_launch_with_unknown_lane_is_reserved_until_stop(self):
        self.assert_changed_lane_waits_for_old_worker(legacy=True)

    def test_configured_checks_cannot_remove_mandatory_ci_minimum(self):
        job = self.job(state='integration_ready')
        for configured in ([], [CHECKS[0]]):
            for present in ([], [self.cli.checks[0]]):
                with self.subTest(configured=configured, present=present):
                    self.config['required_checks'] = configured
                    original = self.cli.checks
                    self.cli.checks = present
                    self.d.integration(job)
                    self.assertFalse(self.cli.pr_data['merged'])
                    self.cli.checks = original

    def test_each_active_native_build_and_comparison_is_required(self):
        job = self.job(state='integration_ready')
        original = self.cli.checks
        for missing in CHECKS:
            with self.subTest(missing=missing):
                self.cli.checks = [check for check in original if check['name'] != missing]
                self.d.integration(job)
                self.assertFalse(self.cli.pr_data['merged'])
        self.cli.checks = original
        self.d.integration(job)
        self.assertTrue(self.cli.pr_data['merged'])

    def test_configured_checks_can_only_add_requirements(self):
        job = self.job(state='integration_ready')
        self.config['required_checks'] = ['Additional compatibility gate']
        self.d.integration(job)
        self.assertFalse(self.cli.pr_data['merged'])
        self.cli.checks.append({'name': 'Additional compatibility gate', 'bucket': 'pass',
                                'workflow': 'Primitive compatibility'})
        self.d.integration(job)
        self.assertTrue(self.cli.pr_data['merged'])

    def test_invalid_additional_check_config_fails_closed(self):
        for checks in (None, 'a check', {}, [''], [False]):
            with self.subTest(checks=checks):
                self.config['required_checks'] = checks
                with self.assertRaises(ControlError):
                    validate_config(self.config)

    def test_no_planner_busywork_while_issue_awaits_manual_merge(self):
        self.job(state='awaiting_merge')
        self.config['auto_merge'] = False
        self.cli.issues = [issue()]
        self.d.tick()
        self.assertEqual(len(self.cli.threads), 0)

    def test_advisory_and_missing_checks_cannot_replace_required_ci(self):
        job = self.job(state='integration_ready')
        self.cli.checks = [{'name': 'some green check', 'bucket': 'pass', 'workflow': 'Other'}]
        self.d.integration(job)
        self.assertFalse(any(name == 'gh' and args[:2] == ('pr', 'merge') for name, args, _ in self.cli.calls))

    def test_current_review_all_ci_and_head_pinning_required_for_merge(self):
        job = self.job(state='integration_ready')
        self.d.integration(job)
        merge = next(args for name, args, _ in self.cli.calls if name == 'gh' and args[:2] == ('pr', 'merge'))
        self.assertEqual(merge[-2:], ('--match-head-commit', HEAD))
        self.assertNotIn('--admin', merge)
        self.assertEqual(job['state'], 'done')

    def test_main_advancement_invalidates_review_and_requires_integration(self):
        job = self.job(state='integration_ready')
        self.cli.base_sha = 'c' * 40
        self.d.integration(job)
        self.assertEqual(job['state'], 'implement_ready')
        self.assertFalse(any(name == 'gh' and args[:2] == ('pr', 'merge') for name, args, _ in self.cli.calls))

    def test_disabled_controller_stops_work_but_does_not_merge(self):
        self.job(state='integration_ready')
        self.config['enabled'] = False
        self.d.tick()
        self.assertFalse(any(name == 'gh' and args[:2] == ('pr', 'merge') for name, args, _ in self.cli.calls))

    def test_config_and_issue_admission_reject_unsafe_defaults(self):
        validate_config(self.config)
        for changes in [{'threshold_percent': 98}, {'providers': ['codex', 'codex']},
                        {'state_dir': self.config['checkout']}, {'auto_merge': 'yes'}]:
            with self.assertRaises(ControlError):
                validate_config(dict(self.config, **changes))
        self.assertEqual(issue_spec(issue())['lane'], 'client')
        with self.assertRaises(ControlError):
            issue_spec(issue(depends=[30]))
        with self.assertRaises(ControlError):
            issue_spec(dict(issue(), body='Do whatever is useful'))

    def test_process_lock_suppresses_overlapping_ticks(self):
        with locked(self.root / 'locks') as first:
            self.assertTrue(first)
            with locked(self.root / 'locks') as second:
                self.assertFalse(second)


if __name__ == '__main__':
    unittest.main()

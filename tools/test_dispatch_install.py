"""Install/health contracts, using isolated files and no real BB mutations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from dispatch import ControlError
from dispatch_health import health
from install_dispatch import install, launcher
from test_dispatch import NOW


class InstallationCLI:
    def __init__(self):
        self.records = {}
        self.calls = []
        self.fail_health_once = False
        self.labels = []

    def bb(self, *args, **kwargs):
        self.calls.append(args)
        if args[:2] == ('automation', 'list'):
            return list(copy.deepcopy(self.records).values())
        if args[:2] == ('automation', 'create'):
            name = args[args.index('--name') + 1]
            if self.fail_health_once and 'health' in name:
                self.fail_health_once = False
                raise ControlError('temporary creation failure')
            ident = f'auto_{len(self.records) + 1}'
            value = {'id': ident, 'projectId': 'proj', 'name': name, 'enabled': False}
            self.records[ident] = value
            return copy.deepcopy(value)
        if args[:2] == ('automation', 'update'):
            return copy.deepcopy(self.records[args[2]])
        if args[:2] == ('automation', 'show'):
            return copy.deepcopy(self.records[args[2]])
        if args[:2] in {('automation', 'resume'), ('automation', 'pause')}:
            self.records[args[2]]['enabled'] = args[1] == 'resume'
            return {}
        raise AssertionError(args)

    def git(self, path, *args):
        if args[0] == 'fetch':
            return ''
        if args[0] == 'show':
            return 'obsolete instructions'
        raise AssertionError(args)

    def gh(self, *args, **kwargs):
        if args[:2] == ('label', 'list'):
            return json.dumps(self.labels)
        if args[:2] == ('label', 'create'):
            self.labels.append({'name': args[2]})
            return ''
        raise AssertionError(args)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        checkout = self.root / 'checkout'
        checkout.mkdir()
        self.config = {'project': 'proj', 'machine': 'host', 'repository': 'owner/warcraft',
                       'checkout': str(checkout), 'state_dir': str(self.root / 'state'),
                       'providers': ['claude-code', 'codex'], 'enabled': False,
                       'auto_merge': False, 'threshold_percent': 80, 'max_workers': 2,
                       'base_branch': 'main'}
        self.cli = InstallationCLI()

    def test_reinstallation_updates_same_two_project_schedules_and_stays_paused(self):
        first = install(self.config, self.cli)
        second = install(self.config, self.cli)
        self.assertEqual(first, second)
        self.assertEqual(len(self.cli.records), 2)
        self.assertTrue(all(not a['enabled'] for a in self.cli.records.values()))
        self.assertTrue(all(args[0] == 'automation' for args in self.cli.calls))
        wrapper = (Path(self.config['state_dir']) / 'controller-launcher.py').read_text()
        compile(wrapper, '<launcher>', 'exec')
        self.assertIn('"tick", "--config"', wrapper)

    def test_partial_install_recovers_without_duplicate_controller(self):
        self.cli.fail_health_once = True
        with self.assertRaises(ControlError):
            install(self.config, self.cli)
        record = json.loads((Path(self.config['state_dir']) / 'automations.json').read_text())
        self.assertEqual(record, {'controller': 'auto_1'})
        self.assertEqual(install(self.config, self.cli)['controller'], 'auto_1')
        self.assertEqual(len(self.cli.records), 2)

    def test_activation_refuses_old_worker_instructions_without_changing_installed_config(self):
        install(self.config, self.cli)
        before = (Path(self.config['state_dir']) / 'config.json').read_bytes()
        with self.assertRaises(ControlError):
            install(dict(self.config, enabled=True), self.cli)
        self.assertEqual((Path(self.config['state_dir']) / 'config.json').read_bytes(), before)
        self.assertTrue(all(not a['enabled'] for a in self.cli.records.values()))

    def test_health_respects_explicit_pause_and_resumes_only_its_own_controller(self):
        ids = install(self.config, self.cli)
        self.cli.calls.clear()
        self.assertEqual(health(self.config, self.cli, NOW), [])
        self.assertEqual(self.cli.calls, [])
        config = dict(self.config, enabled=True)
        messages = health(config, self.cli, NOW)
        self.assertTrue(self.cli.records[ids['controller']]['enabled'])
        self.assertFalse(self.cli.records[ids['health']]['enabled'])
        self.assertTrue(any('Resumed' in m for m in messages))

    def test_health_wrong_project_cannot_resume_automation(self):
        ids = install(self.config, self.cli)
        self.cli.records[ids['controller']]['projectId'] = 'other'
        self.cli.calls.clear()
        with self.assertRaises(ControlError):
            health(dict(self.config, enabled=True), self.cli, NOW)
        self.assertFalse(any(a[:2] == ('automation', 'resume') for a in self.cli.calls))

    def test_launcher_errors_leave_scheduler_alive(self):
        script = self.root / 'failure.py'
        script.write_text('raise SystemExit(2)\n')
        content = launcher(script, self.root / 'config.json')
        # No shell or script interpolation; an unsuccessful child cannot trigger
        # the scheduler's three-failure pause.
        self.assertNotIn('shell=True', content)
        exec(compile(content, '<test-launcher>', 'exec'), {})


if __name__ == '__main__':
    unittest.main()

"""Orchestration failure and evidence integrity tests; no guest/game in CI."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from capture_oracle import Controller, verify_installation
from capture_runs import capture
from normalize_generated import normalize
from trace_contract import BUILD, ROOT, generated_revision, load, sha256, shape
from we_author import clipboard_text


class CaptureTests(unittest.TestCase):
    def controller(self, temporary):
        return Controller(argparse.Namespace(out=Path(temporary) / 'bundle', total_deadline=900,
                          vm='012B6237-1E3E-40AE-9D80-2782BA75E69E', map_revision='MOV-0002-test'))

    def test_installation_machine_architecture_version_and_every_hash(self):
        expected = load(ROOT / f'oracle/environment/{BUILD}.json')
        actual = load(ROOT / 'oracle/environment/phase-6-verification.json')
        verify_installation(actual, expected, actual['machine'])
        for key, value in (('machine', 'another'), ('os_architecture', 'AMD64'), ('target', 'other')):
            changed = copy.deepcopy(actual)
            changed[key] = value
            with self.assertRaises(ValueError): verify_installation(changed, expected, actual['machine'])
        for index in range(7):
            changed = copy.deepcopy(actual)
            changed['files'][index]['sha256'] = '0'*64
            with self.assertRaises(ValueError): verify_installation(changed, expected, actual['machine'])
        for key, value in (('version', '1.30'), ('pe_machine', 34404)):
            changed = copy.deepcopy(actual)
            changed['files'][0][key] = value
            with self.assertRaises(ValueError): verify_installation(changed, expected, actual['machine'])

    def test_shapes_are_from_controls_and_paste_is_crlf(self):
        for exp in ('MOV-0002', 'MOV-0004', 'MOV-0006', 'MOV-0010'):
            label = exp + '-new-revision'
            self.assertTrue(generated_revision(label))
            self.assertEqual(shape(label), shape(exp + '-g1'))
        self.assertEqual(shape('MOV-0002-r2'), ('MOV-0002', 250, '0.020000', 2))
        with self.assertRaises(ValueError): shape('MOV-0013-new')
        self.assertEqual(clipboard_text(b'library\n', b'case\n'), 'library\r\n\r\ncase\r\n')
        with self.assertRaises(ValueError): clipboard_text(b'bad\r\n', b'case\n')

    def test_fresh_output_lease_contention_and_timeout_preserve_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            with self.assertRaises(FileExistsError): self.controller(tmp)
            with patch('capture_oracle.subprocess.run', return_value=subprocess.CompletedProcess([], 15, '', 'lease held')):
                with self.assertRaisesRegex(ValueError, 'lease held'):
                    driver.rdpipe('lease', 'acquire')
            self.assertFalse(driver.leased)
            with patch('capture_oracle.subprocess.run', side_effect=subprocess.TimeoutExpired(['rdpipe'], 1)):
                with self.assertRaisesRegex(RuntimeError, 'timed out'): driver.rdpipe('status', timeout=1)
            logs = sorted((driver.root / 'diagnostics').glob('*-command.json'))
            self.assertEqual(len(logs), 2)
            self.assertEqual(load(logs[-1])['error'], 'timeout')
            self.assertFalse((driver.root / 'report.json').exists())

    def test_transfer_tampering_and_remote_replacement_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            target = driver.root / 'run.txt'
            expected = 'a'*64
            def transfer(*args, **kwargs): target.write_text('altered bytes')
            with patch.object(driver, 'ps', return_value=expected), patch.object(driver, 'rdpipe', side_effect=transfer):
                with self.assertRaisesRegex(ValueError, 'retrieved bytes differ'): driver.pull('remote', target)
            target.unlink()
            with patch.object(driver, 'ps', side_effect=[expected, 'b'*64]), patch.object(driver, 'rdpipe', side_effect=transfer):
                with self.assertRaisesRegex(ValueError, 'transferred file differs'): driver.pull('remote', target)
            self.assertEqual(driver.journal['transfers'], [])

    def test_stop_only_owned_process_with_original_start_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            process = dict(pid=123, path='game.exe', start='999', role='game-1')
            driver.active = [process]
            with patch.object(driver, 'ps') as ps:
                driver.stop(123)
                script = ps.call_args.args[0]
                self.assertIn('PID reused', script)
                self.assertIn('999', script)
                self.assertIn('game.exe', script)
                self.assertNotIn('Get-Process -Name', script)
                self.assertFalse(driver.active)
            with self.assertRaises(StopIteration): driver.stop(987)

    def test_lease_renewal_and_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            driver.leased = True
            driver.renewed = 0
            with patch.object(driver, 'command', return_value='') as command:
                driver.renew()
                self.assertIn('acquire', command.call_args.args[0])
                driver.cleanup()
                self.assertIn('release', command.call_args.args[0])
            self.assertFalse(driver.leased)

    def test_incomplete_or_stale_capture_cannot_count_as_fresh_run(self):
        class Fake:
            stops = []
            def stage(self, name): pass
            def assert_hash(self, *args): pass
            def ps(self, script, **kwargs):
                if 'Remove-Item' in script:
                    raise RuntimeError('stale output remains')
                return ''
            def launch(self, *args): return 7
            def stop(self, pid): self.stops.append(pid)
            def pause(self, seconds): pass
            def note(self, *args): pass
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_path = root / 'map.w3m'
            map_path.write_bytes(b'map')
            fake = Fake()
            with self.assertRaisesRegex(RuntimeError, 'stale output'):
                capture(fake, 'MOV-0002-test', map_path, root, deadline=.001)
            self.assertFalse((root / 'runs.json').exists())
            fake.ps = lambda *args, **kwargs: ''
            with self.assertRaisesRegex(RuntimeError, 'incomplete output'):
                capture(fake, 'MOV-0002-test', map_path, root, deadline=.001)
            self.assertEqual(fake.stops, [7])
            self.assertFalse((root / 'runs.json').exists())

    def test_candidate_normalization_rejects_saved_map_mismatch(self):
        # Exercise actual normalization on independent retained retail evidence.
        with tempfile.TemporaryDirectory() as tmp:
            import shutil
            root = Path(tmp)
            label = 'MOV-0002-g1'
            base = Path(f'oracle/captures/{BUILD}/{label}')
            manifest = load(ROOT / base / 'manifest.json')
            for key in ('map', 'library', 'case', 'environment', 'scenario', 'generation', 'verification'):
                path = Path(manifest[key]['path'])
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, root / path)
            (root / base).mkdir(parents=True)
            for path in (ROOT / base).iterdir():
                if path.is_file(): shutil.copyfile(path, root / base / path.name)
            self.assertEqual(normalize(label, root / 'candidate', root)['status'], 'PASS')
            manifest['check_map']['sha256'] = '0'*64
            (root / base / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'saved-map verification'):
                normalize(label, root / 'rejected', root)
            self.assertFalse((root / 'rejected').exists())

    def test_stopped_vm_start_and_unresponsive_running_guest_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            driver.args.guest_deadline = .005
            driver.args.machine = 'selected'
            driver.leased = False
            # A stopped selected VM may be started. An unresponsive already-running
            # VM must fail without stop/reset commands.
            for state in ('stopped', 'started'):
                calls = []
                def command(argv, *args, **kwargs):
                    calls.append(argv)
                    if argv[:2] == ['utmctl', 'status']: return state
                    return 'started'
                with patch.object(driver, 'command', side_effect=command), \
                     patch.object(driver, 'rdpipe', return_value='{}'), patch.object(driver, 'pause'):
                    with self.assertRaisesRegex(RuntimeError, 'guest unusable'):
                        driver.preflight()
                self.assertEqual(any(c[:2] == ['utmctl', 'start'] for c in calls), state == 'stopped')
                self.assertFalse(any(c[:2] == ['utmctl', 'stop'] for c in calls))
                self.assertFalse(driver.leased)

    def test_launch_receipt_recovers_ownership_for_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            driver.journal['owned_processes'] = [dict(status='launching', role='game-1', receipt='receipt.json')]
            recovered = dict(pid=123, path='game.exe', start='99', role='game-1')
            with patch.object(driver, 'ps', return_value=json.dumps(recovered)), patch.object(driver, 'stop') as stop:
                self.assertEqual(driver.cleanup(), [])
                stop.assert_called_once_with(123)
            self.assertEqual(driver.active, [recovered])

    def test_input_changes_are_rejected_before_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            original = Path(tmp) / 'scenario.yaml'
            original.write_bytes(b'original')
            frozen = driver.pin(original, Path('scenarios/case.yaml'))
            driver.bundle_sources = {'scenarios/case.yaml': sha256(frozen)}
            original.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'input changed'): driver.assert_inputs()
            original.write_bytes(b'original')
            frozen.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'bundle source changed'): driver.assert_inputs()
            self.assertFalse((driver.root / 'report.json').exists())

    def test_cleanup_failure_cannot_leave_a_passing_report(self):
        from capture_oracle import main
        with tempfile.TemporaryDirectory() as tmp:
            driver = self.controller(tmp)
            (driver.root / 'report.json').write_text(json.dumps(dict(status='PASS')))
            argv = ['capture', '--scenario', 'scenarios/MOV-0002.yaml', '--map-revision', 'MOV-0002-test',
                    '--out', str(driver.root), '--vm', driver.args.vm, '--pjass', 'pjass', '--common', 'common', '--blizzard', 'Blizzard']
            with patch('sys.argv', argv), patch('capture_oracle.Controller', return_value=driver), \
                 patch.object(driver, 'run', return_value='PASS'), patch.object(driver, 'cleanup', return_value=['guest unavailable']):
                self.assertEqual(main(), 2)
            self.assertEqual(load(driver.root / 'report.json')['status'], 'FAILED')
            self.assertEqual(driver.journal['status'], 'FAILED')

    def test_retained_unattended_bundles_regrade_without_a_guest(self):
        # Required retail evidence, never skipped when a fixture disappears. The
        # current CI-built C++ runner/codegen operate on the frozen scenario bytes.
        import os
        from regrade_capture import BUNDLES, REVISIONS, regrade
        runner = Path(os.environ.get('WC3TEST_RUNNER', ROOT / 'build' / ('wc3test.exe' if os.name == 'nt' else 'wc3test')))
        codegen = Path(os.environ.get('ORACLE_CODEGEN', ROOT / 'build' / ('oracle_codegen.exe' if os.name == 'nt' else 'oracle_codegen')))
        with tempfile.TemporaryDirectory() as tmp:
            for label in REVISIONS:
                with self.subTest(label=label):
                    self.assertEqual(regrade(BUNDLES / label, runner, codegen, Path(tmp) / label)['status'], 'PASS')


if __name__ == '__main__': unittest.main()

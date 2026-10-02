"""Generator control audit, literal identity, ordering and unsupported input gates."""
import os
from pathlib import Path
import tempfile
import shutil
import unittest

from audit_oracle import audit, statements
from generate_oracle import GOLDENS, generate
from trace_contract import ROOT, load, write_json

CODEGEN = Path(os.environ.get('ORACLE_CODEGEN', ROOT / 'build' /
               ('oracle_codegen.exe' if os.name == 'nt' else 'oracle_codegen')))


class OracleGeneratorTests(unittest.TestCase):
    def test_downloaded_ci_generation_requires_complete_matching_bytes(self):
        from summarize_ci import verify_generation
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(GOLDENS, root / 'generated')
            write_json(root / 'reports/generator-audit.json', audit(root / 'generated'))
            result = dict(oracle_generation_required=True,
                          oracle_generation=dict(status='PASS', manifest=load(GOLDENS / 'manifest.json')))
            self.assertEqual(verify_generation(root, result), result['oracle_generation'])
            with self.assertRaisesRegex(ValueError, 'required oracle generation'):
                verify_generation(root, dict(oracle_generation_required=True))
            self.assertIsNone(verify_generation(root, {}))  # legacy Phase 5 evidence
            path = root / 'generated/MOV-0006.j'
            path.write_bytes(path.read_bytes().replace(b'+ 1000)', b'+ 999)'))
            with self.assertRaisesRegex(ValueError, 'digest differs'):
                verify_generation(root, result)
    def test_world_editor_clipboard_has_one_explicit_crlf_conversion(self):
        from we_author import clipboard_text
        library = (ROOT / 'oracle/jass/lib/oracle-v1.j').read_bytes()
        case = (GOLDENS / 'MOV-0006.j').read_bytes()
        text = clipboard_text(library, case)
        self.assertNotIn('\r\r\n', text)
        self.assertEqual(text.replace('\r\n', '\n').encode(), library + b'\n' + case)
        with self.assertRaisesRegex(ValueError, 'LF-only'):
            clipboard_text(library, case.replace(b'\n', b'\r\n'))
    def test_all_committed_goldens_and_independent_control(self):
        files, manifest = generate(CODEGEN, [Path('scenarios')])
        self.assertEqual(len(files), 10)
        self.assertEqual(manifest, load(GOLDENS / 'manifest.json'))
        for name, text in files.items():
            self.assertEqual(text, (GOLDENS / name).read_bytes(), name)
        self.assertEqual(audit(GOLDENS)['status'], 'PASS')
        self.assertIn(b'707.106781, 707.106781)', files['MOV-0003.j'])
        self.assertIn(b'GetUnitX(unit0), GetUnitY(unit0) + 1000)', files['MOV-0006.j'])
        self.assertIn(b'GetUnitX(unit0) - 1000, GetUnitY(unit0))', files['MOV-0007.j'])

    def test_audit_catches_changed_calls_literals_schedule_and_order(self):
        original = GOLDENS / 'MOV-0006.j'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'changed.j'
            expected = statements(original)[0]
            for old, new in (
                ('0.02, 250', '0.02, 251'), ('== 50', '== 51'),
                ('GetUnitY(unit0) + 1000', 'GetUnitY(unit0) + 999'),
                ('GetUnitX(unit0),', 'GetUnitX(unit0) + 0,'),
                ('call SetUnitAcquireRange(unit0, 0)', 'call SetUnitAcquireRange(unit0, 1)'),
                ('call SetCameraPosition(384, 192)', 'call SetCameraPosition(192, 384)'),
            ):
                path.write_text(original.read_text().replace(old, new), newline='\n')
                self.assertNotEqual(expected, statements(path)[0], old)
            path.write_text(original.read_text().replace('    call SetCameraPosition(384, 192)\n', '')
                            .replace('    call OracleRun(', '    call SetCameraPosition(384, 192)\n    call OracleRun('), newline='\n')
            self.assertNotEqual(expected, statements(path)[0])
            path.write_text(original.read_text().replace('== 50', '>= 50'), newline='\n')
            with self.assertRaisesRegex(ValueError, 'unknown statement'):
                statements(path)

    def test_revision_binds_same_bytes_and_equal_time_actions_keep_file_order(self):
        base = (ROOT / 'scenarios/MOV-0006.yaml').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ordered.yaml'
            path.write_text(base.replace('...', '  - at: 1.0\n    unit: u0\n    order: stop\n...'), newline='\n')
            files, info = generate(CODEGEN, [path], 'MOV-0006-g1')
            text = files['MOV-0006-g1.j'].decode()
            self.assertEqual(text.count('OracleCallback() == 50'), 1)
            self.assertLess(text.index('GetUnitY(unit0) + 1000'), text.index('OracleOrderImmediate'))
            self.assertIn(info['inputs'][0]['scenario']['sha256'], text)
            self.assertIn('"MOV-0006", "MOV-0006-g1", 1000', text)
            self.assertIn('"MOV-0006", "MOV-0006", 1000', generate(CODEGEN, [path])[0]['MOV-0006.j'].decode())

    def test_unsupported_input_is_rejected_not_approximated(self):
        base = (ROOT / 'scenarios/MOV-0006.yaml').read_text()
        cases = (
            (base.replace('version: 1', 'version: 2'), 'unsupported scenario version'),
            (base.replace('period: 0.02', 'period: 0.001').replace('at: 1.0', 'at: 0.05'), '0.02 s sampler'),
            (base.replace('position: [0, 0]', 'position: [0.001953125, 0]'), 'fractional CreateUnit'),
            (base.replace('position: [0, 0]', 'position: [3329, 0]'), 'outside template'),
            (base.replace('target: [1000, 0]', 'target: [0, 3072.000001]'), 'outside template'),
            (base.replace('offset: [0, 1000]', 'offset: [0, 7000]'), 'playable span'),
            (base.replace('    facing: 0', '    facing: 0\n    move_speed: 100\n  - name: u1\n    type: hfoo\n    position: [0, 384]\n    facing: 0'), 'multi-unit property'),
            (base.replace('\n', '\r\n'), 'carriage return'),
            (base.replace('...\n', ''), 'missing document end'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.yaml'
            for text, error in cases:
                path.write_bytes(text.encode())
                with self.assertRaisesRegex(ValueError, error):
                    generate(CODEGEN, [path])
            path.write_text(base, newline='\n')
            with self.assertRaisesRegex(ValueError, 'revision must belong'):
                generate(CODEGEN, [path], 'MOV-0007-g1')
            with self.assertRaisesRegex(ValueError, 'invalid map revision'):
                generate(CODEGEN, [path], 'MOV-0006-G1')


if __name__ == '__main__':
    unittest.main()

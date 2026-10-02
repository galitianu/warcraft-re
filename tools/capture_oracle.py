#!/usr/bin/env python3
"""Capture supported v1 controls unattended through the selected UTM/rdpipe VM.

All output is a new evidence bundle. No canonical references are promoted and no
failed bundle is resumed: use a new map revision and output directory to retry.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

import capture_runs
from compare_traces import compare
from generate_oracle import generate
from normalize_generated import normalize
from trace_contract import BUILD, ROOT, load, sha256, write_json
import we_author

SUPPORTED = ('MOV-0002', 'MOV-0004', 'MOV-0006', 'MOV-0010')
ENVIRONMENT = Path(f'oracle/environment/{BUILD}.json')


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_installation(observed, expected, machine):
    require((observed['reference_build'], observed['target'], observed['machine'], observed['os_architecture'], observed['os']) ==
            (BUILD, 'vm', machine, 'ARM64', 'Microsoft Windows 11 Pro'), 'wrong selected machine, guest OS/architecture or build')
    files = {f['name']: f for f in observed['files']}
    require(len(files) == len(observed['files']) == len(expected['files']) == 7, 'need seven distinct reference files')
    for reference in expected['files']:
        actual = files.get(reference['name'], {})
        require(all(actual.get(k) == reference[k] for k in ('sha256', 'bytes')), f'installation hash/size differs: {reference["name"]}')
        if 'version' in reference:
            require(actual.get('version') == reference['version'] and actual.get('pe_machine') == 332,
                    f'wrong version or x86 PE identity: {reference["name"]}')


class Controller:
    def __init__(self, args):
        self.args = args
        self.root = args.out.resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / 'diagnostics').mkdir()
        self.started = time.monotonic()
        self.end = self.started + args.total_deadline
        self.env = dict(os.environ, RDPIPE_TARGET='vm', RDPIPE_HOLDER=f'oracle-{uuid.uuid4().hex}')
        self.leased = False
        self.renewed = 0
        self.counter = 0
        self.active = []
        self.journal = dict(status='RUNNING', stage='inputs', completed_stages=[], owned_processes=[], transfers=[],
                            events=[], stage_times=[], intervention_count=0, vm=args.vm, target='vm', map_revision=args.map_revision)
        self.pinned = {}
        self.flush()

    def flush(self):
        self.journal['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
        write_json(self.root / 'diagnostics/journal.json', self.journal)

    def note(self, event, detail):
        self.journal['events'].append(dict(event=event, detail=detail))
        self.flush()

    def stage(self, name):
        previous = self.journal['stage']
        if previous != name:
            self.journal['completed_stages'].append(previous)
        self.journal.setdefault('stage_times', []).append(dict(stage=name, elapsed_seconds=round(time.monotonic()-self.started, 3)))
        self.journal['stage'] = name
        self.flush()
        print(f'{self.args.map_revision}: {name}', flush=True)

    def command(self, argv, stdin=None, timeout=60, cleanup=False, cwd=None):
        remaining = self.end - time.monotonic()
        if not cleanup:
            require(remaining > 0, f'total deadline exceeded at {self.journal["stage"]}')
            timeout = min(timeout, remaining)
        self.counter += 1
        log = self.root / 'diagnostics' / f'{self.counter:04}-command.json'
        entry = dict(argv=[str(a) for a in argv], stdin=stdin, timeout_seconds=timeout)
        write_json(log, entry)
        try:
            result = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout, env=self.env, cwd=ROOT if cwd is None else cwd)
            entry.update(exit=result.returncode, stdout=result.stdout, stderr=result.stderr)
            write_json(log, entry)
            require(result.returncode == 0, f'{argv[:3]}: exit {result.returncode}: {result.stderr.strip() or result.stdout.strip()}')
            return result.stdout.strip()
        except subprocess.TimeoutExpired as error:
            entry.update(error='timeout', stdout=str(error.stdout or ''), stderr=str(error.stderr or ''))
            write_json(log, entry)
            raise RuntimeError(f'{self.journal["stage"]}: command timed out after {timeout:.2f}s: {argv[:3]}') from error

    def renew(self):
        if self.leased and time.monotonic() - self.renewed > 60:
            self.command(['rdpipe', '--target', 'vm', 'lease', 'acquire', '--ttl', '300'], timeout=15)
            self.renewed = time.monotonic()

    def rdpipe(self, *args, stdin=None, timeout=60, cleanup=False):
        if not cleanup:
            self.renew()
        return self.command(['rdpipe', '--target', 'vm', *args], stdin, timeout, cleanup)

    def ps(self, script, timeout=30, cleanup=False):
        return self.rdpipe('ps', '-', stdin='$ErrorActionPreference="Stop"; ' + script + '; exit 0', timeout=timeout, cleanup=cleanup)

    def ui(self, tool, **arguments):
        self.renew()
        raw = self.command(['rdpipe', '--target', 'vm', '--json', 'ui', '--image-dir', str(self.root / 'diagnostics'), tool, '-'], json.dumps(arguments), timeout=20)
        self.renew()
        result = json.loads(raw)
        require(not result.get('isError'), f'UI {tool} failed: {raw}')
        return result

    def pause(self, seconds):
        self.renew()
        require(time.monotonic() + seconds <= self.end, 'total deadline exceeded')
        time.sleep(seconds)

    def assert_hash(self, remote, expected):
        actual = self.ps(f'(Get-FileHash -Algorithm SHA256 -LiteralPath "{remote}").Hash').lower()
        require(actual == expected, f'transferred file differs: {remote}; expected {expected}, observed {actual}')
        return actual

    def pull(self, remote, local):
        require(not local.exists(), f'refusing to overwrite {local}')
        before = self.ps(f'(Get-FileHash -Algorithm SHA256 -LiteralPath "{remote}").Hash').lower()
        self.rdpipe('pull', remote, str(local))
        after = self.assert_hash(remote, before)
        require(sha256(local) == before, 'retrieved bytes differ from remote hash')
        self.journal['transfers'].append(dict(direction='pull', remote=remote, local=local.relative_to(self.root).as_posix(),
                                               before_sha256=before, after_sha256=after, local_sha256=sha256(local)))
        self.flush()

    def push(self, local, directory):
        remote = directory + '\\' + local.name
        require(self.ps(f'Test-Path -LiteralPath "{remote}"') == 'False', f'remote artifact exists: {remote}')
        self.rdpipe('push', str(local), '--to', directory)
        self.assert_hash(remote, sha256(local))
        self.journal['transfers'].append(dict(direction='push', remote=remote, sha256=sha256(local)))
        self.flush()
        return remote

    def launch(self, directory, executable, map_path, role):
        # Persist identity in the guest before returning: a lost response still
        # leaves a receipt from which cleanup can recover the owned PID/start.
        receipt = self.remote_work + '\\' + role + '.json'
        script = (f'$p=Start-Process -FilePath "{directory}\\{executable}" -WorkingDirectory "{directory}" '
                  f'-ArgumentList @("-loadfile", "`"{map_path}`"") -PassThru; '
                  '$p.Refresh(); $r=@{pid=$p.Id; start=$p.StartTime.ToUniversalTime().Ticks.ToString(); '
                  f'path="{directory}\\{executable}"; role="{role}"}}; '
                  f'$r | ConvertTo-Json | Set-Content -LiteralPath "{receipt}"; $r | ConvertTo-Json')
        self.journal['owned_processes'].append(dict(role=role, receipt=receipt, status='launching'))
        self.flush()
        info = json.loads(self.ps(script))
        self.active.append(info)
        self.journal['owned_processes'][-1].update(info, status='running')
        self.flush()
        return info['pid']

    def stop(self, pid):
        info = next(p for p in self.active if p['pid'] == pid)
        self.ps(f'$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; if ($p) {{ '
                f'if ($p.Path -ne "{info["path"]}" -or $p.StartTime.ToUniversalTime().Ticks.ToString() -ne "{info["start"]}") '
                '{ throw "PID reused; refusing to stop unowned process" }; '
                '$p | Stop-Process; $p | Wait-Process -Timeout 10 }', timeout=15, cleanup=True)
        self.active.remove(info)
        for p in self.journal['owned_processes']:
            if p.get('pid') == pid: p['status'] = 'stopped'
        self.flush()

    def preflight(self):
        self.stage('guest-preflight')
        require(re.fullmatch(r'[A-Fa-f0-9-]{36}', self.args.vm), '--vm must be the exact selected UTM UUID')
        state = self.command(['utmctl', 'status', self.args.vm], timeout=15)
        self.note('utm-state', state)
        if state.strip().lower() in ('stopped', 'suspended'):
            self.command(['utmctl', 'start', self.args.vm], timeout=30)
        else:
            require(state.strip().lower() == 'started', f'unsupported UTM state {state!r}; no automatic reset')
        deadline = time.monotonic() + self.args.guest_deadline
        last = 'no relay response'
        while time.monotonic() < deadline:
            try:
                status = json.loads(self.rdpipe('--json', 'status', timeout=min(10, max(.1, deadline-time.monotonic()))))
                targets = status['daemon']['targets']
                target = next(t for t in targets if t['name'] == 'vm')
                relay = target['relay']['info']
                require(relay['arch'] == 'aarch64' and relay['exec'] and not relay['elevated'], 'need non-elevated ARM64 relay with exec')
                session = relay['session']
                require(session['state'] == 'active' and not session['locked'] and not session['secure_desktop'], 'guest desktop locked/inactive/secure')
                require(session['screen'] == [1920, 1080] and session['dpi'] == 96, 'requires 1920x1080 desktop at 96 dpi')
                ips = self.command(['utmctl', 'ip-address', self.args.vm], timeout=min(10, max(.1, deadline-time.monotonic())))
                require(target['host'] in ips.splitlines(), 'selected UTM guest IP differs from rdpipe vm target')
                require(self.ps('$env:COMPUTERNAME', timeout=min(10, max(.1, deadline-time.monotonic()))) == self.args.machine,
                        'rdpipe reached a different guest machine')
                self.ui('list_windows')
                write_json(self.root / 'diagnostics/preflight.json', dict(utm_state=state, guest_ips=ips.splitlines(), target=target))
                return
            except (ValueError, RuntimeError, KeyError, TypeError, StopIteration) as error:
                last = str(error)
                if time.monotonic() < deadline:
                    try: self.rdpipe('connect', timeout=min(10, max(.1, deadline-time.monotonic())))
                    except (ValueError, RuntimeError): pass
                    self.pause(min(2, max(0, deadline-time.monotonic())))
        raise RuntimeError(f'guest unusable within {self.args.guest_deadline}s: {last}; VM not reset')

    def installation(self, name):
        script = (ROOT / 'tools/verify_oracle.ps1').read_text()
        observed = json.loads(self.rdpipe('ps', '-', stdin=script, timeout=60))
        write_json(self.root / 'oracle/environment' / name, observed)
        verify_installation(observed, load(ROOT / ENVIRONMENT), self.args.machine)
        return Path('oracle/environment') / name

    def pin(self, source, destination=None):
        source = Path(source)
        relative = destination or source.relative_to(ROOT)
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), f'output exists: {target}')
        shutil.copyfile(source, target)
        self.pinned[str(source)] = sha256(source)
        return target

    def assert_inputs(self):
        for path, digest in self.pinned.items():
            require(sha256(path) == digest, f'input changed during capture: {path}')
        for relative, digest in self.bundle_sources.items():
            require(sha256(self.root / relative) == digest, f'bundle source changed during capture: {relative}')

    def run(self):
        args = self.args
        scenario = args.scenario.resolve()
        # Exact supported descriptions only; a changed/new scenario first needs an
        # independently reviewed control and shape, never one derived from C++.
        exp = scenario.stem
        reviewed = load(ROOT / 'oracle/generated/v1/manifest.json')['inputs']
        accepted = {i['experiment']: i['scenario']['sha256'] for i in reviewed}
        require(exp in SUPPORTED and sha256(scenario) == accepted[exp] and scenario.read_bytes() == (ROOT / f'scenarios/{exp}.yaml').read_bytes(),
                'unsupported scenario: require exact bytes of a supported v1 control')
        require(re.fullmatch(re.escape(exp) + r'-[a-z0-9]+(?:-[a-z0-9]+)*', args.map_revision), 'invalid new map revision')
        label = args.map_revision
        for path in (ROOT / f'oracle-maps/{label}.w3m', ROOT / f'oracle/generated/maps/{label}.j',
                     ROOT / f'oracle/captures/{BUILD}/{label}', ROOT / f'oracle/canonical-generated/{BUILD}/{label}.json'):
            require(not path.exists(), f'retained revision exists: {path}')
        require(args.runs >= 3 and args.runs <= 20, '--runs must be 3..20 for validated repeatability')
        from check_map import check  # optional local packaging dependency, fail before Windows mutation
        scenario = self.pin(scenario, Path(f'scenarios/{exp}.yaml'))
        library = self.pin(ROOT / 'oracle/jass/lib/oracle-v1.j')
        self.pin(ROOT / ENVIRONMENT)
        template = self.pin(ROOT / 'oracle-maps/MOV-0002.w3m')
        menu = self.pin(ROOT / 'tools/editor-menu.ps1')
        for path in sorted(p for p in (ROOT / 'tools').glob('*.py') if not p.name.startswith('test_')) + [ROOT / 'tools/verify_oracle.ps1']:
            self.pinned[str(path)] = sha256(path)
        for path in (args.codegen.resolve(), args.runner.resolve(), args.pjass.resolve(), args.common.resolve(), args.blizzard.resolve()):
            require(path.is_file(), f'missing prerequisite: {path}')
            self.pinned[str(path)] = sha256(path)
        cases, generation = generate(args.codegen, [scenario], label)
        generation['inputs'][0]['scenario']['path'] = f'scenarios/{exp}.yaml'
        require(generation['inputs'][0]['scenario']['version'] == 1, 'v2 unsupported by unattended capture')
        case = self.root / f'oracle/generated/maps/{label}.j'
        case.parent.mkdir(parents=True)
        case.write_bytes(cases[label + '.j'])
        generation_path = Path(f'oracle/generated/maps/{label}-generation.json')
        write_json(self.root / generation_path, generation)
        source = self.root / 'diagnostics/syntax.j'
        source.write_bytes(b'globals\n hashtable udg_OracleState = null\n trigger gg_trg_Melee_Initialization = null\nendglobals\n' + library.read_bytes() + b'\n' + case.read_bytes())
        self.command([str(args.pjass.resolve()), str(args.common.resolve()), str(args.blizzard.resolve()), str(source)])
        self.bundle_sources = {p.relative_to(self.root).as_posix(): sha256(p) for p in (scenario, library, template, menu, case, self.root / generation_path, self.root / ENVIRONMENT)}
        write_json(self.root / 'diagnostics/syntax-identities.json', {str(p): sha256(p) for p in
                   (args.pjass, args.common, args.blizzard, source)})
        self.stage('generated-and-syntax-checked')
        self.preflight()
        self.rdpipe('lease', 'acquire', '--ttl', '300', timeout=15)
        self.leased, self.renewed = True, time.monotonic()
        self.stage('installation-verification')
        verification = self.installation('capture-verification.json')
        # Refuse to share editor/game state, even though exec is not lease-gated.
        require(not self.ps('Get-Process -Name "Warcraft III","World Editor" -ErrorAction SilentlyContinue | Select-Object Id | ConvertTo-Json'),
                'existing WC3/editor process; close it before capture')
        self.remote_work = 'C:\\Users\\rdpipe\\oracle-' + self.env['RDPIPE_HOLDER']
        self.ps(f'New-Item -ItemType Directory -Path "{self.remote_work}" -ErrorAction Stop | Out-Null; '
                f'New-Item -ItemType Directory -Force -Path "{we_author.MAPS}" | Out-Null')
        remote_template = self.push(template, self.remote_work)
        remote_menu = self.push(menu, self.remote_work)
        self.stage('editor-authoring')
        saved_map = self.root / f'oracle-maps/{label}.w3m'
        we_author.author(self, label, library, case, saved_map, remote_template, remote_menu)
        self.stage('saved-map-validation')
        checked = check(saved_map, library, case)
        write_json(self.root / 'diagnostics/check-map.json', checked)
        require(checked['ok'], 'saved map differs from intended library/case/header/format')
        base = self.root / f'oracle/captures/{BUILD}/{label}'
        base.mkdir(parents=True)
        entries = capture_runs.capture(self, label, saved_map, base, args.runs, args.run_deadline)
        self.stage('final-integrity')
        self.assert_inputs()
        self.assert_hash(f'{we_author.MAPS}\\{label}.w3m', sha256(saved_map))
        self.installation('capture-verification-final.json')
        from record_generated import candidate_manifest
        candidate_manifest(self.root, exp, label, generation_path, verification, checked, entries)
        self.stage('normalization')
        candidate = self.root / 'candidate'
        reproduction = normalize(label, candidate, self.root)
        write_json(self.root / 'reproduction.json', reproduction)
        self.stage('same-scenario-comparison')
        actual = self.root / 'cpp'
        # Relative path in both producer identities; bytes frozen in this bundle.
        stdout = self.command([str(args.runner.resolve()), '--scenario', f'scenarios/{exp}.yaml', '--model', 'v4',
                               '--seed', '1', '--out', str(actual)], cwd=self.root, timeout=60)
        write_json(self.root / 'diagnostics/cpp.json', dict(exit=0, stdout=stdout, runner_sha256=sha256(args.runner)))
        self.assert_inputs()
        comparison = compare(load(candidate / f'{label}.json'), load(actual / f'{exp}.json'), self.root)
        write_json(self.root / 'comparison.json', comparison)
        status = 'PASS' if reproduction['status'] == comparison['status'] == 'PASS' else 'FINDING'
        write_json(self.root / 'report.json', dict(status=status, capture='VALIDATED', candidate=f'candidate/{label}.json',
                   canonical_promotion=False, reproduction=reproduction, comparison=comparison,
                   intervention_count=0, elapsed_seconds=round(time.monotonic()-self.started, 3),
                   tool_sha256=self.pinned, limits='selected VM/map/build; other machines/seeds and retail RNG UNKNOWN'))
        return status

    def cleanup(self):
        errors = []
        for process in self.journal['owned_processes']:
            if process['status'] == 'launching':
                try:
                    info = json.loads(self.ps(f'Get-Content -Raw -LiteralPath "{process["receipt"]}"', timeout=10, cleanup=True))
                    self.active.append(info)
                    process.update(info, status='running')
                except Exception as error:
                    errors.append(str(error))
                    self.note('ownership-recovery-failed', str(error))
        for info in self.active[:]:
            try: self.stop(info['pid'])
            except Exception as error:
                errors.append(str(error))
                self.note('owned-process-cleanup-failed', str(error))
        if self.leased:
            try: self.rdpipe('lease', 'release', timeout=10, cleanup=True)
            except Exception as error:
                errors.append(str(error))
                self.note('lease-release-failed', str(error))
            self.leased = False
        return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--map-revision', required=True)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--vm', required=True, help='exact selected UTM UUID (utmctl list); no VM configuration is stored')
    parser.add_argument('--machine', default=load(ROOT / 'oracle/environment/phase-6-verification.json')['machine'])
    parser.add_argument('--codegen', type=Path, default=ROOT / 'build/oracle_codegen')
    parser.add_argument('--runner', type=Path, default=ROOT / 'build/wc3test')
    parser.add_argument('--pjass', type=Path, required=True)
    parser.add_argument('--common', type=Path, required=True)
    parser.add_argument('--blizzard', type=Path, required=True)
    parser.add_argument('--guest-deadline', type=float, default=90)
    parser.add_argument('--run-deadline', type=float, default=120)
    parser.add_argument('--total-deadline', type=float, default=900)
    args = parser.parse_args()
    for name in ('guest_deadline', 'run_deadline', 'total_deadline'):
        require(.1 <= getattr(args, name) <= 3600, f'invalid {name}')
    controller = None
    exit_code = 2
    try:
        controller = Controller(args)
        status = controller.run()
        controller.journal['status'] = status
        controller.stage('complete')
        exit_code = int(status != 'PASS')
    except (Exception, KeyboardInterrupt) as error:
        if controller:
            controller.journal.update(status='FAILED', error=str(error))
            controller.flush()
            if controller.leased:
                try: controller.ui('get_desktop_state')
                except Exception as diagnostic_error: controller.note('UI-diagnostic-failed', str(diagnostic_error))
        print(f'capture_oracle: {error}', flush=True)
        exit_code = 2
    finally:
        if controller:
            cleanup_errors = controller.cleanup()
            if cleanup_errors:
                controller.journal.update(status='FAILED', cleanup_errors=cleanup_errors)
                report_path = controller.root / 'report.json'
                if report_path.exists():
                    report = load(report_path)
                    report.update(status='FAILED', cleanup_errors=cleanup_errors)
                    write_json(report_path, report)
                exit_code = 2
            controller.flush()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

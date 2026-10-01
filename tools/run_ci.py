#!/usr/bin/env python3
"""Build and assess primitive compatibility without a Warcraft III installation."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from compare_traces import markdown as comparison_markdown
from normalize_traces import normalize_all
from regression import assess, markdown as regression_markdown
from trace_contract import BUILD, LABELS, ROOT, digest, load, payload, sha256, validate, write_json

# Archival migration remains a separate command, with permanent Phase 2 byte gates.
BASELINES = {'v1': 'results/phase-3/v1/comparison.json',
             'v2': 'results/phase-3/v2/comparison.json',
             'v2-before': 'results/phase-3/v2-before/comparison.json',
             'v3': 'results/footman-v3/v3/comparison.json',
             'v4': 'results/footman-v4/comparison.json'}


def baseline_for(model, system, arch):
    # Only measured profiles are promoted. Unknown scopes still face the original
    # native baseline, and differences fail for investigation rather than vanish.
    if system in ('Linux', 'Windows') and arch == 'x86_64' and model in ('v1', 'v2', 'v2-before'):
        return f'results/phase-4/baselines/x64-libm/{model}/comparison.json'
    return BASELINES[model]


def architecture(value):
    return {'aarch64': 'arm64', 'ARM64': 'arm64', 'AMD64': 'x86_64'}.get(value, value)


def execute(command, logs, name, *, accepted=(0,), env=None, timeout=180):
    """Every nonzero is explicit; compatibility exit 1 is assessed by the caller."""
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f'{name}.log'
    info = dict(command=[str(v) for v in command], timeout_seconds=timeout)
    started = time.monotonic()
    print(f'{name}: running', flush=True)
    try:
        with log.open('w', encoding='utf-8') as output:
            process_env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
            if env is not None:
                process_env.update(env)
            result = subprocess.run(info['command'], cwd=ROOT, env=process_env,
                                    stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        info['exit_code'] = result.returncode
        if result.returncode not in accepted:
            raise ValueError(f'{name}: exit {result.returncode}; see {log}')
        return result.returncode
    except subprocess.TimeoutExpired:
        info['error'] = 'timeout'
        raise ValueError(f'{name}: timed out after {timeout}s; see {log}') from None
    except OSError as error:
        info['error'] = str(error)
        raise
    finally:
        info['elapsed_seconds'] = time.monotonic() - started
        write_json(log.with_suffix('.json'), info)


def repeatability(first, second):
    expected = {'identity.json'} | {f'MOV-{n:04d}{s}' for n in range(1, 11)
                                  for s in ('.json', '.csv', '-actions.csv')}
    if {p.name for p in first.iterdir()} != expected or {p.name for p in second.iterdir()} != expected:
        raise ValueError('missing/unexpected runner artifacts (31 required per process)')
    full, observation = {}, {}
    for name in sorted(expected):
        hashes = [sha256(root / name) for root in (first, second)]
        full[name] = hashes
        if hashes[0] != hashes[1]:
            raise ValueError(f'separate-process file mismatch: {name}')
        if name.startswith('MOV-') and name.endswith('.json'):
            traces = [validate(load(root / name)) for root in (first, second)]
            observation[name] = [digest(payload(t)) for t in traces]
            if observation[name][0] != observation[name][1]:
                raise ValueError(f'separate-process observation mismatch: {name}')
    return dict(classification='RNG-DETERMINISTIC-WITH-SEED', runs=2, seed=1,
                scope='same binary/model/phase in two fresh processes; movement does not draw RNG',
                retail_rng_equivalence='UNKNOWN', observation_payload_sha256=observation,
                full_file_sha256=full)


def differences(a, b, path=''):
    """Dotted paths whose values differ, including keys present on one side only."""
    if isinstance(a, dict) and isinstance(b, dict):
        found = []
        for key in sorted(set(a) | set(b)):
            child = f'{path}.{key}' if path else key
            found += [child] if key not in a or key not in b else differences(a[key], b[key], child)
        return found
    return [] if a == b else [path]


def migration(control, declared, control_suite, declared_suite):
    """Phase 5 gate: scenario traces equal the hard-coded control in every
    observation/action payload and CSV byte; metadata differences are named."""
    cases = []
    for n in range(1, 11):
        case = f'MOV-{n:04d}'
        coded, scenario = (validate(load(root / f'{case}.json')) for root in (control, declared))
        payloads = [digest(payload(t)) for t in (coded, scenario)]
        if payloads[0] != payloads[1]:
            raise ValueError(f'{case}: scenario observation payload differs from the hard-coded control')
        for suffix in ('.csv', '-actions.csv'):
            if (control / f'{case}{suffix}').read_bytes() != (declared / f'{case}{suffix}').read_bytes():
                raise ValueError(f'{case}{suffix}: scenario CSV differs from the hard-coded control')
        metadata = differences(coded, scenario)
        if metadata != ['identity.build.scenarios', 'provenance.scenario']:
            raise ValueError(f'{case}: unexpected metadata differences {metadata}')
        used = scenario['provenance']['scenario']
        if sha256(ROOT / used['path']) != used['sha256']:
            raise ValueError(f'{case}: scenario hash differs from the committed {used["path"]}')
        cases.append(dict(case=case, scenario=used, observation_payload_sha256=payloads[0],
                          csv_bytes_identical=True, metadata_differences=metadata,
                          full_trace_sha256=dict(hard_coded=sha256(control / f'{case}.json'),
                                                 scenario=sha256(declared / f'{case}.json'))))
    identities = [load(root / 'identity.json') for root in (control, declared)]
    if differences(*identities) != ['scenarios']:
        raise ValueError('run identity differs beyond the scenario list')
    def graded(suite):
        return dict(suite, identity=None, cases=[{k: v for k, v in c.items() if k != 'actual_sha256'}
                                                 for c in suite['cases']])
    if graded(control_suite) != graded(declared_suite):
        raise ValueError('scenario comparison report differs from the hard-coded control')
    return dict(status='EQUIVALENT', cases=cases, identity_differences=['scenarios'],
                comparison_differences=['identity.build.scenarios', 'cases[].actual_sha256'],
                scope='same binary/model/phase/seed; scenarios/*.yaml against the hard-coded MOV-0001..0010 control')


def summarize(result, reports):
    lines = ['# Primitive compatibility CI', '',
             f"CI gate: **{result['status']}**. Retail reference: `{BUILD}` (x86 32-bit).", '',
             f"Host: {result['host']['system']} {result['host']['release']}, "
             f"{result['host']['architecture']}; Python {result['host']['python']}.", '',
             'Primary: footman-v4, after-due-update, seed 1. Missing canonical JASS/CLOCKS: **UNOBSERVED**.',
             'The separate state-capture probe has named sampling-order exceptions; it is not a JASS producer.', '',
             'Scenario runs use the committed scenarios/*.yaml; migration compares them with the hard-coded control.', '',
             '| Model / phase | Compatibility | Regression gate | Improvements | Scenario compatibility | Scenario migration |',
             '|---|---|---|---|---|---|']
    for name, info in result['models'].items():
        scenario = info.get('scenario') or {}
        lines.append(f"| {name} | {info['compatibility_passes']}/10 PASS | {info['regression_verdict']} | {info['improvements']} | "
                     f"{scenario.get('compatibility_passes', '—')}/10 PASS, regression {scenario.get('regression_verdict', 'MISSING')} | "
                     f"{scenario.get('migration', 'MISSING')} |")
    for name, error in result['errors'].items():
        lines += ['', f'**{name}:** {error}']
    for name in result['models']:
        suite = load(reports / name / 'comparison.json')
        lines += ['', f'## {name}', '',
                  f"Compiler: {suite['identity']['build']['compiler']}; "
                  f"{suite['identity']['build']['build_type']}; target {suite['identity']['build']['architecture']}; "
                  f"FP contraction {suite['identity']['build']['fp_contract']}.", '',
                  comparison_markdown(suite).split('\n', 2)[2],
                  regression_markdown(load(reports / name / 'regression.json'))]
    (reports / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run(args):
    build = args.build.resolve()
    reports, traces, logs = build / 'ci/reports', build / 'ci/traces', build / 'ci/logs'
    # Never compare stale output from an earlier successful invocation.
    if (build / 'ci').exists():
        shutil.rmtree(build / 'ci')
    reports.mkdir(parents=True)
    result = dict(status='FAIL', host=dict(system=platform.system(), release=platform.release(),
                  architecture=architecture(platform.machine()), python=platform.python_version()),
                  models={}, errors={}, original_wc3_required=False)
    metadata = dict(host=result['host'], requested_compiler=args.compiler, build_type=args.config,
                    expected_architecture=args.expect_arch, seed=1,
                    github={key: os.environ.get(key) for key in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
                            'GITHUB_SHA', 'GITHUB_EVENT_NAME', 'RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion')})
    write_json(reports / 'environment.json', metadata)
    try:
        if args.expect_arch and result['host']['architecture'] != args.expect_arch:
            raise ValueError(f"host architecture {result['host']['architecture']} != {args.expect_arch}")
        configure = ['cmake', '-S', ROOT, '-B', build, '-G', 'Ninja',
                     f'-DCMAKE_BUILD_TYPE={args.config}', f'-DCMAKE_CXX_COMPILER={args.compiler}',
                     f'-DPython3_EXECUTABLE={sys.executable}', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                     '-DBUILD_TESTING=ON']
        execute(configure, logs, 'configure')
        execute(['cmake', '--build', build, '--parallel', '4'], logs, 'build')
        for name in ('CMakeCache.txt', 'compile_commands.json'):
            if (build / name).exists():
                shutil.copyfile(build / name, reports / name)
        ext = '.exe' if os.name == 'nt' else ''
        runner = build / f'wc3test{ext}'
        execute([build / f'math_scope{ext}'], logs, 'math-scope', timeout=10)
        write_json(reports / 'math-scope.json', load(logs / 'math-scope.log'))
        test_env = dict(os.environ, WC3TEST_RUNNER=str(runner))
        if (build / 'footman-v4-test').exists():
            shutil.rmtree(build / 'footman-v4-test')
        # Keep executing evidence stages after a test failure so diagnostics survive.
        for name, command in (
            ('ctest', ['ctest', '--test-dir', build, '--output-on-failure', '--timeout', '180']),
            ('python-integrity', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py', '-v'])):
            try:
                execute(command, logs, name, env=test_env, timeout=300)
            except (OSError, ValueError) as error:
                result['errors'][name] = str(error)
        references = build / 'ci/references'
        summaries = normalize_all(references)
        validation = dict(runs_validated=sum(s['runs_validated'] for s in summaries),
                          fixtures=len(summaries), summaries=summaries, byte_differences=[])
        for name in [f'{label}.json' for label in LABELS] + ['index.json']:
            if (references / name).read_bytes() != (ROOT / 'oracle/canonical' / BUILD / name).read_bytes():
                validation['byte_differences'].append(name)
        write_json(reports / 'fixture-validation.json', validation)
        if validation['byte_differences']:
            raise ValueError(f"regenerated fixture differs: {validation['byte_differences']}")
        for name in BASELINES:
            report_dir = reports / name
            report_dir.mkdir(parents=True)
            dest, again = traces / name, traces / f'{name}-repeat'
            model, phase = ('v2', 'before') if name == 'v2-before' else (name, 'after')
            command = [runner, '--model', model, '--phase', phase, '--seed', '1']
            try:
                execute([*command, '--out', dest], logs, f'{name}-runner', timeout=60)
                execute([*command, '--out', again], logs, f'{name}-repeat', timeout=60)
                write_json(report_dir / 'repeatability.json', repeatability(dest, again))
                comparison = report_dir / 'comparison.json'
                code = execute([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', dest,
                                '--reference', references, '--json', comparison, '--markdown', report_dir / 'comparison.md'],
                               logs, f'{name}-compare', accepted=(0, 1))
                suite = load(comparison)
                if code != int(suite['status'] == 'FAIL'):
                    raise ValueError('comparator exit/report disagreement')
                identity = load(dest / 'identity.json')
                write_json(report_dir / 'build-identity.json', identity)
                if identity != suite['identity']['build']:
                    raise ValueError('trace/binary identity disagreement')
                if identity['model'] != f'footman-{model}' or identity['observation_phase'] != f'{phase}-due-update' or identity['seed'] != 1:
                    raise ValueError('wrong model/phase/seed identity')
                if identity['architecture'] != (args.expect_arch or result['host']['architecture']):
                    raise ValueError('compiled target architecture differs from verified host/scope')
                if identity['build_type'] != args.config or identity['fp_contract'] != 'off':
                    raise ValueError('wrong build type or floating-point configuration')
                selected_baseline = baseline_for(name, result['host']['system'], identity['architecture'])
                baseline = ROOT / selected_baseline
                assessment = assess(load(baseline), suite)
                assessment.update(baseline_path=selected_baseline, baseline_sha256=sha256(baseline), comparator_exit=code)
                write_json(report_dir / 'regression.json', assessment)
                (report_dir / 'regression.md').write_text(regression_markdown(assessment), encoding='utf-8')
                result['models'][name] = dict(compatibility_passes=assessment['compatibility_passes'],
                       regression_verdict=assessment['regression_verdict'], improvements=len(assessment['improvements']))
                if assessment['regression_verdict'] != 'PASS':
                    result['errors'][name] = f"{len(assessment['regressions'])} protected metrics regressed; see {report_dir / 'regression.md'}"
                if name == 'v4' and (code != 0 or assessment['compatibility_passes'] != 10):
                    result['errors'][name] = 'primary compatibility requires all ten MOV passes'
            except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
                result['errors'][name] = str(error)
                continue
            # Phase 5: the same suite from the committed scenarios, graded identically
            # and checked against the hard-coded control above.
            try:
                scenario_dir = report_dir / 'scenario'
                declared, declared_again = traces / f'{name}-scenario', traces / f'{name}-scenario-repeat'
                from_scenarios = [*command, '--scenario', 'scenarios']
                execute([*from_scenarios, '--out', declared], logs, f'{name}-scenario-runner', timeout=60)
                execute([*from_scenarios, '--out', declared_again], logs, f'{name}-scenario-repeat', timeout=60)
                write_json(scenario_dir / 'repeatability.json', repeatability(declared, declared_again))
                comparison = scenario_dir / 'comparison.json'
                code = execute([sys.executable, ROOT / 'tools/compare_traces.py', '--actual', declared,
                                '--reference', references, '--json', comparison, '--markdown', scenario_dir / 'comparison.md'],
                               logs, f'{name}-scenario-compare', accepted=(0, 1))
                declared_suite = load(comparison)
                if code != int(declared_suite['status'] == 'FAIL'):
                    raise ValueError('scenario comparator exit/report disagreement')
                write_json(scenario_dir / 'migration.json', migration(dest, declared, suite, declared_suite))
                assessment = assess(load(baseline), declared_suite)
                assessment.update(baseline_path=selected_baseline, baseline_sha256=sha256(baseline), comparator_exit=code)
                write_json(scenario_dir / 'regression.json', assessment)
                (scenario_dir / 'regression.md').write_text(regression_markdown(assessment), encoding='utf-8')
                result['models'][name]['scenario'] = dict(
                    migration='EQUIVALENT', compatibility_passes=assessment['compatibility_passes'],
                    regression_verdict=assessment['regression_verdict'])
                if assessment['regression_verdict'] != 'PASS':
                    result['errors'][f'{name}-scenario'] = f"{len(assessment['regressions'])} protected metrics regressed"
                if name == 'v4' and (code != 0 or assessment['compatibility_passes'] != 10):
                    result['errors'][f'{name}-scenario'] = 'primary compatibility requires all ten MOV passes'
            except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
                result['errors'][f'{name}-scenario'] = str(error)
        # CTest's strict exact-text/state-capture check writes its full reports here.
        if (build / 'footman-v4-test/reports').exists():
            shutil.copytree(build / 'footman-v4-test/reports', reports / 'v4-state-probe', dirs_exist_ok=True)
        if args.archive:
            try:
                execute([sys.executable, ROOT / 'tools/run_phase3.py', '--runner', runner,
                         '--out', build / 'ci/archive/traces', '--reports', build / 'ci/archive/reports'],
                        logs, 'archival-migration', timeout=300)
            except (OSError, ValueError) as error:
                result['errors']['archival-migration'] = str(error)
        result['status'] = 'PASS' if not result['errors'] and len(result['models']) == 5 and all(
            'scenario' in info for info in result['models'].values()) else 'FAIL'
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        result['errors']['pipeline'] = str(error)
    finally:
        write_json(reports / 'result.json', result)
        summarize(result, reports)
        print(f"CI {result['status']}; reports: {reports}", flush=True)
    return int(result['status'] != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT / 'build-ci')
    parser.add_argument('--compiler', default='cl' if os.name == 'nt' else 'clang++')
    parser.add_argument('--config', choices=('Release', 'Debug'), default='Release')
    parser.add_argument('--expect-arch', choices=('arm64', 'x86_64'))
    parser.add_argument('--archive', action='store_true', help='also enforce historical Phase 2 migration bytes (native ARM AppleClang scope)')
    args = parser.parse_args()
    # CI cleanup must never be able to remove source or committed evidence.
    directory = args.build.resolve()
    if directory.parent != ROOT or not (directory.name == 'build' or directory.name.startswith('build-')):
        parser.error('--build must be build or build-* directly inside this checkout')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())

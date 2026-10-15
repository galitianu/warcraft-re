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
from audit_oracle import audit
from generate_oracle import generate, GOLDENS
from run_generated import run as run_generated
from run_mov0013 import EXPERIMENTS, run as run_experiment
from run_mov0018 import EXPERIMENTS as COLLISIONS, run as run_collision
from run_mov0023 import run as run_three_footmen
from normalize_traces import normalize_all
from regression import assess, markdown as regression_markdown
from trace_contract import BUILD, LABELS, ROOT, SCENARIOS, digest, load, payload, sha256, validate, write_json

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


def scenario_inputs(identity):
    """Every suite runs the ten committed scenarios; their recorded hashes must be
    those of the files in this checkout."""
    described = identity.get('scenarios')
    if [d['experiment'] for d in described or []] != [f'MOV-{n:04d}' for n in range(1, 11)]:
        raise ValueError('run identity does not list the ten committed MOV scenarios')
    for d in described:
        if d['path'] != f"scenarios/{d['experiment']}.yaml" or sha256(ROOT / d['path']) != d['sha256']:
            raise ValueError(f"{d['experiment']}: scenario identity differs from the committed file")
    return {d['experiment']: d['sha256'] for d in described}


def summarize(result, reports):
    lines = ['# Primitive compatibility CI', '',
             f"CI gate: **{result['status']}**. Retail reference: `{BUILD}` (x86 32-bit).", '',
             f"Host: {result['host']['system']} {result['host']['release']}, "
             f"{result['host']['architecture']}; Python {result['host']['python']}.", '',
             'Primary: footman-v4, after-due-update, seed 1. Missing canonical JASS/CLOCKS: **UNOBSERVED**.',
             'The separate state-capture probe has named sampling-order exceptions; it is not a JASS producer.', '',
             'Every suite runs the committed scenarios/MOV-0001..0010.yaml; their hashes are in each build identity.', '',
             f"Oracle generator: **{result.get('oracle_generation', {}).get('status', 'UNVERIFIED')}**. "
             f"Generated-map WC3 capture loop: **{result.get('generated_capture_loop', {}).get('status', 'UNVERIFIED')}**. "
             'Reviewed-difference gates: ' + ', '.join(
                 f"{e} **{result.get(gate_key(e), {}).get('status', 'UNVERIFIED')}**" for e in [*EXPERIMENTS, *COLLISIONS, 'MOV-0023']) + '.', '',
             '| Model / phase | Compatibility | Regression gate | Improvements |', '|---|---|---|---|']
    for name, info in result['models'].items():
        lines.append(f"| {name} | {info['compatibility_passes']}/10 PASS | {info['regression_verdict']} | {info['improvements']} |")
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


def check_generated_loop(runner, build, reports, result):
    # These captures are now a committed compatibility gate. Missing evidence
    # must fail the gate, never turn the requirement off.
    result['generated_capture_loop_required'] = True
    result['generated_capture_loop'] = dict(status='FAIL')
    try:
        code = run_generated(runner, build / 'ci/generated-loop', reports)
        result['generated_capture_loop'] = dict(status='PASS' if code == 0 else 'FAIL')
        if code:
            result['errors']['generated-capture-loop'] = 'generated map reproduction or comparison failed'
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['errors']['generated-capture-loop'] = str(error)


def gate_key(experiment):
    return experiment.lower().replace('-', '')  # MOV-0013 -> mov0013


def check_experiment(build, reports, result, experiment):
    # docs/mov-0013.md to docs/mov-0015.md: each gate requires exactly the reviewed differences.
    key, name = gate_key(experiment), experiment.lower()
    result[f'{key}_required'] = True
    result[key] = dict(status='FAIL')
    ext = '.exe' if os.name == 'nt' else ''
    try:
        code = run_experiment(build / f'wc3test{ext}', build / f'wc3states{ext}', build / f'oracle_codegen{ext}',
                              build / 'ci' / name, reports, experiment=experiment)
        result[key] = dict(status='PASS' if code == 0 else 'FAIL')
        if code:
            result['errors'][name] = f'{experiment} differences differ from the reviewed list'
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        result['errors'][name] = str(error)


def check_collision(build, reports, result, experiment):
    # docs/mov-0018.md to mov-0020.md: P3 acceptance and exactly the reviewed differences.
    key, name = gate_key(experiment), experiment.lower()
    result[f'{key}_required'] = True
    result[key] = dict(status='FAIL')
    ext = '.exe' if os.name == 'nt' else ''
    try:
        code = run_collision(build / f'wc3test{ext}', build / f'oracle_codegen{ext}', build / 'ci' / name, reports,
                             experiment=experiment)
        result[key] = dict(status='PASS' if code == 0 else 'FAIL')
        if code:
            result['errors'][name] = f'{experiment} acceptance or differences differ from the reviewed lists'
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        result['errors'][name] = str(error)


def run(args):
    build = args.build.resolve()
    reports, traces, logs = build / 'ci/reports', build / 'ci/traces', build / 'ci/logs'
    # Never compare stale output from an earlier successful invocation.
    if (build / 'ci').exists():
        shutil.rmtree(build / 'ci')
    reports.mkdir(parents=True)
    result = dict(status='FAIL', host=dict(system=platform.system(), release=platform.release(),
                  architecture=architecture(platform.machine()), python=platform.python_version()),
                  models={}, errors={}, original_wc3_required=False, oracle_generation_required=True,
                  generated_capture_loop_required=True, **{f'{gate_key(e)}_required': True for e in [*EXPERIMENTS, *COLLISIONS]})
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
        codegen = build / f'oracle_codegen{ext}'
        test_env = dict(os.environ, WC3TEST_RUNNER=str(runner), ORACLE_CODEGEN=str(codegen))
        generated, generation = generate(codegen, [Path('scenarios')])
        for name, text in generated.items():
            if (GOLDENS / name).read_bytes() != text:
                raise ValueError(f'{name}: oracle generator differs from the committed golden')
            target = build / 'ci/generated' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text)
        if load(GOLDENS / 'manifest.json') != generation:
            raise ValueError('oracle generation manifest differs from the committed golden')
        write_json(build / 'ci/generated/manifest.json', generation)
        write_json(reports / 'generator-audit.json', audit(build / 'ci/generated'))
        result['oracle_generation'] = dict(status='PASS', manifest=generation)
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
            command = [runner, *SCENARIOS, '--model', model, '--phase', phase, '--seed', '1']
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
                inputs = scenario_inputs(identity)
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
                       regression_verdict=assessment['regression_verdict'], improvements=len(assessment['improvements']),
                       scenario_sha256=inputs)
                if assessment['regression_verdict'] != 'PASS':
                    result['errors'][name] = f"{len(assessment['regressions'])} protected metrics regressed; see {report_dir / 'regression.md'}"
                if name == 'v4' and (code != 0 or assessment['compatibility_passes'] != 10):
                    result['errors'][name] = 'primary compatibility requires all ten MOV passes'
            except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
                result['errors'][name] = str(error)
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
        check_generated_loop(runner, build, reports, result)
        for experiment in EXPERIMENTS:
            check_experiment(build, reports, result, experiment)
        for experiment in COLLISIONS:
            check_collision(build, reports, result, experiment)
        result['mov0023_required'] = True
        ext = '.exe' if os.name == 'nt' else ''
        code = run_three_footmen(build / f'wc3test{ext}', build / f'oracle_codegen{ext}',
                                build / 'ci/mov-0023', reports)
        result['mov0023'] = dict(status='PASS' if code == 0 else 'FAIL')
        if code:
            result['errors']['mov-0023'] = 'three-unit evidence or frozen prediction verdict changed'
        result['status'] = 'PASS' if not result['errors'] and len(result['models']) == 5 else 'FAIL'
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

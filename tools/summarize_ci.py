#!/usr/bin/env python3
"""Measure build scope from downloaded CI artifacts; no cross-host byte assumption."""
import argparse
import json
from pathlib import Path
import tempfile

from compare_traces import compare, verify_reference_provenance
from normalize_generated import normalize
from run_generated import FIXTURES
from regression import CASES, validate_report
from run_ci import BASELINES, gate_key
from generate_oracle import GOLDENS
from audit_oracle import audit
from run_mov0013 import CASES as GENERATED_CASES, EXPERIMENTS, FIXTURES as EXPERIMENT_FIXTURES, assess as assess_experiment, exact, labels
from run_mov0018 import EXPERIMENTS as COLLISIONS, gate_key, grade as grade_collision
from trace_contract import EXPERIMENT_SHAPES, GENERATED_SHAPES, digest, load, payload, sha256, validate, write_json

CONFIGURATIONS = ('mac-arm-release', 'mac-arm-debug', 'linux-gcc-release',
                  'linux-clang-debug', 'windows-msvc-release')


def verify_generation(root, result):
    generation = result.get('oracle_generation')
    if result.get('oracle_generation_required') and not generation:
        raise ValueError('required oracle generation evidence missing')
    if generation:
        if generation['status'] != 'PASS' or generation['manifest'] != load(root / 'generated/manifest.json'):
            raise ValueError('oracle generation result/manifest differs')
        if generation['manifest'] != load(GOLDENS / 'manifest.json'):
            raise ValueError('oracle generation differs from committed goldens/source identities')
        for entry in generation['manifest']['inputs']:
            if sha256(root / 'generated' / entry['case']['file']) != entry['case']['sha256']:
                raise ValueError('generated JASS digest differs from the downloaded bytes')
        if load(root / 'reports/generator-audit.json')['status'] != 'PASS':
            raise ValueError('independent JASS call audit did not pass')
        audit(root / 'generated')
    return generation


def verify_generated_loop(root, result, legacy_before_generated_captures=False):
    loop = result.get('generated_capture_loop')
    if not legacy_before_generated_captures and result.get('generated_capture_loop_required') is not True:
        raise ValueError('required generated capture loop disabled or requirement missing')
    if (not legacy_before_generated_captures or result.get('generated_capture_loop_required')) and (not loop or loop['status'] != 'PASS'):
        raise ValueError('required generated capture loop missing or failing')
    if not loop or loop['status'] == 'UNOBSERVED':
        return None  # Historical workflows before the real reproduction captures.
    report = load(root / 'reports/generated-loop.json')
    if loop['status'] != 'PASS' or report['status'] != 'PASS':
        raise ValueError('generated capture loop did not pass')
    if [c['map_revision'] for c in report['cases']] != list(GENERATED_SHAPES):
        raise ValueError('generated capture loop has missing or unexpected revisions')
    scenarios, observations, cpp = {}, {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for row in report['cases']:
            label = row['map_revision']
            exp = GENERATED_SHAPES[label][0]
            reference_path = root / 'generated-loop/references' / f'{label}.json'
            actual_path = root / 'generated-loop/traces' / label / f'{exp}.json'
            reproduction = normalize(label, Path(tmp))
            if (reference_path.read_bytes() != (FIXTURES / f'{label}.json').read_bytes()
                    or row['reproduction'] != reproduction or reproduction['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded WC3 fixture/reproduction differs from retained evidence')
            reference, actual = load(reference_path), load(actual_path)
            if actual['identity']['model']['name'] != 'footman-v4':
                raise ValueError(f'{label}: generated loop did not run the required v4 model')
            verify_reference_provenance(reference)
            comparison = compare(reference, actual)
            comparison.update(reference_sha256=sha256(reference_path), actual_sha256=sha256(actual_path))
            if row['status'] != 'PASS' or comparison['status'] != 'PASS' or row['comparison'] != comparison:
                raise ValueError(f'{label}: downloaded generated comparison does not reproduce')
            if row['scenario'] != reference['provenance']['scenario']:
                raise ValueError(f'{label}: generated comparison names different scenario bytes')
            scenarios[exp] = row['scenario']['sha256']
            observations[label] = reproduction['observations']['generated_sha256']
            cpp[label] = digest(payload(actual))
    return dict(status='PASS', compatibility_passes=len(report['cases']), scenario_sha256=scenarios,
                wc3_observation_sha256=observations, cpp_payload_sha256=cpp)


def verify_experiment(root, result, experiment, legacy=False):
    """Regrade downloaded experiment traces against retained evidence and the reviewed list."""
    key, name = gate_key(experiment), experiment.lower()
    if legacy and f'{key}_required' not in result:
        return None  # Workflows before this experiment.
    if result.get(f'{key}_required') is not True or result.get(key, {}).get('status') != 'PASS':
        raise ValueError(f'required {experiment} gate missing, disabled or failing')
    report = load(root / f'reports/{name}.json')
    if report['status'] != 'PASS' or [c['map_revision'] for c in report['cases']] != labels(experiment):
        raise ValueError(f'{experiment} report did not pass or has missing/unexpected revisions')
    cpp = {}
    with tempfile.TemporaryDirectory() as tmp:
        for row in report['cases']:
            label = row['map_revision']
            reference_path = root / name / 'references' / f'{label}.json'
            actual_path = root / name / 'traces' / label / f'{experiment}.json'
            reproduction = normalize(label, Path(tmp))
            if (reference_path.read_bytes() != (EXPERIMENT_FIXTURES / f'{label}.json').read_bytes()
                    or row['reproduction'] != reproduction or reproduction['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded WC3 fixture/reproduction differs from retained evidence')
            if row['case_sha256'] != load(GENERATED_CASES / f'{label}-generation.json')['inputs'][0]['case']['sha256']:
                raise ValueError(f'{label}: {experiment} ran a different generated case')
            reference, actual = load(reference_path), load(actual_path)
            if actual['identity']['model']['name'] != 'footman-v4':
                raise ValueError(f'{label}: {experiment} did not run the required v4 model')
            verify_reference_provenance(reference)
            if row['scenario'] != reference['provenance']['scenario'] or row['scenario'] != actual['provenance']['scenario']:
                raise ValueError(f'{label}: {experiment} names different scenario bytes')
            comparison = compare(reference, actual)
            comparison.update(reference_sha256=sha256(reference_path), actual_sha256=sha256(actual_path))
            compared, differences = exact(reference, actual)
            # Frame attribution needs wc3states; the state differences themselves are recomputed.
            assessment = assess_experiment(label, comparison['status'], differences, row['frames_read'])
            if (row['comparison'] != comparison or row['exact']['mismatches'] != differences
                    or row['exact']['compared'] != compared or row['assessment'] != assessment
                    or assessment['status'] != 'PASS' or row['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded {experiment} grading does not reproduce')
            cpp[label] = digest(payload(actual))
    return dict(status='PASS', cases=len(report['cases']), cpp_payload_sha256=cpp)


def verify_collision(root, result, experiment, legacy=False):
    """Regrade downloaded MOV-0018..0020 traces: P3 acceptance and the reviewed differences."""
    key, name = gate_key(experiment), experiment.lower()
    if legacy and f'{key}_required' not in result:
        return None  # Workflows before this experiment's gate.
    if result.get(f'{key}_required') is not True or result.get(key, {}).get('status') != 'PASS':
        raise ValueError(f'required {experiment} gate missing, disabled or failing')
    report = load(root / f'reports/{key}.json')
    if report['status'] != 'PASS' or [c['map_revision'] for c in report['cases']] != labels(experiment):
        raise ValueError(f'{experiment} report did not pass or has missing/unexpected revisions')
    cpp = {}
    with tempfile.TemporaryDirectory() as tmp:
        for row in report['cases']:
            label = row['map_revision']
            reference_path = root / name / 'references' / f'{label}.json'
            actual_path = root / name / 'traces' / label / f'{experiment}.json'
            reproduction = normalize(label, Path(tmp))
            if (reference_path.read_bytes() != (EXPERIMENT_FIXTURES / f'{label}.json').read_bytes()
                    or row['reproduction'] != reproduction or reproduction['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded WC3 fixture/reproduction differs from retained evidence')
            if row['case_sha256'] != load(GENERATED_CASES / f'{label}-generation.json')['inputs'][0]['case']['sha256']:
                raise ValueError(f'{label}: {experiment} ran a different generated case')
            reference, actual = load(reference_path), load(actual_path)
            if actual['identity']['model']['name'] != 'footman-v4':
                raise ValueError(f'{label}: {experiment} did not run the required v4 model')
            verify_reference_provenance(reference)
            if row['scenario'] != reference['provenance']['scenario'] or row['scenario'] != actual['provenance']['scenario']:
                raise ValueError(f'{label}: {experiment} names different scenario bytes')
            comparison, assessment, accepted = grade_collision(label, reference, actual)
            comparison.update(reference_sha256=sha256(reference_path), actual_sha256=sha256(actual_path))
            if (row['comparison'] != comparison or row['assessment'] != assessment or row['acceptance'] != accepted
                    or assessment['status'] != 'PASS' or accepted['reviewed'] != 'PASS' or row['status'] != 'PASS'):
                raise ValueError(f'{label}: downloaded {experiment} grading does not reproduce')
            cpp[label] = digest(payload(actual))
    return dict(status='PASS', cases=len(report['cases']), cpp_payload_sha256=cpp)


def summarize(artifacts, out, legacy_before_generated_captures=False, include_windows=False):
    # Windows is temporarily disabled by the owner (15 October 2026).
    # Retain the five-platform mode for explicit historical artifact regrading.
    configurations = CONFIGURATIONS if include_windows else CONFIGURATIONS[:-1]
    out.mkdir(parents=True, exist_ok=True)
    report = dict(status='FAIL', configurations={}, errors={}, models={},
                  required_configurations=list(configurations),
                  disabled_configurations=[] if include_windows else ['windows-msvc-release'],
                  scope='measured artifact-producing configurations of this workflow run only; '
                        'movement RNG unused; retail RNG/other hosts remain UNKNOWN')
    for config in configurations:
        root = artifacts / f'compatibility-{config}'
        try:
            result = load(root / 'reports/result.json')
            environment = load(root / 'reports/environment.json')
            identity = load(root / 'reports/v4/build-identity.json')
            generation = verify_generation(root, result)
            generated_loop = verify_generated_loop(root, result, legacy_before_generated_captures)
            experiments = {e: verify_experiment(root, result, e, legacy_before_generated_captures) for e in EXPERIMENTS}
            for experiment in COLLISIONS:
                experiments[experiment] = verify_collision(root, result, experiment, legacy_before_generated_captures)
            suites = {}
            for model in BASELINES:
                suite = validate_report(load(root / 'reports' / model / 'comparison.json'))
                assessment = load(root / 'reports' / model / 'regression.json')
                repeated = load(root / 'reports' / model / 'repeatability.json')
                traces = [validate(load(root / 'traces' / model / f'{case}.json')) for case in CASES]
                # Recheck payload and full metadata hashes in downloaded artifacts.
                for case, trace in zip(CASES, traces):
                    name = f'{case}.json'
                    if repeated['observation_payload_sha256'][name] != [digest(payload(trace))] * 2:
                        raise ValueError(f'{model}/{case}: artifact payload hash mismatch')
                    for suffix in ('.json', '.csv', '-actions.csv'):
                        file = f'{case}{suffix}'
                        hashes = [sha256(root / 'traces' / folder / file) for folder in (model, model + '-repeat')]
                        if repeated['full_file_sha256'][file] != hashes or hashes[0] != hashes[1]:
                            raise ValueError(f'{model}/{file}: artifact full hash mismatch')
                # Each configuration graded the same committed scenario files.
                described = load(root / 'reports' / model / 'build-identity.json')['scenarios']
                for case, trace, row in zip(CASES, traces, described):
                    if row['experiment'] != case or trace['provenance']['scenario']['sha256'] != row['sha256']:
                        raise ValueError(f'{model}/{case}: trace and run identity name different scenarios')
                suites[model] = dict(compatibility_passes=sum(c['status'] == 'PASS' for c in suite['cases']),
                    regression_verdict=assessment['regression_verdict'],
                    payload_sha256={k: v[0] for k, v in repeated['observation_payload_sha256'].items()},
                    full_trace_sha256={k: v[0] for k, v in repeated['full_file_sha256'].items() if k.endswith('.json')},
                    scenario_sha256={row['experiment']: row['sha256'] for row in described})
                if generation and suites[model]['scenario_sha256'] != {
                        e['experiment']: e['scenario']['sha256'] for e in generation['manifest']['inputs']}:
                    raise ValueError('oracle generator and C++ suite consumed different scenarios')
            report['configurations'][config] = dict(ci_status=result['status'], host=result['host'],
                     environment=environment, primary_identity=identity, models=suites,
                     oracle_generation=generation, generated_capture_loop=generated_loop, experiments=experiments)
            if result['status'] != 'PASS':
                report['errors'][config] = result['errors'] or 'configuration did not pass'
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            report['errors'][config] = str(error)
    for model in BASELINES:
        configs = {k: v['models'][model] for k, v in report['configurations'].items()}
        variants = {case: len({c['payload_sha256'][f'{case}.json'] for c in configs.values()}) for case in CASES}
        full_variants = {case: len({c['full_trace_sha256'][f'{case}.json'] for c in configs.values()}) for case in CASES}
        scenario_hashes = {json.dumps(c['scenario_sha256'], sort_keys=True) for c in configs.values()}
        if len(scenario_hashes) > 1:
            report['errors'][f'{model}-scenarios'] = 'configurations ran different scenario files'
        report['models'][model] = dict(configurations_compared=list(configs),
                    scenario_inputs='IDENTICAL' if len(scenario_hashes) == 1 else 'DIFFERENT',
                    observation_payload_variants=variants, full_trace_variants=full_variants,
                    observation_byte_equality=('UNVERIFIED' if len(configs) < 2 else
                                              'IDENTICAL' if all(v == 1 for v in variants.values()) else 'DIFFERENT'),
                    compatibility_passes={k: v['compatibility_passes'] for k, v in configs.items()})
    generators = {k: v['oracle_generation'] for k, v in report['configurations'].items() if v['oracle_generation']}
    variants = {digest(g['manifest']) for g in generators.values()}
    if generators and (len(generators) != len(configurations) or len(variants) != 1):
        report['errors']['oracle-generation'] = 'missing configuration evidence or different generated JASS/inputs'
    report['oracle_generation'] = dict(status='IDENTICAL' if generators and len(variants) == 1 else 'UNOBSERVED',
                                      configurations_compared=list(generators))
    loops = {k: v['generated_capture_loop'] for k, v in report['configurations'].items() if v['generated_capture_loop']}
    if loops and (len(loops) != len(configurations) or len({digest(v) for v in loops.values()}) != 1):
        report['errors']['generated-capture-loop'] = 'missing configuration evidence or different scenario/observation inputs'
    report['generated_capture_loop'] = dict(status=('FAIL' if 'generated-capture-loop' in report['errors']
                                                  else 'PASS' if loops else 'UNOBSERVED'),
                                          configurations_compared=list(loops),
                                          compatibility_passes={k: v['compatibility_passes'] for k, v in loops.items()})
    report['experiments'] = {}
    for experiment in [*EXPERIMENTS, *COLLISIONS]:
        studies = {k: v['experiments'][experiment] for k, v in report['configurations'].items()
                   if v['experiments'][experiment]}
        if studies and (len(studies) != len(configurations) or len({digest(v) for v in studies.values()}) != 1):
            report['errors'][experiment.lower()] = f'missing configuration evidence or different C++ {experiment} payloads'
        report['experiments'][experiment] = dict(
            status='FAIL' if experiment.lower() in report['errors'] else 'PASS' if studies else 'UNOBSERVED',
            configurations_compared=list(studies))
    report['status'] = 'PASS' if not report['errors'] and len(report['configurations']) == len(configurations) else 'FAIL'
    write_json(out / 'scope.json', report)
    lines = ['# Measured build scope', '', f"CI scope gate: **{report['status']}**.", '', report['scope'], '',
             ('Windows/MSVC: **DISABLED / UNOBSERVED for this run** (owner decision, 15 October 2026).'
              if not include_windows else 'Windows/MSVC included in this explicit five-configuration regrade.'), '',
             'Payload hashes exclude build/transport identity; full trace hashes include it.',
             'Cross-configuration byte differences are reported, while each configuration is graded against the same WC3 fixtures.', '',
             f"Oracle generation: **{report['oracle_generation']['status']}** across {len(generators)} configurations.", '',
             f"Generated-map capture/comparison: **{report['generated_capture_loop']['status']}** across {len(loops)} configurations.", '',
             *[f"{e} reviewed differences, regraded: **{v['status']}** across {len(v['configurations_compared'])} configurations."
               for e, v in report['experiments'].items()], '',
             '| Configuration | Host / target | Compiler | Build | CI | v4 compatibility |', '|---|---|---|---|---|---|']
    for config, info in report['configurations'].items():
        identity = info['primary_identity']
        lines.append(f"| {config} | {info['host']['system']} {info['host']['architecture']} / {identity['architecture']} | "
                     f"{identity['compiler']} | {identity['build_type']} | {info['ci_status']} | {info['models']['v4']['compatibility_passes']}/10 PASS |")
    lines += ['', '| Model | Observation payload equality | Distinct payloads per case | Full trace variants per case | Scenario inputs |',
              '|---|---|---|---|---|']
    for model, info in report['models'].items():
        lines.append(f"| {model} | {info['observation_byte_equality']} | {list(info['observation_payload_variants'].values())} | "
                     f"{list(info['full_trace_variants'].values())} | {info['scenario_inputs']} |")
    for config, error in report['errors'].items():
        lines += ['', f'**{config}:** {error}']
    (out / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"Build scope {report['status']}; {len(report['configurations'])}/{len(configurations)} configurations measured")
    return int(report['status'] != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--legacy-before-generated-captures', action='store_true',
                        help='explicit historical recheck only: workflow predates the committed generated captures')
    parser.add_argument('--include-windows', action='store_true',
                        help='explicit five-configuration regrade, including temporarily disabled Windows/MSVC')
    args = parser.parse_args()
    return summarize(args.artifacts, args.out, args.legacy_before_generated_captures, args.include_windows)


if __name__ == '__main__':
    raise SystemExit(main())

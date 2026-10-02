#!/usr/bin/env python3
"""Measure build scope from downloaded CI artifacts; no cross-host byte assumption."""
import argparse
import json
from pathlib import Path

from regression import CASES, validate_report
from run_ci import BASELINES
from generate_oracle import GOLDENS
from audit_oracle import audit
from trace_contract import digest, load, payload, sha256, validate, write_json

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


def summarize(artifacts, out):
    out.mkdir(parents=True, exist_ok=True)
    report = dict(status='FAIL', configurations={}, errors={}, models={},
                  scope='measured artifact-producing configurations of this workflow run only; '
                        'movement RNG unused; retail RNG/other hosts remain UNKNOWN')
    for config in CONFIGURATIONS:
        root = artifacts / f'compatibility-{config}'
        try:
            result = load(root / 'reports/result.json')
            environment = load(root / 'reports/environment.json')
            identity = load(root / 'reports/v4/build-identity.json')
            generation = verify_generation(root, result)
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
                     environment=environment, primary_identity=identity, models=suites, oracle_generation=generation)
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
    if generators and (len(generators) != len(CONFIGURATIONS) or len(variants) != 1):
        report['errors']['oracle-generation'] = 'missing configuration evidence or different generated JASS/inputs'
    report['oracle_generation'] = dict(status='IDENTICAL' if generators and len(variants) == 1 else 'UNOBSERVED',
                                      configurations_compared=list(generators))
    report['status'] = 'PASS' if not report['errors'] and len(report['configurations']) == len(CONFIGURATIONS) else 'FAIL'
    write_json(out / 'scope.json', report)
    lines = ['# Measured build scope', '', f"CI scope gate: **{report['status']}**.", '', report['scope'], '',
             'Payload hashes exclude build/transport identity; full trace hashes include it.',
             'Cross-configuration byte differences are reported, while each configuration is graded against the same WC3 fixtures.', '',
             f"Oracle generation: **{report['oracle_generation']['status']}** across {len(generators)} configurations.", '',
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
    print(f"Build scope {report['status']}; {len(report['configurations'])}/{len(CONFIGURATIONS)} configurations measured")
    return int(report['status'] != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    return summarize(args.artifacts, args.out)


if __name__ == '__main__':
    raise SystemExit(main())

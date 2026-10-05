"""Canonical v1 trace values, shape and validation; no simulation dependencies."""
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

from wc3_float import add, bits

ROOT = Path(__file__).resolve().parents[1]
BUILD = 'wc3-1.29.2-9231-x86'
SCHEMA = 'wc3-trace'
# The one tolerance declaration, shared by canonical and historical CSV tools.
TOLERANCES = {'x': .001, 'y': .001, 'facing': .001, 'order': 0, 't': .0000615}
KINDS = {'BEGIN', 'SETUP', 'WATCH', 'RUN', 'TICK', 'SAMPLE', 'ACTION', 'EVENT', 'END'}
TIMED = {'TICK', 'SAMPLE', 'ACTION', 'EVENT'}
REAL = re.compile(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')
LABELS = [f'MOV-{n:04d}' if n != 2 else 'MOV-0002-r2' for n in range(1, 11)] + [
    f'JASS-0001-p{p:03d}' for p in (1, 10, 20, 25, 50)]
RETAINED_MOV = {label[:8]: label for label in LABELS if label.startswith('MOV')}
# Independently reviewed Phase 6 reproductions. This is not generated from YAML;
# the original 15-label normalization suite and all tolerances stay unchanged.
GENERATED_SHAPES = {
    'MOV-0002-g1': ('MOV-0002', 250, '0.020000', 2),
    'MOV-0004-g1': ('MOV-0004', 600, '0.020000', 1),
    'MOV-0006-g1': ('MOV-0006', 250, '0.020000', 1),
    'MOV-0010-g1': ('MOV-0010', 250, '0.020000', 1),
}
# Generated experiments of their own (docs/mov-0013.md to docs/mov-0015.md), written
# here by hand from the experiment definition, never from a scenario. Each binds one
# v2 scenario file; `start_us` is its declared sampler start, `control` the retained
# capture whose observations the revision must reproduce exactly (or None).
EXPERIMENT_SHAPES = {
    f'{exp}-{v}': dict(experiment=exp, callbacks=1000, period='0.001000', units=1,
                       scenario=f'scenarios/{exp}/{exp}-{v}.yaml', start_us=start,
                       control='MOV-0012-a' if (exp, v) == ('MOV-0013', 'a') else None, state='STATE',
                       definition=f'docs/{exp.lower()}.md', version=2)
    for exp, variants in (('MOV-0013', (('a', 0), ('b', 2500), ('c', 20000), ('d', 0))),
                          ('MOV-0014', (('a', 300000), ('b', 720000), ('c', 900000))),
                          ('MOV-0015', (('a', 120000), ('b', 450000), ('c', 999054), ('d', 997001))))
    for v, start in variants}
# MOV-0018 (docs/mov-0018.md): two Footmen, v1 timing (callback 0 at the setup, 20 ms
# sampling, no STATE event), 600 callbacks so both units are idle well before the end.
EXPERIMENT_SHAPES.update({
    f'MOV-0018-{v}': dict(experiment='MOV-0018', callbacks=600, period='0.020000', units=2,
                          scenario=f'scenarios/MOV-0018/MOV-0018-{v}.yaml', start_us=0, control=None,
                          state=None, definition='docs/mov-0018.md', version=1)
    for v in 'abcd'})
# MOV-0019 (docs/mov-0019.md): the same shape, ten variants pinning MOV-0018's pathing fits.
EXPERIMENT_SHAPES.update({
    f'MOV-0019-{v}': dict(experiment='MOV-0019', callbacks=600, period='0.020000', units=2,
                          scenario=f'scenarios/MOV-0019/MOV-0019-{v}.yaml', start_us=0, control=None,
                          state=None, definition='docs/mov-0019.md', version=1)
    for v in 'abcdefghij'})
# MOV-0020 (docs/mov-0020.md): the same shape, MOV-0019's crossings with the units' roles swapped.
EXPERIMENT_SHAPES.update({
    f'MOV-0020-{v}': dict(experiment='MOV-0020', callbacks=600, period='0.020000', units=2,
                          scenario=f'scenarios/MOV-0020/MOV-0020-{v}.yaml', start_us=0, control=None,
                          state=None, definition='docs/mov-0020.md', version=1)
    for v in 'abcdef'})
# MOV-0021 (docs/mov-0021.md): the same shape, MOV-0019-j's offset head-on mirrored and turned.
EXPERIMENT_SHAPES.update({
    f'MOV-0021-{v}': dict(experiment='MOV-0021', callbacks=600, period='0.020000', units=2,
                          scenario=f'scenarios/MOV-0021/MOV-0021-{v}.yaml', start_us=0, control=None,
                          state=None, definition='docs/mov-0021.md', version=1)
    for v in 'abcdef'})
STATE_KEYS = {'c10_9', 'x_9', 'y_9', 'facing_9'}
# wc3test arguments selecting the committed scenarios (docs/scenario-v1.md). Run it
# with cwd=ROOT and an absolute --out so recorded scenario paths stay repo-relative.
SCENARIOS = ['--scenario', 'scenarios']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, required):
    require(isinstance(value, dict) and set(value) == set(required), f'expected fields {required}')


def integer(value, lo=0, hi=2**32-1):
    require(type(value) is int and lo <= value <= hi, 'integer type/range violation')
    return value


def number(value):
    require(isinstance(value, str) and len(value) <= 64 and REAL.fullmatch(value), 'invalid numeric string')
    parsed = float(value)
    require(math.isfinite(parsed) and abs(parsed) <= 1e12, 'nonfinite/overflow/out-of-range numeric value')
    return parsed


def order(value):
    require(isinstance(value, str) and len(value) <= 10 and value.isascii() and value.isdigit(), 'invalid order')
    integer(int(value))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write_json(path, value, compact_records=False):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if compact_records:
        # One record per line keeps committed evidence reviewable; numeric strings
        # and payload hashing are independent of JSON whitespace and key order.
        header = json.dumps({k: v for k, v in value.items() if k != 'records'}, indent=2, allow_nan=False)
        records = ',\n'.join('    ' + json.dumps(r, separators=(',', ':'), allow_nan=False) for r in value['records'])
        encoded = header[:-2] + ',\n  "records": [\n' + records + '\n  ]\n}'
    else:
        encoded = json.dumps(value, indent=2, allow_nan=False)
    Path(path).write_text(encoded + '\n', encoding='utf-8', newline='\n')


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f'nonfinite JSON constant {value}')
    value = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    finite_json(value)
    return value


def finite_json(value):
    """JSON's numeric syntax permits overflowing binary64 even without NaN tokens."""
    if isinstance(value, dict):
        for child in value.values(): finite_json(child)
    elif isinstance(value, list):
        for child in value: finite_json(child)
    elif type(value) is float:
        require(math.isfinite(value) and abs(value) <= 1e12, 'nonfinite/overflow JSON number')
    elif type(value) is int:
        require(abs(value) <= 10**12, 'overflow JSON integer')


def generated_revision(label):
    """Supported v1 packaging revisions; shapes come from reviewed controls, not YAML."""
    return bool(isinstance(label, str) and label not in LABELS and re.fullmatch(
        r'MOV-(?:0002|0004|0006|0010)-[a-z0-9]+(?:-[a-z0-9]+)*', label))


def shape(label):
    if label in GENERATED_SHAPES:
        return GENERATED_SHAPES[label]
    if generated_revision(label):
        return shape(RETAINED_MOV[label[:8]])
    if label in EXPERIMENT_SHAPES:
        e = EXPERIMENT_SHAPES[label]
        return e['experiment'], e['callbacks'], e['period'], e['units']
    require(label in LABELS, f'unsupported scenario revision {label}')
    if label.startswith('MOV'):
        return ('MOV-0002' if label == 'MOV-0002-r2' else label,
                600 if label == 'MOV-0004' else 250, '0.020000', 2 if label == 'MOV-0002-r2' else 1)
    p = int(label[-3:])
    return 'JASS-0001', {1: 500, 10: 500, 20: 250, 25: 200, 50: 100}[p], f'{p/1000:.6f}', 1


def requested(callback, period):
    return format(Decimal(period) * callback, '.6f')


def counts(records):
    return {'complete': True, 'records': len(records), **{
        key: sum(r['kind'] == kind for r in records) for key, kind in (
            ('ticks', 'TICK'), ('samples', 'SAMPLE'), ('actions', 'ACTION'), ('events', 'EVENT'))}}


def payload(trace):
    return {k: trace[k] for k in ('scenario', 'units', 'time', 'records', 'completion')}


def raw_record(raw, period, callback=None):
    """Lossless semantic mapping of one already parsed oracle-v1 record."""
    f = raw.split('|')
    seq, kind = int(f[1]), f[2]
    rec = {'seq': seq, 'kind': kind, 'source': {'seq': seq, 'payload': raw}}
    if kind not in TIMED:
        rec['fields'] = f[3:]
        return rec
    require(len(f) >= 5, 'malformed raw timed record')
    if kind == 'TICK':
        require(len(f) == 5, 'malformed raw TICK')
        callback = int(f[4])
    rec.update(callback=callback, time={'requested': requested(callback, period), 'reported': f[3], 'state_us': None})
    if kind == 'SAMPLE':
        require(len(f) == 9, 'malformed raw SAMPLE')
        rec.update(unit=f[4], values=dict(zip(('x', 'y', 'facing', 'order'), f[5:9])))
    elif kind == 'ACTION':
        require(len(f) in (7, 9) and f[-1] in ('accepted=0', 'accepted=1'), 'malformed raw ACTION')
        rec.update(unit=f[4], command=f[5], accepted=f[-1] == 'accepted=1',
                   target={'x': f[6], 'y': f[7]} if len(f) == 9 else None)
    elif kind == 'EVENT':
        rec.update(name=f[4], values=dict(field.split('=', 1) for field in f[5:]))
        require(len(rec['values']) == len(f[5:]) and all(rec['values']), 'duplicate/empty raw EVENT property')
    return rec


def validate_cadence_parameters(parameters):
    """footman-v1/v2 parameters."""
    keys(parameters, ('position_period_steps', 'facing_period_steps', 'facing_phase_steps', 'move_delay_steps', 'stop_radius', 'default_speed', 'speed_clamp', 'movement_angle_limit_degrees', 'turn_ramp_radians', 'opposite_angle_tie'))
    for key in ('position_period_steps', 'facing_period_steps'):
        integer(parameters[key], 1, 10000)
    for key in ('facing_phase_steps', 'move_delay_steps'):
        integer(parameters[key], 0, 10000)
    for key in ('stop_radius', 'default_speed'):
        require(type(parameters[key]) in (int, float) and parameters[key] >= 0, 'invalid model parameter')
    require(parameters['movement_angle_limit_degrees'] == 'unlimited' or
            (type(parameters['movement_angle_limit_degrees']) in (int, float) and 0 <= parameters['movement_angle_limit_degrees'] <= 180), 'invalid angle limit')
    for key, size in (('speed_clamp', 2), ('turn_ramp_radians', 3)):
        require(isinstance(parameters[key], list) and len(parameters[key]) == size
                and all((type(v) in (int, float) and v >= 0) or
                        (key == 'turn_ramp_radians' and v == 'unlimited')
                        for v in parameters[key]), 'invalid parameter array')
    keys(parameters['opposite_angle_tie'], ('turn', 'within_degrees'))
    require(parameters['opposite_angle_tie']['turn'] == 'clockwise' and
            type(parameters['opposite_angle_tie']['within_degrees']) in (int, float) and
            0 <= parameters['opposite_angle_tie']['within_degrees'] <= 180, 'invalid angle tie')


def validate_v3_parameters(parameters):
    """footman-v3: separate heading, phased logical updates, truncating float32."""
    keys(parameters, ('update_period_steps', 'update_phase_steps', 'exposure_period_steps', 'stop_radius',
                      'default_speed', 'speed_clamp', 'turn_rate_radians', 'propulsion_window_degrees',
                      'facing_acceleration_radians', 'facing_max_velocity_radians', 'facing_snap_radians',
                      'facing_braking', 'frame_origin', 'float_rounding', 'opposite_angle_tie'))
    for key in ('update_period_steps', 'exposure_period_steps'):
        integer(parameters[key], 1, 10000)
    integer(parameters['update_phase_steps'], 0, 10000)
    require(parameters['update_period_steps'] % parameters['exposure_period_steps'] == 0, 'exposures must divide updates')
    for key in ('stop_radius', 'default_speed', 'turn_rate_radians', 'facing_acceleration_radians',
                'facing_max_velocity_radians', 'facing_snap_radians'):
        require(type(parameters[key]) in (int, float) and parameters[key] >= 0, 'invalid model parameter')
    require(type(parameters['propulsion_window_degrees']) in (int, float) and 0 <= parameters['propulsion_window_degrees'] <= 180, 'invalid propulsion window')
    require(type(parameters['frame_origin']) in (int, float), 'invalid frame origin')
    require(isinstance(parameters['speed_clamp'], list) and len(parameters['speed_clamp']) == 2
            and all(type(v) in (int, float) and v >= 0 for v in parameters['speed_clamp']), 'invalid parameter array')
    require(parameters['facing_braking'] == 'error * (error / max_velocity)^0.25'
            and parameters['float_rounding'] == 'toward-zero'
            and parameters['opposite_angle_tie'] == {'turn': 'counter-clockwise', 'within_degrees': 0}, 'unsupported v3 rule')


# footman-v4's reported callback time: TimerGetElapsed of the library's 1000 s timer.
LIBRARY_CLOCK = 'sub(1000, sub(add(start, 1000), scheduled)); scheduled += 0.02 per callback'
# Scenario v2 runs (docs/scenario-v2.md) also declare their observation rule.
LIBRARY_CLOCK_V2 = ('sub(1000, floor32(1000 + floor(start, 2^-17) - scheduled)); start = scheduled(0) = add(0.5, observe.start); '
                    'scheduled += period per callback; a callback observes every frame with clock <= scheduled')


def scheduled_frame_us(start_us, period, callback, _cache={}):
    """Scenario v2 H0: the latest 5 ms frame whose float32 clock is at or before the
    sampler's float32 scheduled time (docs/scenario-v2.md), as us after the 0.5 s setup.
    Both clocks are positive, so their bit patterns order like their values."""
    setup = bits(0.5)
    times, clocks, frames = _cache.setdefault((start_us, period), (
        [add(setup, bits(start_us / 1000000)) if start_us else setup], [setup], []))
    while len(frames) <= callback:
        while clocks[-1] <= times[len(frames)]:
            clocks.append(add(clocks[-1], bits(0.005)))
        frames.append(5000 * (len(clocks) - 2))
        times.append(add(times[-1], bits(float(period))))
    return frames[callback]


def retail_numeric_format(label):
    v2 = label in EXPERIMENT_SHAPES and EXPERIMENT_SHAPES[label]['version'] == 2
    return 'R2SW_6; STATE R2SW_9' if v2 else 'R2SW_6; CLOCKS R2SW_9'


def validate_v4_parameters(parameters, library_clock=LIBRARY_CLOCK):
    """footman-v4: retail soft-float arithmetic on the footman-v3 cadence."""
    v4_keys = ('update_period_steps', 'update_phase_steps', 'frame_steps', 'stop_radius',
               'default_speed', 'speed_clamp', 'turn_rate_radians', 'propulsion_window_degrees',
               'facing', 'frame_origin', 'clock_start_seconds', 'library_clock', 'arithmetic')
    # MOV-0018 added unit pathing (docs/mov-0018.md); earlier retained traces lack it.
    keys(parameters, v4_keys + (('unit_pathing',) if 'unit_pathing' in parameters else ()))
    if 'unit_pathing' in parameters:
        pathing = parameters['unit_pathing']
        keys(pathing, ('cell', 'blocked_cells', 'line_clearance', 'waypoint_radius', 'block_radius',
                       'block_lookahead', 'block_lateral', 'recheck_updates'))
        require(pathing['blocked_cells'] == "3x3 around each other unit's cell", 'unsupported unit pathing rule')
        integer(pathing['recheck_updates'], 1, 1000)
        for key in ('cell', 'line_clearance', 'waypoint_radius', 'block_radius', 'block_lookahead', 'block_lateral'):
            require(type(pathing[key]) in (int, float) and pathing[key] >= 0, 'invalid unit pathing parameter')
    for key in ('update_period_steps', 'frame_steps'):
        integer(parameters[key], 1, 10000)
    integer(parameters['update_phase_steps'], 0, 10000)
    require(parameters['update_period_steps'] % parameters['frame_steps'] == 0, 'frames must divide updates')
    for key in ('stop_radius', 'default_speed'):
        require(type(parameters[key]) in (int, float) and parameters[key] >= 0, 'invalid model parameter')
    require(type(parameters['propulsion_window_degrees']) in (int, float) and 0 <= parameters['propulsion_window_degrees'] <= 180, 'invalid propulsion window')
    require(type(parameters['frame_origin']) in (int, float), 'invalid frame origin')
    require(type(parameters['clock_start_seconds']) in (int, float) and parameters['clock_start_seconds'] >= 0, 'invalid clock start')
    require(isinstance(parameters['speed_clamp'], list) and len(parameters['speed_clamp']) == 2
            and all(type(v) in (int, float) and v >= 0 for v in parameters['speed_clamp']), 'invalid parameter array')
    require(parameters['turn_rate_radians'] == 'atof(0.6)'
            and parameters['facing'] == 'atof(0.07, 0.2, 0.2, 0.25, 0.001)'
            and parameters['library_clock'] == library_clock
            and parameters['arithmetic'] == 'wc3::sf retail soft-float', 'unsupported v4 rule')


def validate(trace, evidence_root=None):
    evidence_root = ROOT if evidence_root is None else evidence_root
    finite_json(trace)
    keys(trace, ('schema', 'version', 'scenario', 'identity', 'units', 'time', 'records', 'completion', 'provenance'))
    require(trace['schema'] == SCHEMA and type(trace['version']) is int and trace['version'] == 1, 'unsupported schema/version')
    scenario = trace['scenario']
    keys(scenario, ('experiment', 'map_revision', 'callbacks', 'requested_period'))
    exp, callbacks, period, units = shape(scenario['map_revision'])
    integer(scenario['callbacks'], 0, 10000)
    require(scenario == dict(experiment=exp, map_revision=scenario['map_revision'], callbacks=callbacks, requested_period=period), 'scenario identity/shape mismatch')
    experiment = EXPERIMENT_SHAPES.get(scenario['map_revision'])
    ident = trace['identity']
    keys(ident, ('engine', 'build', 'source', 'environment', 'seed', 'model'))
    require(ident['engine'] in ('wc3', 'cpp'), 'unsupported engine')
    retail = ident['engine'] == 'wc3'
    model_clock = not retail and isinstance(ident.get('model'), dict) and ident['model'].get('name') == 'footman-v4'
    keys(ident['seed'], ('status', 'value', 'retail_equivalent'))
    require(ident['seed']['retail_equivalent'] is False, 'retail seed equivalence unobserved')
    if retail:
        require(ident['build'] == BUILD and ident['model'] is None, 'wrong reference build/model')
        require(ident['seed'] == {'status': 'unset-unobserved', 'value': None, 'retail_equivalent': False}, 'invalid WC3 seed status')
        keys(ident['source'], ('map', 'library', 'case'))
        for source in [*ident['source'].values(), ident['environment']]:
            require(isinstance(source, dict) and isinstance(source.get('path'), str) and HASH.fullmatch(source.get('sha256', '')), 'missing source identity')
        label = scenario['map_revision']
        case_path = (f'oracle/generated/maps/{label}.j' if generated_revision(label) or experiment
                     else f'oracle/jass/{label}.j')
        require(ident['source']['map']['path'] == f'oracle-maps/{label}.w3m'
                and ident['source']['library']['path'] == 'oracle/jass/lib/oracle-v1.j'
                and ident['source']['case']['path'] == case_path
                and ident['environment']['path'] == f'oracle/environment/{BUILD}.json', 'source identity does not match scenario/build')
        manifest = load(evidence_root / f'oracle/captures/{BUILD}/{label}/manifest.json')
        for key in ('map', 'library', 'case'):
            require(ident['source'][key] == manifest[key], 'source identity differs from retained manifest')
        require(ident['environment'] == manifest['environment'], 'environment identity differs from retained manifest')
        if generated_revision(label) or experiment:
            used = manifest['scenario']
            version, path = (experiment['version'], experiment['scenario']) if experiment else (1, f'scenarios/{exp}.yaml')
            keys(used, ('schema', 'version', 'path', 'sha256'))
            require(used['schema'] == 'wc3-scenario' and used['version'] == version
                    and used['path'] == path and HASH.fullmatch(used['sha256']), 'invalid generated scenario identity')
            require(trace['provenance'].get('scenario') == used, 'generated trace/manifest scenario identity differs')
            setups = [r['fields'] for r in trace['records'] if r['kind'] == 'SETUP']
            require(len(setups) == 1 and setups[0][:2] == [f"scenario_sha256={used['sha256']}", f'scenario_version={version}'],
                    'generated capture SETUP does not bind the exact scenario')
    else:
        require(exp.startswith('MOV-'), 'C++ timing variants are unobserved/unsupported')
        require(isinstance(ident['build'], dict), 'missing C++ build identity')
        build = ident['build']
        for key in ('compiler', 'build_type', 'architecture', 'fp_contract', 'model', 'parameters', 'source_sha256', 'git_commit', 'git_dirty_at_configure', 'step_us', 'seed', 'observation_phase', 'state_lag_us', 'sample_period_us', 'rng', 'time_unit', 'cases'):
            require(key in build, f'missing C++ build field {key}')
        require(HASH.fullmatch(build['source_sha256']), 'invalid C++ source digest')
        require(ident['source'] == {'sha256': build['source_sha256']} and ident['environment'] is None, 'C++ source/environment mismatch')
        require(ident['model'] == {'name': build['model'], 'parameters': build['parameters']}, 'C++ model identity mismatch')
        require(build['model'] in ('footman-v1', 'footman-v2', 'footman-v3', 'footman-v4'), 'unsupported model')
        for key in ('compiler', 'build_type', 'architecture', 'fp_contract', 'rng'):
            require(isinstance(build[key], str) and build[key], f'invalid C++ {key}')
        require(build['git_commit'] is None or (isinstance(build['git_commit'], str) and re.fullmatch(r'[a-f0-9]{40}', build['git_commit'])), 'invalid revision')
        require(build['git_dirty_at_configure'] is None or type(build['git_dirty_at_configure']) is bool, 'invalid git dirty state')
        parameters = build['parameters']
        # Scenario v2 timing (docs/scenario-v2.md) exists only for registered experiments.
        scheduled = build['observation_phase'] == 'scheduled-sampler-time'
        require(scheduled == bool(experiment and experiment['version'] == 2), 'v2 timing only for a registered v2 experiment')
        if build['model'] == 'footman-v3':
            validate_v3_parameters(parameters)
        elif build['model'] == 'footman-v4':
            validate_v4_parameters(parameters, LIBRARY_CLOCK_V2 if scheduled else LIBRARY_CLOCK)
        else:
            validate_cadence_parameters(parameters)
        # The run's case table: the ten hard-coded cases, or the scenarios named
        # on the command line. Retained experiments keep their independent shape.
        require(isinstance(build['cases'], list) and 1 <= len(build['cases']) <= 1000, 'invalid build case table')
        tests = [case.get('test') if isinstance(case, dict) else None for case in build['cases']]
        require(len(set(tests)) == len(tests) and exp in tests, 'build case table lacks this experiment or repeats one')
        for case in build['cases']:
            keys(case, ('test', 'callbacks', 'units', 'samples'))
            require(isinstance(case['test'], str) and re.fullmatch(r'[A-Z]{2,5}-\d{4}', case['test']), 'invalid case test ID')
            for key in ('callbacks', 'units', 'samples'): integer(case[key], 0, 50000)
            require(case['samples'] == (case['callbacks'] + 1) * case['units'], 'inconsistent case sample count')
            if case['test'] in RETAINED_MOV:
                _, cb_count, _, unit_count = shape(RETAINED_MOV[case['test']])
                require((case['callbacks'], case['units']) == (cb_count, unit_count), 'build case table cannot redefine experiment')
        if 'scenarios' in build:
            # Scenario-driven run: every listed description is identified by hash, and
            # this trace's provenance names the one that produced it.
            require(isinstance(build['scenarios'], list) and [d.get('experiment') if isinstance(d, dict) else None
                    for d in build['scenarios']] == tests, 'scenario list differs from case table')
            for description in build['scenarios']:
                keys(description, ('experiment', 'map_revision', 'path', 'sha256'))
                require(isinstance(description['path'], str) and description['path']
                        and isinstance(description['map_revision'], str)
                        and HASH.fullmatch(description['sha256']), 'invalid scenario identity')
            keys(trace['provenance'], ('scenario',))
            used = trace['provenance']['scenario']
            keys(used, ('schema', 'version', 'path', 'sha256'))
            require(used['schema'] == 'wc3-scenario' and type(used['version']) is int
                    and used['version'] == (2 if scheduled else 1), 'unsupported scenario schema/version')
            if experiment:
                require(used['path'] == experiment['scenario'], 'trace from an unregistered scenario path')
            require(dict(experiment=exp, map_revision=scenario['map_revision'], path=used['path'], sha256=used['sha256'])
                    in build['scenarios'], 'scenario provenance differs from the run identity')
        else:
            require(trace['provenance'] == {}, 'hard-coded C++ trace with scenario provenance')
        require(ident['seed']['status'] == 'explicit-cpp-only', 'invalid C++ seed status')
        integer(ident['seed']['value'])
        require(build['seed'] == ident['seed']['value'], 'build seed mismatch')
        integer(build['step_us'], 1, 20000)
        if scheduled:
            require(build['model'] == 'footman-v4' and len(build['cases']) == 1, 'v2 timing needs footman-v4, one case per run')
            require(build['step_us'] == 1000 and build['time_unit'] == 'seconds'
                    and build['sample_period_us'] == round(Decimal(period) * 1000000)
                    and build.get('sampler_start_us') == experiment['start_us'], 'unsupported C++ v2 timing')
        else:
            require(build['step_us'] == 1000 and build['sample_period_us'] == 20000 and build['time_unit'] == 'seconds', 'unsupported C++ timing')
    watched = trace['units']
    require(isinstance(watched, list) and len(watched) == units, 'wrong unit count')
    for n, unit in enumerate(watched):
        keys(unit, ('name', 'type', 'speed', 'default_speed'))
        require(unit['name'] == f'u{n}' and isinstance(unit['type'], str) and unit['type'], 'invalid watch order/type')
        require(number(unit['speed']) > 0 and number(unit['default_speed']) > 0, 'invalid unit speed')
    time = trace['time']
    keys(time, ('unit', 'position_unit', 'facing_unit', 'numeric_format', 'clock_duration', 'step_us', 'observation_phase', 'state_lag_us'))
    require((time['unit'], time['position_unit'], time['facing_unit']) == ('seconds', 'world-units', 'degrees'), 'unsupported units')
    if retail:
        require(time == dict(unit='seconds', position_unit='world-units', facing_unit='degrees', numeric_format=retail_numeric_format(scenario['map_revision']), clock_duration='1000.000000', step_us=None, observation_phase='unknown-relative-to-due-update', state_lag_us=None), 'invalid WC3 time semantics')
    else:
        require(time['numeric_format'] == 'float-max_digits10' and time['clock_duration'] is None, 'invalid C++ precision/clock')
        require(time['observation_phase'] in (('scheduled-sampler-time',) if scheduled else ('after-due-update', 'before-due-update')), 'unsupported observation phase')
        lag = None if scheduled else 1000 if time['observation_phase'] == 'before-due-update' else 0
        require(time['step_us'] == build['step_us'] and time['state_lag_us'] == lag, 'invalid state lag')
        require(build['observation_phase'] == time['observation_phase'] and build['state_lag_us'] == time['state_lag_us'], 'build phase mismatch')
    records = trace['records']
    require(isinstance(records, list) and 1 <= len(records) <= 50000, 'invalid record count')
    current, sample_index, previous_time = -1, 0, -1
    begun, running, ended, watch_count = False, False, False, 0
    for seq, rec in enumerate(records):
        require(isinstance(rec, dict) and rec.get('kind') in KINDS, 'invalid record kind')
        integer(rec['seq'], 0, 50000)
        require(rec['seq'] == seq and not ended, 'sequence gap/record after END')
        kind = rec['kind']
        fields = {'seq', 'kind', 'source'}
        if kind in TIMED:
            fields |= {'callback', 'time'}
            integer(rec['callback'], 0, callbacks)
            cb = rec['callback']
            keys(rec['time'], ('requested', 'reported', 'state_us'))
            require(rec['time']['requested'] == requested(cb, period), 'invalid requested time')
            if retail:
                t = number(rec['time']['reported'])
                require(re.fullmatch(r'-?\d+\.\d{6}', rec['time']['reported']) and rec['time']['state_us'] is None, 'invalid observed time')
            else:
                # Only footman-v4 models the library clock; that is a prediction, not an observation.
                if model_clock:
                    t = number(rec['time']['reported'])
                else:
                    require(rec['time']['reported'] is None, 'C++ cannot claim observed WC3 time')
                    t = number(rec['time']['requested'])
                integer(rec['time']['state_us'], 0, 20000000)
                if scheduled:
                    # The latest 5 ms frame at or before the float32 scheduled time.
                    require(rec['time']['state_us'] == scheduled_frame_us(experiment['start_us'], period, cb),
                            'invalid C++ state timing')
                else:
                    lag = time['state_lag_us'] if cb > 0 and kind in ('TICK', 'SAMPLE') else 0
                    require(rec['time']['state_us'] == cb * 20000 - lag, 'invalid C++ state timing')
            if kind == 'TICK':
                require(running and cb == current + 1 and (current < 0 or sample_index == units), 'incomplete/reordered callback')
                # A delayed v2 start cannot hold its float32 start exactly, so callback 0's
                # library clock may read just above zero (docs/mov-0013.md).
                first_ok = t == 0 or (experiment and experiment['start_us'] and 0 <= t < number(period))
                require(t >= previous_time and (cb > 0 or first_ok), 'decreasing/nonzero initial time')
                current, sample_index, previous_time, tick_time = cb, 0, t, rec['time']
            else:
                require(running and cb == current, 'record outside callback')
                require(rec['time']['requested'] == tick_time['requested'] and rec['time']['reported'] == tick_time['reported'], 'time differs from TICK')
            if kind == 'SAMPLE':
                fields |= {'unit', 'values'}
                require(sample_index < units and rec['unit'] == f'u{sample_index}', 'sample unit/order mismatch')
                keys(rec['values'], ('x', 'y', 'facing', 'order'))
                for prop in ('x', 'y', 'facing'):
                    number(rec['values'][prop])
                    if retail:
                        require(re.fullmatch(r'-?\d+\.\d{6}', rec['values'][prop]), 'lost WC3 decimal precision')
                require(0 <= number(rec['values']['facing']) < 360, 'facing outside [0,360)')
                order(rec['values']['order'])
                require(rec['time']['state_us'] == tick_time['state_us'], 'sample state differs from TICK')
                sample_index += 1
            elif kind in ('ACTION', 'EVENT'):
                require(sample_index == units, 'action/event precedes samples')
                if kind == 'ACTION':
                    fields |= {'unit', 'command', 'accepted', 'target'}
                    require(rec['unit'] in [u['name'] for u in watched] and rec['command'] in ('move', 'stop'), 'invalid action unit/command')
                    require(type(rec['accepted']) is bool, 'invalid acceptance')
                    if rec['command'] == 'move':
                        keys(rec['target'], ('x', 'y'))
                        number(rec['target']['x']); number(rec['target']['y'])
                    else:
                        require(rec['target'] is None, 'immediate action has point target')
                else:
                    fields |= {'name', 'values'}
                    require(isinstance(rec['name'], str) and rec['name'] and isinstance(rec['values'], dict), 'invalid event')
                    for value in rec['values'].values():
                        number(value)
                    if experiment and experiment['state']:
                        require(rec['name'] == experiment['state'] and set(rec['values']) == STATE_KEYS, 'unregistered event')
                        if retail:
                            for value in rec['values'].values():
                                require(re.fullmatch(r'-?\d+\.\d{9}', value), 'lost STATE decimal precision')
                    elif rec['name'] == 'CLOCKS':
                        require(set(rec['values']) == {'c1000_9', 'c100', 'c100_9', 'c10', 'c10_9', 'c10_remaining_9', 'x_9', 'y_9', 'facing_9'}, 'incomplete CLOCKS event')
                        for key, value in rec['values'].items():
                            require(re.fullmatch(r'-?\d+\.\d{' + ('9' if key.endswith('_9') else '6') + '}', value), 'lost CLOCKS decimal precision')
        else:
            fields.add('fields')
            require(isinstance(rec['fields'], list) and all(isinstance(v, str) for v in rec['fields']), 'invalid control fields')
            if kind == 'BEGIN':
                require(seq == 0 and not begun, 'invalid BEGIN')
                begun = True
            elif kind == 'SETUP':
                require(begun and not running, 'SETUP after RUN')
            elif kind == 'WATCH':
                require(begun and not running, 'WATCH after RUN')
                watch_count += 1
            elif kind == 'RUN':
                require(begun and not running and watch_count == units, 'invalid RUN/WATCH count')
                running = True
            elif kind == 'END':
                require(running and current == callbacks and sample_index == units, 'incomplete END')
                ended = True
        keys(rec, fields)
        if retail:
            keys(rec['source'], ('seq', 'payload'))
            require(rec['source']['seq'] == seq and isinstance(rec['source']['payload'], str), 'invalid raw mapping')
            require(raw_record(rec['source']['payload'], period, current) == rec, 'canonical record differs from raw evidence')
        else:
            require(rec['source'] is None, 'unexpected C++ raw source')
    require(ended and current == callbacks, 'missing END/callbacks')
    require(trace['completion'] == counts(records) and trace['completion'].get('complete') is True, 'completion/count mismatch')
    for key, value in trace['completion'].items():
        if key != 'complete': integer(value, 0, 50000)
    require(isinstance(trace['provenance'], dict), 'missing provenance')
    if retail:
        # Identity in raw controls must agree with the canonical metadata.
        begin = records[0]['fields']
        require(begin == [exp, BUILD, f'map={scenario["map_revision"]}', 'lib=oracle-v1', 'time_unit=seconds', 'numeric_format=R2SW_6', 'clock_duration=1000.000000'], 'raw BEGIN identity mismatch')
        require(records[-1]['fields'] == [exp, f'map={scenario["map_revision"]}', f'callbacks={callbacks}'], 'raw END mismatch')
        run = next(r for r in records if r['kind'] == 'RUN')
        require(run['fields'] == [f'requested_period={period}', f'callbacks={callbacks}'], 'raw RUN shape mismatch')
        raw_watches = [r['fields'] for r in records if r['kind'] == 'WATCH']
        require(raw_watches == [[u['name'], f'type={u["type"]}', f'speed={u["speed"]}', f'default_speed={u["default_speed"]}'] for u in watched], 'raw WATCH mismatch')
        prov = trace['provenance']
        require('manifest' in prov and 'runs' in prov and 'repeatability' in prov, 'missing WC3 provenance')
        run_count = len(manifest['runs']) if evidence_root != ROOT else 3
        require(run_count >= 3 and isinstance(prov['runs'], list) and len(prov['runs']) == run_count, 'missing retained run provenance')
        raw_hash = hashlib.sha256('\n'.join(r['source']['payload'] for r in records).encode('ascii')).hexdigest()
        require([r['run'] for r in prov['runs']] == list(range(1, run_count + 1)), 'duplicate/missing run identity')
        require(prov['manifest']['path'] == f'oracle/captures/{BUILD}/{scenario["map_revision"]}/manifest.json'
                and HASH.fullmatch(prov['manifest']['sha256']), 'invalid manifest provenance')
        require(prov['representative_run'] == 1, 'invalid representative run')
        for run in prov['runs']:
            require(run['payload_sha256'] == raw_hash and HASH.fullmatch(run['sha256']), 'raw payload/hash mismatch')
            require(run['path'] == f'oracle/captures/{BUILD}/{scenario["map_revision"]}/run-{run["run"]:02d}.txt', 'invalid run path')
            require(run['fresh_game_process'] is True and run['previous_output_removed'] is True, 'invalid run procedure')
            require(isinstance(run['footer'], str) and re.fullmatch(r'call PreloadEnd\( \d+\.\d+ \)', run['footer']), 'invalid transport footer')
            require(isinstance(run['generated_preload_entries'], list), 'missing transport entries')
            for entry in run['generated_preload_entries']:
                keys(entry, ('after_record', 'entry'))
                integer(entry['after_record'], -1, len(records)-1)
                require(isinstance(entry['entry'], str), 'invalid transport entry')
        repeatability = prov['repeatability']
        require(repeatability['classification'] == 'DETERMINISTIC' and repeatability['runs'] == run_count
                and repeatability['canonical_payload_sha256'] == [digest(payload(trace))]*run_count
                and repeatability['observation_payload_sha256'] == [raw_hash]*run_count
                and repeatability['other_seeds_or_machines'] == 'UNKNOWN', 'invalid scoped repeatability evidence')
    return trace

#!/usr/bin/env python3
"""Install/update this project's two BB script automations without global changes."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from dispatch import CLI, ControlError, LABEL, ROOT, atomic_json, require, validate_config


def launcher(script, config):
    # BB saves a private copy of this launcher. The controller implementation is
    # snapshotted separately, so a worker/manual checkout edit cannot alter it.
    return ('import subprocess, sys\n'
            f'result = subprocess.run([sys.executable, {str(script)!r}, "--config", {str(config)!r}])\n'
            'if result.returncode:\n'
            '    print("Controller needs attention: process exited", result.returncode, file=sys.stderr)\n'
            '# Keep recurring ticks alive through errors; health records remain visible.\n')


def automation_id(result):
    return result.get('id') or result.get('automation', {}).get('id')


def install(config, cli):
    validate_config(config)
    root = Path(config['state_dir'])
    config_file = root / 'config.json'
    record = root / 'automations.json'
    runtime = root / 'runtime'
    # Disabled installation is safe even before the bootstrap is published.
    # Activation requires the worker's base branch to include the instructions.
    if config['enabled']:
        cli.git(config['checkout'], 'fetch', 'origin', config['base_branch'])
        for path in ('AGENTS.md', 'CLAUDE.md', 'docs/next-roadmap.md', 'docs/continuous-development.md'):
            require(cli.git(config['checkout'], 'show', f"origin/{config['base_branch']}:{path}") ==
                    (ROOT / path).read_text().strip(),
                    'publish the bootstrap instructions on the base branch before activation')
    labels = json.loads(cli.gh('label', 'list', '--repo', config['repository'], '--limit', '100',
                              '--json', 'name', json_output=False))
    if LABEL not in {label['name'] for label in labels}:
        cli.gh('label', 'create', LABEL, '--repo', config['repository'], '--color', '2E7D32',
               '--description', 'Eligible for the project-scoped continuous dispatcher', json_output=False)
    root.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(exist_ok=True)
    for name in ('dispatch.py', 'dispatch_health.py'):
        temporary = runtime / (name + '.tmp')
        shutil.copyfile(ROOT / 'tools' / name, temporary)
        temporary.replace(runtime / name)
    atomic_json(config_file, config)
    previous = json.loads(record.read_text()) if record.exists() else {}
    known = cli.bb('automation', 'list', '--project', config['project'])
    known_ids = {a['id'] for a in known if a['projectId'] == config['project']}
    ids = {}
    for role, name, cron, script, args in (
        ('controller', 'Warcraft continuous development', '* * * * *', 'dispatch.py', ['tick']),
        ('health', 'Warcraft dispatcher health', '*/5 * * * *', 'dispatch_health.py', [])):
        executable = runtime / script
        wrapper = root / f'{role}-launcher.py'
        content = launcher(executable, config_file)
        if args:
            content = content.replace('"--config",', '"tick", "--config",')
        wrapper.write_text(content, encoding='utf-8')
        wrapper.chmod(0o600)
        common = ['--project', config['project'], '--script-file', str(wrapper),
                  '--host', config['machine'], '--interpreter', 'python3', '--timeout', '90s',
                  '--working-directory', config['checkout']]
        ident = previous.get(role)
        if ident:
            require(ident in known_ids, 'saved automation missing/wrong project; inspect before reinstall')
            result = cli.bb('automation', 'update', ident, *common)
            ids[role] = ident
        else:
            require(not any(a['name'] == name for a in known),
                    'automation name exists without saved identity; inspect before adopting it')
            result = cli.bb('automation', 'create', '--name', name, '--cron', cron,
                            '--timezone', 'Europe/Bucharest', '--disabled', *common)
            ids[role] = automation_id(result)
            require(ids[role], 'automation creation returned no ID')
        atomic_json(record, dict(previous, **ids))  # Save after EACH creation.
    for ident in ids.values():
        cli.bb('automation', 'resume' if config['enabled'] else 'pause', ident,
               '--project', config['project'])
    return ids


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--providers', nargs=2, choices=['claude-code', 'codex', 'acp-cursor'], required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--auto-merge', action='store_true')
    parser.add_argument('--max-workers', type=int, default=2)
    args = parser.parse_args(argv)
    cli = CLI(str(ROOT))
    context = cli.bb('status')
    require(context.get('project') and context.get('thread'), 'run installer from this BB project thread')
    show = cli.bb('thread', 'show', context['thread']['id'])
    environment = show['environment']
    require(Path(environment['path']).resolve() == ROOT and not environment['isWorktree'],
            'install from the server-host project checkout, not a worker worktree')
    require(args.state_dir.is_absolute(), 'state directory must be absolute')
    config = {'project': context['project']['id'], 'machine': environment['hostId'],
              'repository': 'galitianu/warcraft-re', 'checkout': str(ROOT),
              'state_dir': str(args.state_dir), 'providers': args.providers,
              'enabled': args.activate, 'auto_merge': args.auto_merge,
              'max_workers': args.max_workers, 'threshold_percent': 80, 'base_branch': 'main'}
    ids = install(config, cli)
    print(json.dumps({'automations': ids, 'enabled': config['enabled'],
                      'config': str(args.state_dir / 'config.json')}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ControlError, OSError, ValueError, KeyError, TypeError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        sys.exit(2)

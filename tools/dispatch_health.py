#!/usr/bin/env python3
"""Observe/resume only this controller's schedule; never start model work directly."""
import argparse
import json
from pathlib import Path
import sys
import time

from dispatch import CLI, ControlError, require


def health(config, cli, now=None):
    now = time.time() if now is None else now
    if not config['enabled']:
        return []  # Explicit pause is authoritative.
    root = Path(config['state_dir'])
    ids = json.loads((root / 'automations.json').read_text())
    result = cli.bb('automation', 'show', ids['controller'], '--project', config['project'])
    require(result['id'] == ids['controller'] and result['projectId'] == config['project'],
            'health target identity changed')
    messages = []
    if not result['enabled']:
        cli.bb('automation', 'resume', result['id'], '--project', config['project'])
        messages.append('Resumed this project’s unexpectedly paused controller.')
    state_file = root / 'state.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    if now - state.get('last_tick_at', 0) > 300:
        messages.append('Controller heartbeat is stale; inspect its recorded automation output.')
    if state.get('last_error'):
        messages.append('Controller recorded an error: ' + state['last_error']['message'])
    for job in state.get('jobs', {}).values():
        if job['state'] == 'blocked':
            messages.append(f"Issue #{job['issue']} parked: " + '; '.join(job.get('findings', [])))
    if state.get('planning_blocked'):
        messages.append('Planning needs a decision: ' + state['planning_blocked'])
    for number, error in state.get('queue_errors', {}).items():
        messages.append(f'Issue #{number} needs queue metadata repair: {error}')
    # Print changes only, so healthy ticks and repeated obstacles remain quiet.
    health_file = root / 'health.json'
    previous = json.loads(health_file.read_text()) if health_file.exists() else {}
    from dispatch import atomic_json
    atomic_json(health_file, {'observed_at': now, 'messages': messages})
    return messages if messages != previous.get('messages', []) else []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text())
        for message in health(config, CLI(config['checkout'])):
            print(message)
    except (ControlError, OSError, ValueError, KeyError, TypeError) as error:
        print(f'Dispatcher health waiting: {error}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

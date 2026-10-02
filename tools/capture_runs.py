#!/usr/bin/env python3
"""Capture fresh-process WC3 runs of one committed oracle map through rdpipe.

For each run: stop the game started by the previous run, delete the old output and
confirm it is gone, launch WC3 with -loadfile, wait for a new complete output file,
pull it unchanged to run-NN.txt and parse it. Run from the repository root.
The map must already be in Maps\\Oracle on Windows with the committed bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import oracle_parse

HOME = "C:\\Users\\rdpipe\\Documents\\Warcraft III"
GAME = "C:\\Program Files (x86)\\Warcraft III"


def ps(script, timeout=60):
    result = subprocess.run(["rdpipe", "ps", '$ErrorActionPreference="Stop"; ' + script],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"rdpipe ps failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def capture(driver, label, local_map, root, runs=3, deadline=120):
    """Fresh processes and hash-verified raw retrieval; the driver owns cleanup."""
    map_sha = hashlib.sha256(local_map.read_bytes()).hexdigest()
    remote_map = f"{HOME}\\Maps\\Oracle\\{label}.w3m"
    output = f"{HOME}\\CustomMapData\\{label}.txt"
    log = []
    for number in range(1, runs + 1):
        driver.stage(f'capture-{number:02}')
        driver.assert_hash(remote_map, map_sha)
        target = root / f"run-{number:02}.txt"
        if target.exists():
            raise ValueError('capture exists; never overwrite evidence')
        driver.ps(f'if (Test-Path -LiteralPath "{output}") {{ Remove-Item -LiteralPath "{output}" }}; '
                  f'if (Test-Path -LiteralPath "{output}") {{ throw "stale output remains" }}')
        started = time.time()
        pid = driver.launch(GAME, 'Warcraft III.exe', remote_map, f'game-{number}')
        end = time.monotonic() + deadline
        try:
            while True:
                driver.pause(min(2, max(0, end - time.monotonic())))
                state = driver.ps(f'$p="{output}"; if (Test-Path -LiteralPath $p) {{ $t=Get-Content -Raw -LiteralPath $p; '
                                  'if ($t.Contains("|END|") -and $t.Contains("call PreloadEnd(" ) '
                                  '-and $t.TrimEnd().EndsWith("endfunction")) '
                                  '{ Get-Item -LiteralPath $p | Select-Object Length,LastWriteTimeUtc | ConvertTo-Json } }',
                                  timeout=max(.1, min(15, end - time.monotonic())))
                if state:
                    break
                if time.monotonic() >= end:
                    raise RuntimeError(f'run {number}: stale/absent/incomplete output; no END + transport footer within {deadline}s')
            driver.pull(output, target)
            report = oracle_parse.parse(target, map_label=label)
            log.append(dict(run=number, file=target.name, game_pid=pid, start_unix_seconds=started,
                            fresh_game_process=True, previous_output_removed=True,
                            launch=f'WC3 -loadfile {label}.w3m', map_sha256=map_sha,
                            output=json.loads(state), sha256=report['sha256'], payload_sha256=report['payload_sha256'],
                            footer=report['footer']))
            (root / 'runs.json').write_text(json.dumps(log, indent=2) + '\n')
            print(f'{label} run {number}: {report["records"]} records, {report["payload_sha256"][:12]}', flush=True)
        finally:
            # Retain incomplete output as a rejected attempt, never as a fresh run.
            if not target.exists():
                try:
                    if driver.ps(f'Test-Path -LiteralPath "{output}"') == 'True':
                        driver.pull(output, root / f'attempt-{number:02}.txt')
                except Exception as error:
                    driver.note('partial-output-retrieval', str(error))
            driver.stop(pid)
    return log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", help="map label, e.g. MOV-0001")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--first", type=int, default=1, help="number of the first run file")
    parser.add_argument("--deadline", type=float, default=120, help="seconds to wait per run")
    args = parser.parse_args()
    local_map = Path("oracle-maps") / f"{args.label}.w3m"
    map_sha = hashlib.sha256(local_map.read_bytes()).hexdigest().upper()
    remote_map = f"{HOME}\\Maps\\Oracle\\{args.label}.w3m"
    output = f"{HOME}\\CustomMapData\\{args.label}.txt"
    if ps(f'(Get-FileHash -LiteralPath "{remote_map}").Hash') != map_sha:
        raise SystemExit(f"remote map differs from {local_map}")
    root = Path("oracle/captures/wc3-1.29.2-9231-x86") / args.label
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / "runs.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else []
    pid = None
    try:
        for number in range(args.first, args.first + args.runs):
            target = root / f"run-{number:02}.txt"
            if target.exists():
                raise SystemExit(f"{target} exists; refusing to overwrite a retained capture")
            if pid:
                ps(f"Stop-Process -Id {pid}; Wait-Process -Id {pid} -Timeout 20")
            ps(f'if (Test-Path -LiteralPath "{output}") {{ Remove-Item -LiteralPath "{output}" }}; '
               f'if (Test-Path -LiteralPath "{output}") {{ throw "old output remains" }}')
            started = time.time()
            pid = json.loads(ps(
                f'Start-Process -FilePath "{GAME}\\Warcraft III.exe" -WorkingDirectory "{GAME}" '
                f'-ArgumentList @("-loadfile", "`"{remote_map}`"") -PassThru | Select-Object Id | ConvertTo-Json'))["Id"]
            deadline = time.monotonic() + args.deadline
            while True:
                time.sleep(2)
                state = ps(f'$p="{output}"; if (Test-Path -LiteralPath $p) {{ $t = Get-Content -Raw -LiteralPath $p; '
                           f'if ($t.Contains("|END|") -and $t.TrimEnd().EndsWith("endfunction")) '
                           f'{{ Get-Item -LiteralPath $p | Select-Object Length,LastWriteTimeUtc | ConvertTo-Json }} }}')
                if state:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError(f"run {number}: no complete output within {args.deadline} s")
            subprocess.run(["rdpipe", "pull", output, str(target)], capture_output=True, text=True,
                           check=True, timeout=60)
            report = oracle_parse.parse(target, map_label=args.label)
            log.append({"run": number, "file": target.name, "game_pid": pid, "start_unix_seconds": started,
                        "fresh_game_process": True, "previous_output_removed": True,
                        "launch": f"WC3 -loadfile {args.label}.w3m", "map_sha256": map_sha.lower(),
                        "output": json.loads(state), "sha256": report["sha256"],
                        "payload_sha256": report["payload_sha256"], "footer": report["footer"]})
            log_path.write_text(json.dumps(log, indent=2) + "\n")
            print(f"{args.label} run {number:02}: {report['records']} records, "
                  f"payload {report['payload_sha256'][:12]}, {report['footer']}", flush=True)
    finally:
        if pid:
            ps(f"Stop-Process -Id {pid} -ErrorAction SilentlyContinue")


if __name__ == "__main__":
    raise SystemExit(main())

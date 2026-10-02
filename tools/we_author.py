#!/usr/bin/env python3
"""Drive the manual World Editor steps for one Phase 1 map through rdpipe.

This only repeats the documented GUI procedure: copy the Phase 0 map to a new name,
open it in World Editor, paste library + case into the Melee Initialization custom
text, save, close. It does not write map files itself. Afterwards the saved map is
pulled to oracle-maps/ and must pass tools/check_map.py. Run from the repository root
with RDPIPE_HOLDER set and the desktop lease held. Coordinates are Trigger Editor
screenshot pixels at 1920x1080, 96 dpi; the screenshot is saved for inspection.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

MAPS = "C:\\Users\\rdpipe\\Documents\\Warcraft III\\Maps\\Oracle"
EDITOR = "C:\\Program Files (x86)\\Warcraft III"
MENU = "C:\\Users\\rdpipe\\editor-menu.ps1"  # tools/editor-menu.ps1, pushed with --to C:\Users\rdpipe
TRIGGER_ITEM, TEXT_AREA = (90, 106), (800, 500)


def clipboard_text(library, case):
    text = library + b"\n" + case
    if b'\r' in text or not text.endswith(b'\n'):
        raise ValueError('authored source must be LF-only with a final newline')
    return text.decode('ascii').replace('\n', '\r\n')


def rdpipe(*args, stdin=None):
    result = subprocess.run(["rdpipe", *args], input=stdin, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"rdpipe {args[:2]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def ps(script):
    return rdpipe("ps", '$ErrorActionPreference="Stop"; ' + script).strip()


def author(driver, label, case, destination, remote_base, menu=MENU):
    """Repeat the proven editor route using a leased, bounded transport.

    driver supplies ps/ui/rdpipe, owns process cleanup, and retains snapshots.
    """
    text = clipboard_text(Path("oracle/jass/lib/oracle-v1.j").read_bytes(), case.read_bytes())
    new = f"{MAPS}\\{label}.w3m"
    driver.ps(f'if (Test-Path -LiteralPath "{new}") {{ throw "map exists; use a new revision" }}; '
              f'Copy-Item -LiteralPath "{remote_base}" -Destination "{new}"')
    pid = driver.launch(EDITOR, "World Editor.exe", new, "editor")

    def current():
        result = driver.ui("list_windows")
        return {w['title']: w['window_id'] for w in result['structuredContent']['windows'] if w['pid'] == pid}

    def wait(predicate, what, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            found = current()
            for title, wid in found.items():
                if predicate(title):
                    return title, wid
            driver.pause(1)
        raise RuntimeError(f"timed out waiting for {what}; windows: {found}")

    def snapshot(wid):
        driver.ui("get_window_state", pid=pid, window_id=wid, include_accessibility_tree=False)

    is_map = lambda t: t.startswith("Warcraft III World Editor - [") and label in t
    _, main_window = wait(is_map, "map window", 90)
    snapshot(main_window)
    driver.ui("hotkey", pid=pid, window_id=main_window, keys=["f4"], delivery_mode="foreground")
    _, trig = wait(lambda t: t == "Trigger Editor", "Trigger Editor")
    target = {"pid": pid, "window_id": trig}
    driver.pause(2)
    snapshot(trig)
    driver.ui("bring_to_front", **target)
    snapshot(trig)
    driver.ui("click", **target, x=TRIGGER_ITEM[0], y=TRIGGER_ITEM[1], delivery_mode="foreground")
    driver.pause(1)
    snapshot(trig)
    driver.ui("clipboard_write", text=text)
    driver.ui("click", **target, x=TEXT_AREA[0], y=TEXT_AREA[1], delivery_mode="foreground")
    snapshot(trig)
    driver.ui("hotkey", **target, keys=["ctrl", "a"], delivery_mode="foreground")
    snapshot(trig)
    driver.ui("hotkey", **target, keys=["ctrl", "v"], delivery_mode="foreground")
    driver.pause(1)
    snapshot(trig)
    driver.rdpipe("exec", "--", "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                  "-File", menu, "-Window", str(trig), "-Command", "4")
    title, dialog = wait(lambda t: t not in ("Tool Palette", "Trigger Editor") and "World Editor -" not in t,
                         "save dialog")
    snapshot(dialog)
    if title != "Reminder":
        raise RuntimeError(f"unexpected save dialog {title!r}; see retained UI state")
    driver.ui("hotkey", pid=pid, window_id=dialog, keys=["enter"], delivery_mode="foreground")
    _, saved = wait(lambda t: is_map(t) and not t.endswith("*]"), "saved title without *")
    snapshot(saved)
    driver.stop(pid)
    driver.pause(2)
    driver.pull(new, destination)
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--base", default="MOV-0002")
    parser.add_argument("--case", type=Path)
    args = parser.parse_args()
    # The unattended command owns leases and integrity. Keep this legacy/manual
    # entry point for the existing documented workflow.
    if not all(re.fullmatch(r'[A-Z]{2,5}-\d{4}(?:-[a-z0-9]+)*', label) for label in (args.label, args.base)):
        parser.error('invalid map label')
    destination = Path('oracle-maps') / f'{args.label}.w3m'
    if destination.exists():
        parser.error('local map exists; never overwrite a retained revision')
    class Manual:
        owned = []
        def rdpipe(self, *args): return rdpipe(*args)
        def ps(self, script): return ps(script)
        def ui(self, tool, **arguments): return json.loads(rdpipe('--json', 'ui', tool, '-', stdin=json.dumps(arguments)))
        def pause(self, seconds): time.sleep(seconds)
        def launch(self, directory, exe, path, role):
            pid = int(ps(f'(Start-Process -FilePath "{directory}\\{exe}" -WorkingDirectory "{directory}" '
                         f'-ArgumentList @("-loadfile", "`"{path}`"") -PassThru).Id'))
            self.owned.append(pid)
            return pid
        def stop(self, pid):
            ps(f"Stop-Process -Id {pid} -ErrorAction SilentlyContinue")
            self.owned.remove(pid)
        def pull(self, remote, local): rdpipe('pull', remote, str(local))
    driver = Manual()
    try:
        author(driver, args.label, args.case or Path('oracle/jass') / f'{args.label}.j', destination,
               f'{MAPS}\\{args.base}.w3m')
    finally:
        for pid in driver.owned[:]: driver.stop(pid)


if __name__ == "__main__":
    raise SystemExit(main())

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


def rdpipe(*args, stdin=None):
    result = subprocess.run(["rdpipe", *args], input=stdin, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"rdpipe {args[:2]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def ps(script):
    return rdpipe("ps", '$ErrorActionPreference="Stop"; ' + script).strip()


def ui(tool, **arguments):
    return rdpipe("ui", tool, json.dumps(arguments))


def windows(pid):
    found = re.findall(r'\(pid (\d+)\) "([^"]*)" \[window_id: (\d+)\]', ui("list_windows"))
    return {title: int(wid) for p, title, wid in found if int(p) == pid}


def wait_window(pid, predicate, what, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for title, wid in windows(pid).items():
            if predicate(title):
                return title, wid
        time.sleep(1)
    raise RuntimeError(f"timed out waiting for {what}; windows: {windows(pid)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--base", default="MOV-0002", help="World Editor map copied as the start")
    args = parser.parse_args()
    case = Path("oracle/jass") / f"{args.label}.j"
    text = Path("oracle/jass/lib/oracle-v1.j").read_text() + "\n" + case.read_text()
    new = f"{MAPS}\\{args.label}.w3m"
    pid = int(ps(f'if (Test-Path -LiteralPath "{new}") {{ throw "map exists" }}; '
                 f'Copy-Item -LiteralPath "{MAPS}\\{args.base}.w3m" -Destination "{new}"; '
                 f'(Start-Process -FilePath "{EDITOR}\\World Editor.exe" -WorkingDirectory "{EDITOR}" '
                 f'-ArgumentList @("-loadfile", "`"{new}`"") -PassThru).Id'))
    try:
        # Long titles are truncated (e.g. ".../JASS-0001-p020.w3]"); unsaved ones end in " *]".
        is_map = lambda t: t.startswith("Warcraft III World Editor - [") and args.label in t
        _, main_window = wait_window(pid, is_map, "map window", 90)
        ui("hotkey", pid=pid, window_id=main_window, keys=["f4"])
        _, trig = wait_window(pid, lambda t: t == "Trigger Editor", "Trigger Editor")
        target = {"pid": pid, "window_id": trig}
        time.sleep(2)
        # Clicks are mapped through this window's latest screenshot scale; without a
        # screenshot first they land ~12% up-left (on the category row).
        ui("get_window_state", **target, include_accessibility_tree=False)
        ui("bring_to_front", **target)
        ui("click", **target, x=TRIGGER_ITEM[0], y=TRIGGER_ITEM[1], delivery_mode="foreground")
        time.sleep(1)
        rdpipe("ui", "clipboard_write", "-", stdin=json.dumps({"text": text.replace("\n", "\r\n")}))
        ui("click", **target, x=TEXT_AREA[0], y=TEXT_AREA[1], delivery_mode="foreground")
        ui("hotkey", **target, keys=["ctrl", "a"], delivery_mode="foreground")
        ui("hotkey", **target, keys=["ctrl", "v"], delivery_mode="foreground")
        time.sleep(1)
        shot = re.search(r"image: (\S+)", ui("get_window_state", **target, include_accessibility_tree=False))
        print("trigger screenshot:", shot[1] if shot else "none")
        rdpipe("exec", "--", "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", MENU, "-Window", str(trig), "-Command", "4")  # Save Map
        # Expected dialog: the default-map-name Reminder. Anything else stops the run.
        title, dialog = wait_window(pid, lambda t: t not in ("Tool Palette", "Trigger Editor")
                                    and "World Editor -" not in t, "save dialog")
        if title != "Reminder":
            raise RuntimeError(f"unexpected dialog {title!r}; inspect it before continuing")
        ui("hotkey", pid=pid, window_id=dialog, keys=["enter"])
        wait_window(pid, lambda t: is_map(t) and not t.endswith("*]"), "saved title without *")
        print(ps(f'(Get-FileHash -LiteralPath "{new}").Hash'))
    finally:
        ps(f"Stop-Process -Id {pid} -ErrorAction SilentlyContinue")
    time.sleep(2)
    rdpipe("pull", new, f"oracle-maps/{args.label}.w3m")


if __name__ == "__main__":
    raise SystemExit(main())

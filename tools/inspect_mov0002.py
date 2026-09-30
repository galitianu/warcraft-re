#!/usr/bin/env python3
"""Inspect Phase 0's raw PreloadGen capture without executing or normalizing it."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

BEGIN = "@O|0|BEGIN|MOV-0002|wc3-1.29.2-9231-x86|time_unit=seconds|numeric_format=R2SW_6"
SETUP = "@O|1|SETUP|u0=hfoo,0,0,0|u1=hfoo,0,384,0|target=1000,0|requested_period=0.02|intervals=250|speed=270.000000"
ACTION = "@O|4|ACTION|0.000000|u0|move|1000|0|accepted=1"
END = "@O|505|END|MOV-0002|callbacks=250"
NUMBER = re.compile(r"-?\d+\.\d{6}")


def inspect(path):
    raw = Path(path).read_bytes()
    lines = [line.strip() for line in raw.decode("ascii").splitlines() if line.strip()]
    if len(lines) != 509 or lines[0] != "function PreloadFiles takes nothing returns nothing" or lines[-1] != "endfunction":
        raise ValueError("missing/extra content or incomplete PreloadFiles envelope")
    if not re.fullmatch(r"call PreloadEnd\( \d+\.\d+ \)", lines[-2]):
        raise ValueError("missing PreloadEnd footer")
    records = []
    for line in lines[1:-2]:
        match = re.fullmatch(r'call Preload\( "(@O\|[^"\r\n]+)" \)', line)
        if not match:
            raise ValueError("unrecognized record envelope")
        records.append(match[1])
    if len(records) != 506:
        raise ValueError("expected 506 records")
    for seq, record in enumerate(records):
        if record.split("|", 2)[:2] != ["@O", str(seq)]:
            raise ValueError(f"sequence discontinuity at record {seq}")
    if records[0] != BEGIN or records[1] != SETUP or records[4] != ACTION or records[-1] != END:
        raise ValueError("wrong experiment/build/setup, rejected order, or missing completion")
    samples = {"u0": [], "u1": []}
    for record in records[2:-1]:
        fields = record.split("|")
        if record == ACTION:
            continue
        if len(fields) != 9 or fields[2] != "SAMPLE" or fields[4] not in samples:
            raise ValueError("unexpected sample shape or unit")
        if not all(NUMBER.fullmatch(fields[i]) for i in [3, 5, 6, 7]) or not fields[8].isdigit():
            raise ValueError("invalid sample number")
        if not Decimal(0) <= Decimal(fields[7]) < Decimal(360):
            raise ValueError("facing outside [0,360)")
        samples[fields[4]].append(fields)
    for name, rows in samples.items():
        if len(rows) != 251 or Decimal(rows[0][3]) != 0:
            raise ValueError(f"incomplete samples for {name}")
        if any(Decimal(b[3]) <= Decimal(a[3]) for a, b in zip(rows, rows[1:])):
            raise ValueError(f"non-increasing time for {name}")
    for index, (a, b) in enumerate(zip(samples["u0"], samples["u1"])):
        if a[3] != b[3] or int(b[1]) != int(a[1]) + 1:
            raise ValueError(f"unpaired observations at sample {index}")
    times = [Decimal(row[3]) for row in samples["u0"]]
    intervals = sorted({str(b - a) for a, b in zip(times, times[1:])})
    final = samples["u0"][-1]
    return {
        "file": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
        "records": len(records), "samples_per_unit": 251,
        "elapsed_seconds": str(times[-1]), "observed_callback_intervals_seconds": intervals,
        "control_unchanged": all(row[5:] == ["0.000000", "384.000000", "0.000000", "0"] for row in samples["u1"]),
        "moving_final": dict(zip(["x", "y", "facing", "order"], final[5:])),
        "payload_sha256": hashlib.sha256("\n".join(records).encode("ascii")).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        reports = [inspect(path) for path in args.captures]
    except (OSError, UnicodeError, ValueError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"captures": reports,
                      "all_payloads_identical": len({r["payload_sha256"] for r in reports}) == 1}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

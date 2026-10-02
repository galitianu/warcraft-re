#!/usr/bin/env python3
"""Parse oracle-v1 PreloadGen captures into CSV, without executing or normalizing them.

Values are kept as the exact strings WC3 emitted. Rows keep capture sequence order,
including callbacks whose clock readings coincide; nothing is sorted by time.
Phase 3 normalization reuses these validated records; this parser does not read
the simulation or grade gameplay.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

BUILD = "wc3-1.29.2-9231-x86"
REAL6 = re.compile(r"-?\d+\.\d{6}")
REAL9 = re.compile(r"-?\d+\.\d{9}")
PRELOAD = re.compile(r'call Preload\( "([^"\r\n]*)" \)')
FOOTER = re.compile(r"call PreloadEnd\( \d+\.\d+ \)")
KINDS = {"BEGIN", "SETUP", "WATCH", "RUN", "TICK", "SAMPLE", "ACTION", "EVENT", "END"}


class Invalid(ValueError):
    pass


def real(value, what):
    if not REAL6.fullmatch(value):
        raise Invalid(f"{what}: not a 6-decimal real: {value!r}")
    return value


def pairs(fields, what):
    result = {}
    for field in fields:
        key, sep, value = field.partition("=")
        if not sep or not key or key in result:
            raise Invalid(f"{what}: malformed key=value field {field!r}")
        result[key] = value
    return result


def parse(path, build=BUILD, experiment=None, map_label=None):
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise Invalid(f"non-ASCII content: {error}") from None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 4 or lines[0] != "function PreloadFiles takes nothing returns nothing":
        raise Invalid("missing PreloadFiles header")
    if lines[-1] != "endfunction" or not FOOTER.fullmatch(lines[-2]):
        raise Invalid("incomplete PreloadFiles envelope (missing PreloadEnd/endfunction)")
    # WC3 also records files it loads after PreloadGenStart (e.g. unit models).
    # Those generated entries are kept separately and excluded from the payload.
    records, generated = [], []
    for line in lines[1:-2]:
        match = PRELOAD.fullmatch(line)
        if not match:
            raise Invalid(f"unrecognized line: {line[:80]!r}")
        if match[1].startswith("@O|"):
            records.append(match[1])
        elif match[1].startswith("@"):
            raise Invalid(f"malformed record: {match[1][:40]!r}")
        else:
            generated.append({"after_record": len(records) - 1, "entry": match[1]})

    fields_by_seq = []
    for seq, record in enumerate(records):
        fields = record.split("|")
        if fields[0] != "@O" or fields[1] != str(seq):
            raise Invalid(f"sequence discontinuity at record {seq}: {record[:40]!r}")
        if len(fields) < 3 or fields[2] not in KINDS:
            raise Invalid(f"record {seq}: unknown kind")
        fields_by_seq.append(fields[2:])

    if not fields_by_seq:
        raise Invalid("missing BEGIN")
    begin = fields_by_seq[0]
    if begin[0] != "BEGIN" or len(begin) != 8:
        raise Invalid("first record is not a well-formed BEGIN")
    meta = pairs(begin[3:], "BEGIN")
    if begin[2] != build:
        raise Invalid(f"wrong build {begin[2]!r}, expected {build!r}")
    if experiment and begin[1] != experiment:
        raise Invalid(f"wrong experiment {begin[1]!r}, expected {experiment!r}")
    if map_label and meta.get("map") != map_label:
        raise Invalid(f"wrong map {meta.get('map')!r}, expected {map_label!r}")
    if meta.get("lib") != "oracle-v1" or meta.get("time_unit") != "seconds" or meta.get("numeric_format") != "R2SW_6":
        raise Invalid("unexpected library/time unit/numeric format")
    real(meta.get("clock_duration", ""), "BEGIN clock_duration")

    watched, setup, run = [], [], None
    ticks, samples, events = [], [], []
    current = None  # (callback, t, index of next expected SAMPLE unit)
    end = None
    for seq, fields in enumerate(fields_by_seq[1:], start=1):
        kind = fields[0]
        if end is not None:
            raise Invalid(f"record {seq} after END")
        if kind == "BEGIN":
            raise Invalid(f"record {seq}: repeated BEGIN")
        if kind in ("SETUP", "WATCH") and (run or ticks):
            raise Invalid(f"record {seq}: {kind} after RUN")
        if kind == "SETUP":
            setup.append("|".join(fields[1:]))
        elif kind == "WATCH":
            if len(fields) != 5:
                raise Invalid(f"record {seq}: malformed WATCH")
            info = pairs(fields[2:], "WATCH")
            if set(info) != {"type", "speed", "default_speed"} or fields[1] in [w["name"] for w in watched]:
                raise Invalid(f"record {seq}: malformed or duplicate WATCH")
            real(info["speed"], "WATCH speed")
            real(info["default_speed"], "WATCH default_speed")
            watched.append({"name": fields[1], **info})
        elif kind == "RUN":
            if run or len(fields) != 3 or not watched:
                raise Invalid(f"record {seq}: malformed/repeated RUN or no watched units")
            run = pairs(fields[1:], "RUN")
            real(run.get("requested_period", ""), "RUN requested_period")
            if not run.get("callbacks", "").isdigit():
                raise Invalid("RUN callbacks is not an integer")
        elif kind == "TICK":
            if not run or len(fields) != 3:
                raise Invalid(f"record {seq}: malformed TICK or TICK before RUN")
            if current and current[2] != len(watched):
                raise Invalid(f"record {seq}: callback {current[0]} has missing SAMPLE records")
            t, n = real(fields[1], "TICK time"), fields[2]
            if n != str(len(ticks)):
                raise Invalid(f"record {seq}: callback discontinuity, got {n}, expected {len(ticks)}")
            if ticks and Decimal(t) < Decimal(ticks[-1]["t"]):
                raise Invalid(f"record {seq}: clock reading decreased")
            ticks.append({"seq": seq, "callback": int(n), "t": t})
            current = (int(n), t, 0)
        elif kind == "SAMPLE":
            if not current or len(fields) != 7:
                raise Invalid(f"record {seq}: malformed SAMPLE or SAMPLE outside a callback")
            callback, t, index = current
            if index >= len(watched) or fields[2] != watched[index]["name"]:
                raise Invalid(f"record {seq}: unexpected SAMPLE unit/order {fields[2]!r}")
            if fields[1] != t:
                raise Invalid(f"record {seq}: SAMPLE time differs from its TICK")
            x, y, facing = (real(fields[i], "SAMPLE value") for i in (3, 4, 5))
            if not Decimal(0) <= Decimal(facing) < Decimal(360):
                raise Invalid(f"record {seq}: facing outside [0,360)")
            if not fields[6].isdigit():
                raise Invalid(f"record {seq}: order is not a non-negative integer")
            samples.append({"seq": seq, "callback": callback, "t": t, "unit": fields[2],
                            "x": x, "y": y, "facing": facing, "order": fields[6]})
            current = (callback, t, index + 1)
        elif kind in ("ACTION", "EVENT"):
            if not current or current[2] != len(watched) or len(fields) < 3:
                raise Invalid(f"record {seq}: {kind} outside a sampled callback")
            if fields[1] != current[1]:
                raise Invalid(f"record {seq}: {kind} time differs from its TICK")
            if kind == "ACTION":
                if fields[2] not in [w["name"] for w in watched] or len(fields) not in (5, 7):
                    raise Invalid(f"record {seq}: malformed ACTION")
                if fields[-1] not in ("accepted=0", "accepted=1"):
                    raise Invalid(f"record {seq}: ACTION lacks acceptance")
                if len(fields) == 7:
                    real(fields[4], "ACTION x")
                    real(fields[5], "ACTION y")
            else:
                pairs(fields[3:], "EVENT")
            events.append({"seq": seq, "callback": current[0], "t": current[1], "kind": kind,
                           "name": fields[2], "detail": "|".join(fields[3:])})
        elif kind == "END":
            if len(fields) != 4:
                raise Invalid(f"record {seq}: malformed END")
            info = pairs(fields[2:], "END")
            if fields[1] != begin[1] or info.get("map") != meta["map"]:
                raise Invalid("END identity differs from BEGIN")
            end = info
    if end is None:
        raise Invalid("missing END (incomplete capture)")
    if not run:
        raise Invalid("missing RUN")
    if current and current[2] != len(watched):
        raise Invalid(f"callback {current[0]} has missing SAMPLE records")
    expected = int(run["callbacks"])
    if end.get("callbacks") != str(expected) or len(ticks) != expected + 1:
        raise Invalid(f"incomplete callbacks: END {end.get('callbacks')}, ticks {len(ticks) - 1}, requested {expected}")
    # A v2 generated map may declare a delayed start (docs/scenario-v2.md). Its
    # library clock then starts at a time float32 cannot hold exactly, and callback
    # 0 reads a small nonzero elapsed time; it must still precede callback 1.
    declared = pairs(setup[0].split("|"), "SETUP") if len(setup) == 1 and setup[0].startswith("scenario_sha256=") else {}
    delayed = declared.get("scenario_version") == "2" and declared.get("start", "0") != "0"
    if Decimal(ticks[0]["t"]) != 0 and not (delayed and Decimal(ticks[0]["t"]) < Decimal(run["requested_period"])):
        raise Invalid("callback 0 is not at clock zero")

    times = [Decimal(tick["t"]) for tick in ticks]
    deltas = [b - a for a, b in zip(times, times[1:])]
    finals = {}
    for sample in samples:
        finals[sample["unit"]] = {k: sample[k] for k in ("callback", "t", "x", "y", "facing", "order")}
    return {
        "file": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256("\n".join(records).encode("ascii")).hexdigest(),
        "footer": lines[-2],
        "generated_preload_entries": generated,
        "experiment": begin[1], "map": meta["map"], "lib": meta["lib"],
        "clock_duration": meta["clock_duration"],
        "requested_period": run["requested_period"], "callbacks": expected,
        "records": len(records), "watched": watched, "setup": setup,
        "elapsed_last": ticks[-1]["t"],
        "observed_intervals": sorted({str(d) for d in deltas}, key=Decimal),
        "equal_time_callbacks": sum(1 for d in deltas if d == 0),
        "actions": [e for e in events if e["kind"] == "ACTION"],
        "final": finals,
        "_ticks": ticks, "_samples": samples, "_events": events,
        "_records": records, "_build": begin[2],
    }


def write_csv(path, rows, columns):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--build", default=BUILD)
    parser.add_argument("--experiment", help="required experiment ID, e.g. MOV-0001")
    parser.add_argument("--map", help="required map label, e.g. MOV-0002-r2")
    parser.add_argument("--csv-dir", type=Path, help="write <capture>-samples.csv, -events.csv")
    args = parser.parse_args()
    reports, failed = [], False
    for path in args.captures:
        try:
            report = parse(path, args.build, args.experiment, args.map)
        except (OSError, Invalid) as error:
            print(f"INVALID: {path}: {error}", file=sys.stderr)
            failed = True
            continue
        if args.csv_dir:
            args.csv_dir.mkdir(parents=True, exist_ok=True)
            stem = f"{report['map']}-{path.stem}"
            write_csv(args.csv_dir / f"{stem}-samples.csv", report["_samples"],
                      ["seq", "callback", "t", "unit", "x", "y", "facing", "order"])
            write_csv(args.csv_dir / f"{stem}-events.csv", report["_events"],
                      ["seq", "callback", "t", "kind", "name", "detail"])
        reports.append({k: v for k, v in report.items() if not k.startswith("_")})
    by_map = {}
    for report in reports:
        by_map.setdefault(report["map"], set()).add(report["payload_sha256"])
    print(json.dumps({"captures": reports,
                      "payloads_identical_per_map": {m: len(h) == 1 for m, h in by_map.items()}},
                     indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

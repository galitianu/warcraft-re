#!/usr/bin/env python3
"""Summarize parsed Phase 1 captures: repeatability, movement landmarks and timing.

Reads raw captures through oracle_parse (no normalization) and prints JSON. Numbers
are exact decimal arithmetic on emitted strings; derived rates are labelled as such.
Usage: python3 tools/summarize_phase1.py [--csv-dir DIR] MAP_LABEL...
"""
import argparse
from collections import Counter
from decimal import Decimal as D
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import oracle_parse  # noqa: E402

ROOT = Path("oracle/captures/wc3-1.29.2-9231-x86")


def details(event):
    return dict(field.split("=", 1) for field in event["detail"].split("|") if "=" in field)


def movement(samples, unit="u0"):
    rows = [s for s in samples if s["unit"] == unit]
    first = rows[0]
    moved = next((r for r in rows if (r["x"], r["y"]) != (first["x"], first["y"])), None)
    turned = next((r for r in rows if r["facing"] != first["facing"]), None)
    steps = []
    for a, b in zip(rows, rows[1:]):
        dx, dy = D(b["x"]) - D(a["x"]), D(b["y"]) - D(a["y"])
        steps.append({"callback": b["callback"], "dt": str(D(b["t"]) - D(a["t"])),
                      "step": str((dx * dx + dy * dy).sqrt().quantize(D("0.000001")))})
    orders = []
    for a, b in zip(rows, rows[1:]):
        if a["order"] != b["order"]:
            orders.append({"callback": b["callback"], "t": b["t"], "from": a["order"], "to": b["order"]})
    moving = [D(s["step"]) for s in steps if D(s["step"]) > 0]
    return {
        "initial": {k: first[k] for k in ("x", "y", "facing", "order")},
        "first_position_change": moved and {k: moved[k] for k in ("callback", "t", "x", "y", "facing")},
        "first_facing_change": turned and {k: turned[k] for k in ("callback", "t", "x", "y", "facing")},
        "order_changes": orders,
        "moving_callbacks": len(moving),
        "max_step": str(max(moving)) if moving else "0",
        "most_common_steps": Counter(str(s) for s in moving).most_common(3),
        "final": {k: rows[-1][k] for k in ("callback", "t", "x", "y", "facing", "order")},
        "_rows": rows, "_steps": steps,
    }


def timing(report):
    clocks = [(e["callback"], details(e)) for e in report["_events"] if e["name"] == "CLOCKS"]
    c10 = [D(c["c10_9"]) for _, c in clocks]
    c10_deltas = [b - a for a, b in zip(c10, c10[1:])]
    changes, previous = [], None
    for callback, c in clocks:
        state = (c["x_9"], c["y_9"], c["facing_9"])
        if previous is not None and state != previous[1]:
            changes.append((callback, D(c["c10_9"])))
        previous = (callback, state)
    change_gaps = [b[1] - a[1] for a, b in zip(changes, changes[1:])]
    return {
        "tick_intervals_1000s_clock": Counter(str(D(b["t"]) - D(a["t"])) for a, b in
                                              zip(report["_ticks"], report["_ticks"][1:])).most_common(),
        "c10_intervals_9dp": Counter(str(d) for d in c10_deltas).most_common(8),
        "c100_intervals_9dp": Counter(str(D(b["c100_9"]) - D(a["c100_9"])) for (_, a), (_, b) in
                                      zip(clocks, clocks[1:])).most_common(8),
        "zero_c10_intervals": sum(1 for d in c10_deltas if d == 0),
        "c10_last": str(c10[-1]),
        "c10_remaining_plus_elapsed": sorted({str(D(c["c10_9"]) + D(c["c10_remaining_9"])) for _, c in clocks}),
        "state_changes": len(changes),
        "first_state_changes": [(cb, str(t)) for cb, t in changes[:6]],
        "state_change_gaps_c10": Counter(str(g) for g in change_gaps).most_common(8),
        "last_state_change": changes and (changes[-1][0], str(changes[-1][1])),
    }


def summarize(label, csv_dir=None):
    runs = sorted((ROOT / label).glob("run-*.txt"))
    reports = [oracle_parse.parse(run, map_label=label) for run in runs]
    first = reports[0]
    payloads = {r["payload_sha256"] for r in reports}
    generated = {json.dumps(r["generated_preload_entries"]) for r in reports}
    result = {
        "map": label, "experiment": first["experiment"], "runs": len(reports),
        "payloads_identical": len(payloads) == 1, "payload_sha256": sorted(payloads),
        "raw_sha256": sorted({r["sha256"] for r in reports}),
        "footers": sorted({r["footer"] for r in reports}),
        "generated_entries_identical": len(generated) == 1,
        "generated_entries": len(first["generated_preload_entries"]),
        "records": first["records"], "callbacks": first["callbacks"],
        "requested_period": first["requested_period"], "watched": first["watched"],
        "actions": [{k: a[k] for k in ("callback", "t", "name", "detail")} for a in first["actions"]],
        "units": {},
    }
    for unit in [w["name"] for w in first["watched"]]:
        m = movement(first["_samples"], unit)
        result["units"][unit] = {k: v for k, v in m.items() if not k.startswith("_")}
    if first["experiment"] == "JASS-0001":
        result["timing"] = timing(first)
    if csv_dir:
        out = Path(csv_dir) / label
        out.mkdir(parents=True, exist_ok=True)
        for run, report in zip(runs, reports):
            if run != runs[0] and report["payload_sha256"] == first["payload_sha256"]:
                continue  # identical observation payload: one derived copy suffices
            oracle_parse.write_csv(out / f"{run.stem}-samples.csv", report["_samples"],
                                   ["seq", "callback", "t", "unit", "x", "y", "facing", "order"])
            oracle_parse.write_csv(out / f"{run.stem}-events.csv", report["_events"],
                                   ["seq", "callback", "t", "kind", "name", "detail"])
    return result


def compare(a_label, b_label, a_unit="u0", b_unit="u0"):
    """First callback where two maps' SAMPLE values differ (time excluded)."""
    rows = []
    for label, unit in ((a_label, a_unit), (b_label, b_unit)):
        report = oracle_parse.parse(sorted((ROOT / label).glob("run-*.txt"))[0], map_label=label)
        rows.append([s for s in report["_samples"] if s["unit"] == unit])
    keys = ("x", "y", "facing", "order")
    for a, b in zip(*rows):
        if any(a[k] != b[k] for k in keys):
            return {"maps": [a_label, b_label], "first_divergence_callback": a["callback"],
                    a_label: {k: a[k] for k in ("t",) + keys}, b_label: {k: b[k] for k in ("t",) + keys}}
    return {"maps": [a_label, b_label], "identical_callbacks": min(map(len, rows))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--csv-dir", type=Path)
    parser.add_argument("--compare", action="store_true",
                        help="compare u0 SAMPLE values of each label with the first label")
    args = parser.parse_args()
    if args.compare:
        print(json.dumps([compare(args.labels[0], other) for other in args.labels[1:]], indent=1))
        return
    print(json.dumps([summarize(label, args.csv_dir) for label in args.labels], indent=1))


if __name__ == "__main__":
    raise SystemExit(main())

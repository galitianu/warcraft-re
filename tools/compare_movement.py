#!/usr/bin/env python3
"""Provisional Phase 2 CSV comparison; never read by the simulation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

# Fixed before running either model. Units: world units, degrees, seconds.
from trace_contract import TOLERANCES
PROPERTIES = tuple(TOLERANCES)
REFERENCE_BUILD = "wc3-1.29.2-9231-x86"
ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_samples(path, callbacks, units):
    with Path(path).open(newline="") as source:
        reader = csv.DictReader(source)
        required = {"callback", "t", "unit", "x", "y", "facing", "order"}
        if set(reader.fieldnames or []) not in (required, required | {"seq"}):
            raise ValueError(f"{path}: invalid sample columns")
        rows = list(reader)
    expected = [(cb, f"u{u}") for cb in range(callbacks + 1) for u in range(units)]
    if len(rows) != len(expected):
        raise ValueError(f"{path}: expected {len(expected)} samples, got {len(rows)}")
    previous_time = -1.0
    previous_seq = -1
    for index, (row, key) in enumerate(zip(rows, expected)):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("ragged row")
            if (int(row["callback"]), row["unit"]) != key:
                raise ValueError(f"expected ordered callback/unit {key}")
            for prop in PROPERTIES:
                number = int(row[prop]) if prop == "order" else float(row[prop])
                if not math.isfinite(number):
                    raise ValueError(f"nonfinite {prop}")
            if not 0 <= float(row["facing"]) < 360:
                raise ValueError("facing outside [0,360)")
            if int(row["order"]) < 0:
                raise ValueError("negative order")
            t = float(row["t"])
            if t < previous_time:
                raise ValueError("time decreased")
            if key[1] != "u0" and t != previous_time:
                raise ValueError("units in callback have different times")
            previous_time = t
            if "seq" in row:
                seq = int(row["seq"])
                if seq <= previous_seq:
                    raise ValueError("sequence not strictly increasing")
                previous_seq = seq
        except (TypeError, ValueError) as error:
            raise ValueError(f"{path}: row {index + 2}: {error}") from error
    return rows


def delta(prop, reference, actual):
    if prop == "order":
        return int(actual) - int(reference)
    value = float(actual) - float(reference)
    return (value + 180) % 360 - 180 if prop == "facing" else value


def compare_case(reference_path, actual_path, case, callbacks, units):
    # Counts come from the runner's case table; the WC3 reference must agree.
    reference = read_samples(reference_path, callbacks, units)
    actual = read_samples(actual_path, callbacks, units)
    properties = {prop: {"samples": len(reference), "failures": 0,
                         "max_abs_delta": 0, "final_delta_by_unit": {},
                         "first_divergence": None} for prop in PROPERTIES}
    first = None
    for index, (ref, act) in enumerate(zip(reference, actual)):
        for prop, tolerance in TOLERANCES.items():
            difference = delta(prop, ref[prop], act[prop])
            stats = properties[prop]
            stats["max_abs_delta"] = max(stats["max_abs_delta"], abs(difference))
            stats["final_delta_by_unit"][ref["unit"]] = difference
            if abs(difference) > tolerance:
                stats["failures"] += 1
                divergence = {"sample_index": index, "callback": int(ref["callback"]),
                              "unit": ref["unit"], "property": prop,
                              "reference_t": ref["t"], "actual_t": act["t"],
                              "reference": ref[prop], "actual": act[prop],
                              "delta": difference, "tolerance": tolerance}
                if stats["first_divergence"] is None:
                    stats["first_divergence"] = divergence
                if first is None:
                    first = divergence
    for stats in properties.values():
        stats["status"] = "PASS" if stats["failures"] == 0 else "FAIL"
    return {"case": case, "status": "PASS" if first is None else "FAIL",
            "reference_samples": len(reference), "actual_samples": len(actual),
            "reference_sha256": sha256(reference_path), "actual_sha256": sha256(actual_path),
            "first_divergence": first, "properties": properties}


def compare_suite(reference_root, actual_root):
    identity = json.loads((Path(actual_root) / "identity.json").read_text())
    shapes = {entry["test"]: (int(entry["callbacks"]), int(entry["units"]))
              for entry in identity["cases"]}
    cases = []
    for number in range(1, 11):
        case = f"MOV-{number:04d}"
        label = "MOV-0002-r2" if number == 2 else case
        if case not in shapes:
            raise ValueError(f"identity.json lacks {case}")
        cases.append(compare_case(Path(reference_root) / label / "run-01-samples.csv",
                                  Path(actual_root) / f"{case}.csv", case, *shapes[case]))
    return {"reference_build": REFERENCE_BUILD, "identity": identity,
            "alignment": "ordered (callback, unit); requested schedule, no time resampling",
            "delta_convention": "actual minus reference; facing wrapped to [-180,180)",
            "tolerances": TOLERANCES, "cases": cases}


def format_first(first):
    if first is None:
        return "—"
    return (f"cb {first['callback']} {first['unit']} {first['property']}: "
            f"{first['reference']} → {first['actual']} (Δ {first['delta']:.9g})")


def markdown(report):
    identity = report["identity"]
    lines = [f"# {identity['model']} — {identity['observation_phase']}", "",
             f"Reference: `{report['reference_build']}`. Delta = actual − reference.", "",
             "Tolerances: X/Y 0.001 world unit, facing 0.001° circular, order exact;",
             "clock 0.0000615 s. Compare in callback/unit sequence; do not resample.", "",
             "| Case | Result | Reference / actual samples | First divergence |",
             "|---|---|---|---|"]
    for case in report["cases"]:
        lines.append(f"| {case['case']} | {case['status']} | {case['reference_samples']} / "
                     f"{case['actual_samples']} | {format_first(case['first_divergence'])} |")
    lines += ["", "Per-property results continue through the final sample. Final deltas are",
              "listed per unit (the stationary control must not hide u0's endpoint error).", ""]
    for case in report["cases"]:
        lines += [f"## {case['case']}", "",
                  "| Property | Samples / failing | Max absolute Δ | Final Δ by unit | First divergence |",
                  "|---|---|---|---|---|"]
        for prop, stats in case["properties"].items():
            finals = "; ".join(f"{u}: {d:.9g}" for u, d in stats["final_delta_by_unit"].items())
            lines.append(f"| {prop} | {stats['samples']} / {stats['failures']} | "
                         f"{stats['max_abs_delta']:.9g} | {finals} | "
                         f"{format_first(stats['first_divergence'])} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path,
                        default=ROOT / "oracle/derived" / REFERENCE_BUILD)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        report = compare_suite(args.reference, args.actual)
        if args.json:
            args.json.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        if args.markdown:
            args.markdown.write_text(markdown(report))
        for case in report["cases"]:
            print(f"{case['case']} {case['status']}: {format_first(case['first_divergence'])}")
        return int(any(case["status"] == "FAIL" for case in report["cases"]))
    # Everything short of a completed comparison is malformed input, never exit 1.
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, csv.Error) as error:
        parser.exit(2, f"compare_movement: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())

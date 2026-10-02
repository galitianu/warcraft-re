#!/usr/bin/env python3
"""Run finite Phase 2 models and retain reports, identity and trace hashes."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

from compare_movement import REFERENCE_BUILD, ROOT, compare_suite, format_first, markdown, sha256
from oracle_parse import parse
from trace_contract import SCENARIOS


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def change(old, new):
    old_cb = old["callback"] if old else None
    new_cb = new["callback"] if new else None
    if old_cb == new_cb:
        return "unchanged"
    if new_cb is None or (old_cb is not None and new_cb > old_cb):
        return "later"
    return "earlier"


def verify_references(reference):
    """Check chosen CSV strings against raw data, without rewriting either."""
    verified = []
    labels = ["MOV-0002-r2" if n == 2 else f"MOV-{n:04d}" for n in range(1, 11)]
    labels += ["JASS-0001-p001", "JASS-0001-p010", "JASS-0001-p020"]
    for label in labels:
        experiment = "MOV-0002" if label == "MOV-0002-r2" else (
            "JASS-0001" if label.startswith("JASS") else label)
        raw_dir = ROOT / "oracle/captures" / REFERENCE_BUILD / label
        captures = [parse(raw_dir / f"run-{n:02d}.txt", experiment=experiment,
                          map_label=label) for n in range(1, 4)]
        if len({c["payload_sha256"] for c in captures}) != 1:
            raise ValueError(f"{label}: raw payloads differ")
        for suffix, key in (("samples", "_samples"), ("events", "_events")):
            with (reference / label / f"run-01-{suffix}.csv").open(newline="") as source:
                rows = list(csv.DictReader(source))
            raw_rows = [{k: str(v) for k, v in row.items()} for row in captures[0][key]]
            if rows != raw_rows:
                raise ValueError(f"{label}: derived {suffix} differs from raw capture")
        verified.append({"map": label, "runs_parsed": 3, "derived_rows_equal_raw": True,
                         "payload_sha256": captures[0]["payload_sha256"],
                         "raw_sha256": [c["sha256"] for c in captures]})
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()
    runner = args.runner.resolve()
    reference = ROOT / "oracle/derived" / REFERENCE_BUILD
    args.reports.mkdir(parents=True, exist_ok=True)
    write_json(args.reports / "raw-verification.json", verify_references(reference))
    reports = {}
    for name, model, phase in (("v1", "v1", "after"), ("v2", "v2", "after"),
                               ("v2-before", "v2", "before")):
        out = args.out / name
        report_dir = args.reports / name
        report_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(runner), *SCENARIOS, "--out", str(out.resolve()), "--model", model,
                        "--phase", phase, "--seed", "1"], cwd=ROOT, check=True)
        report = compare_suite(reference, out)
        reports[name] = report
        write_json(report_dir / "comparison.json", report)
        (report_dir / "comparison.md").write_text(markdown(report))
        # Regenerate CSVs with the command above; hashes bind each to its identity.
        paths = [out / "identity.json"]
        for number in range(1, 11):
            paths += [out / f"MOV-{number:04d}.csv", out / f"MOV-{number:04d}-actions.csv"]
        write_json(report_dir / "trace-hashes.json", {p.name: sha256(p) for p in paths})
        passed = sum(c["status"] == "PASS" for c in report["cases"])
        print(f"{name}: {passed}/10 cases passed; retained comparison and 21 file hashes")

    lines = ["# Model revision: footman-v1 → footman-v2", "",
             "Both use the same setups and tolerances. First divergence is compared per",
             "case/property; later does not mean passing. Before-phase is diagnostic only.", "",
             "| Case | Property | v1 first callback | v2 first callback | Change |",
             "|---|---|---|---|---|"]
    for old, new in zip(reports["v1"]["cases"], reports["v2"]["cases"]):
        for prop in ("overall", "x", "y", "facing", "order"):
            a = old["first_divergence"] if prop == "overall" else old["properties"][prop]["first_divergence"]
            b = new["first_divergence"] if prop == "overall" else new["properties"][prop]["first_divergence"]
            lines.append(f"| {old['case']} | {prop} | {a['callback'] if a else '—'} | "
                         f"{b['callback'] if b else '—'} | {change(a, b)} |")
    lines += ["", "## Observation-phase sensitivity (v2 only)", "",
              "Rows count differing primary/diagnostic samples, while each phase is still",
              "graded independently against WC3. No shifted matching or tolerance changes.", "",
              "| Case | Samples changed by phase | After first divergence | Before first divergence |",
              "|---|---|---|---|"]
    for after, before in zip(reports["v2"]["cases"], reports["v2-before"]["cases"]):
        case = after["case"]
        with (args.out / "v2" / f"{case}.csv").open(newline="") as a, \
                (args.out / "v2-before" / f"{case}.csv").open(newline="") as b:
            changed = sum(x != y for x, y in zip(csv.DictReader(a), csv.DictReader(b)))
        lines.append(f"| {case} | {changed} | {format_first(after['first_divergence'])} | "
                     f"{format_first(before['first_divergence'])} |")
    (args.reports / "model-history.md").write_text("\n".join(lines) + "\n")

    evidence = {}
    for number in range(1, 11):
        label = "MOV-0002-r2" if number == 2 else f"MOV-{number:04d}"
        paths = [f"oracle/derived/{REFERENCE_BUILD}/{label}/run-01-samples.csv",
                 f"oracle/derived/{REFERENCE_BUILD}/{label}/run-01-events.csv",
                 f"oracle/captures/{REFERENCE_BUILD}/{label}/manifest.json",
                 f"oracle/captures/{REFERENCE_BUILD}/{label}/run-01.txt",
                 f"oracle-maps/{label}.w3m", f"oracle/jass/{label}.j"]
        evidence.update({path: sha256(ROOT / path) for path in paths})
    for path in ("oracle/jass/lib/oracle-v1.j", f"oracle/environment/{REFERENCE_BUILD}.json",
                 "docs/phase-2-model.md", "tools/compare_movement.py", "tools/run_phase2.py",
                 "tools/oracle_parse.py"):
        evidence[path] = sha256(ROOT / path)
    for label in ("JASS-0001-p001", "JASS-0001-p010", "JASS-0001-p020"):
        for filename in ("run-01.txt", "manifest.json"):
            path = f"oracle/captures/{REFERENCE_BUILD}/{label}/{filename}"
            evidence[path] = sha256(ROOT / path)
    write_json(args.reports / "evidence-hashes.json", evidence)
    # Numerical FAIL is a valid Phase 2 result. Malformed/missing output raises an
    # error above. For compatibility exit status, use compare_movement.py directly.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

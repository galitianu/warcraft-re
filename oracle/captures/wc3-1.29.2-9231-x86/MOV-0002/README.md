# MOV-0002 raw captures

Captured 30 September 2026 from the verified `wc3-1.29.2-9231-x86` installation in
the Windows 11 Pro ARM64 VM. See the [procedure and limits](../../../../docs/phase-0-capture.md),
[environment identity](../../../environment/wc3-1.29.2-9231-x86.json), and
[manifest](manifest.json).

`run-01.txt` through `run-20.txt` are the original files retrieved by `rdpipe pull`,
without newline conversion, rounding, filtering or other edits. Each came from a
fresh game process and an output path cleared before launch. Run 1 used World
Editor's Test Map; later runs loaded the same map bytes through `-loadfile`.

Each file has 506 consecutive `@O` records: BEGIN, SETUP, two initial SAMPLE records,
an accepted ACTION, 250 paired callbacks and END. SAMPLE fields are:

```text
@O|sequence|SAMPLE|elapsed_seconds|unit_name|x|y|facing_degrees|current_order
```

Real values are emitted by WC3's `R2SW(value,1,6)`; timestamps come from the experiment's
separate timer, not wall time or an inferred simulation tick. Payloads match across
all 20 runs. The generated `PreloadEnd` footer varies independently; distinguish
both full-file and payload hashes.

[verification.json](verification.json) records the inspector's results. It is an
extraction/repeatability report, not the later canonical trace schema or a C++
compatibility reference. Run from the repository root:

```sh
python3 tools/inspect_mov0002.py oracle/captures/wc3-1.29.2-9231-x86/MOV-0002/run-*.txt
```

Agreement applies to this map, launch setup and emitted fields. RNG seed influence,
other scenarios/platforms and hidden simulation state remain untested.

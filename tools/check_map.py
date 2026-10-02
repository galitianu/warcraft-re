#!/usr/bin/env python3
"""Check that a saved Phase 1 map contains exactly the intended authored JASS.

Requires the third-party `mpyq` package (pip install mpyq). The map is only read.
Expected trigger text: library + "\\n" + case file, compared after CRLF -> LF.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import sys

import mpyq


def read_map(path, names=("war3map.wct", "war3map.j", "war3map.w3i")):
    raw = Path(path).read_bytes()
    archive = mpyq.MPQArchive(BytesIO(raw[raw.index(b"MPQ\x1a"):]), listfile=False)
    return raw, {name: archive.read_file(name) for name in names}


def wct_texts(data):
    version, = struct.unpack_from("<i", data, 0)
    if version != 0:
        raise ValueError(f"war3map.wct version {version}: map header custom script present")
    count, = struct.unpack_from("<i", data, 4)
    offset, texts = 8, []
    for _ in range(count):
        size, = struct.unpack_from("<i", data, offset)
        texts.append(data[offset + 4:offset + 4 + size].rstrip(b"\0"))
        offset += 4 + size
    if offset != len(data):
        raise ValueError("unexpected trailing war3map.wct data")
    return texts


def check(map_path, library, case):
    raw, files = read_map(map_path)
    expected = Path(library).read_bytes() + b"\n" + Path(case).read_bytes()
    texts = [t.replace(b"\r\n", b"\n") for t in wct_texts(files["war3map.wct"])]
    script = files["war3map.j"].replace(b"\r\n", b"\n")
    w3i_version, = struct.unpack_from("<i", files["war3map.w3i"], 0)
    result = {
        "map": str(map_path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "w3i_format": w3i_version, "custom_text_triggers": len(texts),
        "trigger_matches_source": texts == [expected],
        "war3map_j_contains_source": expected in script,
        "war3map_j_runs_init_triggers": b"RunInitializationTriggers" in script,
        "generated_war3map_j_sha256": hashlib.sha256(files["war3map.j"]).hexdigest(),
        "library_sha256": hashlib.sha256(Path(library).read_bytes()).hexdigest(),
        "case_sha256": hashlib.sha256(Path(case).read_bytes()).hexdigest(),
    }
    result["ok"] = (result["trigger_matches_source"] and result["war3map_j_contains_source"]
                    and not result["war3map_j_runs_init_triggers"] and w3i_version == 18)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("case", type=Path)
    parser.add_argument("--library", type=Path, default=Path("oracle/jass/lib/oracle-v1.j"))
    args = parser.parse_args()
    try:
        result = check(args.map, args.library, args.case)
    except (OSError, ValueError, struct.error) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

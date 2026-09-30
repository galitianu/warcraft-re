#!/usr/bin/env python3
"""Check oracle_parse against a real capture and deliberately altered temporary copies.

Run from the repository root: python3 tools/test_oracle_parse.py
Retained captures are only read; alterations are written to a temporary directory.
"""
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import oracle_parse  # noqa: E402

REAL = Path("oracle/captures/wc3-1.29.2-9231-x86/MOV-0002-r2/run-01.txt")


class ParserChecks(unittest.TestCase):
    def setUp(self):
        self.text = REAL.read_text(encoding="ascii")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def variant(self, text):
        path = Path(self.tmp.name) / "altered.txt"
        path.write_bytes(text.encode("ascii"))
        return path

    def record(self, seq):
        return re.search(rf'"@O\|{seq}\|[^"]*"', self.text)[0]

    def rejects(self, text, pattern):
        with self.assertRaisesRegex(oracle_parse.Invalid, pattern):
            oracle_parse.parse(self.variant(text), map_label="MOV-0002-r2")

    def test_real_capture(self):
        report = oracle_parse.parse(REAL, experiment="MOV-0002", map_label="MOV-0002-r2")
        self.assertEqual((report["records"], report["callbacks"], report["equal_time_callbacks"]), (760, 250, 0))
        self.assertEqual(report["final"]["u0"]["x"], "988.133301")

    def test_truncated(self):
        self.rejects(self.text[: len(self.text) // 2], "envelope")

    def test_missing_end(self):
        self.rejects(self.text.replace(self.record(759), '"@O|759|EVENT|5.000000|X|a=1"'), "outside|END")

    def test_sequence_gap(self):
        self.rejects(re.sub(r'\n[^\n]*"@O\|100\|[^\n]*', "", self.text), "sequence discontinuity")

    def test_wrong_build(self):
        self.rejects(self.text.replace("wc3-1.29.2-9231-x86", "wc3-1.29.2-9321-x86", 1), "wrong build")

    def test_wrong_map(self):
        self.rejects(self.text.replace("map=MOV-0002-r2", "map=MOV-0003"), "wrong map")

    def test_malformed_sample(self):
        s = self.record(10)
        self.rejects(self.text.replace(s, s.replace(".", ",", 2)), "SAMPLE|real")

    def test_missing_sample(self):
        # Drop one unit's sample and renumber so only the callback shape is wrong.
        lines = self.text.split("\n")
        index = next(i for i, l in enumerate(lines) if '"@O|10|' in l)
        self.assertIn("SAMPLE", lines[index])
        del lines[index]
        renumbered, seq = [], 0
        for line in lines:
            if '"@O|' in line:
                line = re.sub(r'"@O\|\d+\|', f'"@O|{seq}|', line)
                seq += 1
            renumbered.append(line)
        self.rejects("\n".join(renumbered), "missing SAMPLE|unexpected SAMPLE")

    def test_decreasing_clock(self):
        t = re.search(r'"@O\|\d+\|TICK\|([\d.]+)\|7"', self.text)[1]
        self.rejects(self.text.replace(f"|{t}|", "|0.000001|"), "decreased")

    def test_equal_time_callbacks_are_kept_in_sequence_order(self):
        # Give callbacks 5 and 6 the same reading: valid, reported, never reordered.
        t5 = re.search(r'"@O\|\d+\|TICK\|([\d.]+)\|5"', self.text)[1]
        t6 = re.search(r'"@O\|\d+\|TICK\|([\d.]+)\|6"', self.text)[1]
        report = oracle_parse.parse(self.variant(self.text.replace(f"|{t6}|", f"|{t5}|")),
                                    map_label="MOV-0002-r2")
        self.assertEqual(report["equal_time_callbacks"], 1)
        rows = [r for r in report["_samples"] if r["t"] == t5]
        self.assertEqual([(r["callback"], r["unit"]) for r in rows], [(5, "u0"), (5, "u1"), (6, "u0"), (6, "u1")])
        self.assertEqual([r["seq"] for r in rows], sorted(r["seq"] for r in rows))

    def test_sample_moved_before_its_tick(self):
        # Swap the payloads of records 11 (SAMPLE u1, callback 1) and 12 (TICK 2),
        # keeping sequence numbers continuous.
        a, b = self.record(11), self.record(12)
        self.assertIn("SAMPLE", a)
        self.assertIn("TICK", b)
        a2 = a.replace("@O|11|", "@O|12|")
        b2 = b.replace("@O|12|", "@O|11|")
        swapped = self.text.replace(a, "\0").replace(b, a2).replace("\0", b2)
        self.rejects(swapped, "missing SAMPLE")

    def test_rejected_order_is_reported_not_hidden(self):
        report = oracle_parse.parse(self.variant(self.text.replace("accepted=1", "accepted=0")),
                                    map_label="MOV-0002-r2")
        self.assertTrue(report["actions"][0]["detail"].endswith("accepted=0"))

    def test_generated_entries_excluded_from_payload(self):
        base = oracle_parse.parse(REAL, map_label="MOV-0002-r2")
        extra = self.text.replace("\tcall PreloadEnd", '\tcall Preload( "Textures\\\\Extra.blp" )\n\tcall PreloadEnd')
        report = oracle_parse.parse(self.variant(extra), map_label="MOV-0002-r2")
        self.assertEqual(report["payload_sha256"], base["payload_sha256"])
        self.assertEqual(len(report["generated_preload_entries"]), len(base["generated_preload_entries"]) + 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

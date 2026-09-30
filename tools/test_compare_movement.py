"""Checks of comparison integrity, separate from engine/gameplay outcomes."""
import csv
import tempfile
import unittest
from pathlib import Path

from compare_movement import compare_case, read_samples


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reference = Path(self.temp.name) / "reference.csv"
        self.actual = Path(self.temp.name) / "actual.csv"
        self.rows = [{"callback": str(cb), "t": f"{cb * .02:.6f}", "unit": "u0",
                      "x": "0", "y": "0", "facing": "359.9998", "order": "0"}
                     for cb in range(251)]
        self.write(self.reference, self.rows)

    @staticmethod
    def write(path, rows):
        with path.open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_circular_facing_and_clock_quantization(self):
        for row in self.rows:
            row["facing"] = "0.0002"
        self.rows[1]["t"] = "0.020061"
        self.write(self.actual, self.rows)
        self.assertEqual(compare_case(self.reference, self.actual, "MOV-0001")["status"], "PASS")

    def test_first_failure_and_accumulated_deltas(self):
        self.rows[1]["x"] = "0.0011"
        self.rows[2]["order"] = "851986"
        self.rows[-1]["x"] = "12"
        self.write(self.actual, self.rows)
        report = compare_case(self.reference, self.actual, "MOV-0001")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["first_divergence"]["callback"], 1)
        self.assertEqual(report["properties"]["x"]["max_abs_delta"], 12)
        self.assertEqual(report["properties"]["x"]["final_delta_by_unit"], {"u0": 12})
        self.assertEqual(report["properties"]["order"]["first_divergence"]["callback"], 2)

    def test_incomplete_reordered_and_nonfinite_rejected(self):
        bad_rows = [self.rows[:-1], [self.rows[1], self.rows[0]] + self.rows[2:]]
        for value in ("nan", "inf", "-inf"):
            rows = [dict(row) for row in self.rows]
            rows[5]["x"] = value
            bad_rows.append(rows)
        for rows in bad_rows:
            with self.subTest(rows=rows[0]):
                self.write(self.actual, rows)
                with self.assertRaises(ValueError):
                    compare_case(self.reference, self.actual, "MOV-0001")

    def test_equal_time_callbacks_preserve_order(self):
        self.rows[1]["t"] = "0.000000"
        self.write(self.actual, self.rows)
        rows = read_samples(self.actual, 250, 1)
        self.assertEqual([int(row["callback"]) for row in rows[:2]], [0, 1])


if __name__ == "__main__":
    unittest.main()

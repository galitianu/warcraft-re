import unittest

from wc3_float import add, bits, r2sw, sub


class R2swTest(unittest.TestCase):
    def test_six_decimals_round_half_up_of_truncated_fraction(self):
        self.assertEqual(r2sw(bits(-155 / 4096), 6), '-0.037842')
        self.assertEqual(r2sw(bits(267.287109375), 6), '267.287109')
        self.assertEqual(r2sw(0, 6), '0.000000')

    def test_library_clock_reads_like_wc3(self):
        # MOV-0004 callback 503: TimerGetElapsed of the 1000 s clock printed 10.059937.
        start, timeout, scheduled = 0x3f000000, bits(1000.0), 0x3f000000
        for _ in range(503):
            scheduled = add(scheduled, bits(0.02))
        self.assertEqual(r2sw(sub(timeout, sub(add(start, timeout), scheduled)), 6), '10.059937')

    def test_nine_decimals(self):
        self.assertEqual(r2sw(bits(0.5), 9), '0.500000000')
        self.assertEqual(r2sw(0x3bbc919d, 9), '0.005754663')


if __name__ == '__main__':
    unittest.main()

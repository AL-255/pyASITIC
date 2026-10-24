import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.network_metrics import probe
from reasitic import Technology


class NetworkMetricTests(unittest.TestCase):
    def test_original_technology_coordinate_height_stores(self):
        cases = json.loads((Path(__file__).parent / "fixtures/pi_sessions_original.json").read_text())["cases"]
        for c in cases:
            tech = Technology.from_text(c["request"]["technology"])
            actual = [struct.pack('<d', m.geometry_height).hex() for m in tech.metals]
            self.assertEqual(actual, c["model"]["coordinate_heights"], (c["fixture"], c["index"]))

    def test_intact_original_metric_records(self):
        cases = json.loads((Path(__file__).parent / "fixtures/network_metrics_original.json").read_text())["cases"]
        components = 0
        for offset in range(0, len(cases), 256):
            batch = cases[offset:offset + 256]
            rows = [[float(v) for v in c["input"]] for c in batch]
            saved = [struct.pack('<26d', *row) for row in rows]
            result = probe(rows)
            self.assertEqual(saved, [struct.pack('<26d', *row) for row in rows])
            for i, (case, output) in enumerate(zip(batch, result)):
                expected = bytes.fromhex(case["output_bits"])
                self.assertEqual(output[0], 0)
                for k in range(28):
                    value = struct.unpack_from('<d', expected, 8 * k)[0]
                    if math.isnan(value):
                        self.assertTrue(math.isnan(output[k + 1]), (offset + i, k))
                    else:
                        self.assertEqual(struct.pack('<d', output[k + 1]), expected[8 * k:8 * k + 8], (offset + i, k))
                    components += 1
                for k, raw in enumerate(case["extended_bits"]):
                    target = bytes.fromhex(raw)
                    if struct.unpack_from('<H', target, 8)[0] & 0x7fff != 0x7fff:
                        self.assertEqual(struct.pack('<IIH', *map(int, output[29 + 3 * k:32 + 3 * k])), target, (offset + i, k))
        self.assertEqual(components, 28 * len(cases))


if __name__ == '__main__':
    unittest.main()

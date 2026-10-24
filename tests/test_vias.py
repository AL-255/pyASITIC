import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.vias import stamp,active_height


class ViaTests(unittest.TestCase):
    def test_original_via_formula_and_stores(self):
        cases=json.loads((Path(__file__).parent/"fixtures/vias_original.json").read_text())["cases"]
        rows=[c["input"][:5]+[int(v) for v in c["input"][5:7]]+c["input"][7:] for c in cases]
        for i,(actual,case) in enumerate(zip(stamp(rows),cases)):
            for value,bits in zip((actual.real,actual.imag),case["output_bits"]):
                expected=struct.unpack("<d",bytes.fromhex(bits))[0]
                # Portable guard precision is a fallback; compiled browser tests
                # require exact bits for every component of these same cases.
                if math.isnan(expected):self.assertTrue(math.isnan(value),str(i))
                elif math.isinf(expected):self.assertEqual(value,expected,str(i))
                else:self.assertAlmostEqual(value,expected,delta=4*math.ulp(expected),msg=str(i))

    def test_height_threshold_and_invalid_counts(self):
        self.assertFalse(active_height(0.,1e-10))
        self.assertTrue(active_height(0.,math.nextafter(1e-10,math.inf)))
        for counts in ((-65536,1),(1,1.5),(1,65536)):
            with self.assertRaisesRegex(ValueError,"via record"):
                stamp([[1e9,0.,1.,.8,.137,*counts,0.,0.]])

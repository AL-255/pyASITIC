import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.table_kernel import _coefficient_records,layer_coefficients

class LayerCoefficientTests(unittest.TestCase):
    def test_original_frequency_weight_and_scalar_inverse_bits(self):
        fixture=json.loads((Path(__file__).parent/"fixtures/layer_coefficients.json").read_text())
        components=0
        for c in fixture["cases"]:
            values=_coefficient_records([(float(r),float(e)) for r,e in c["records"]],float(c["frequency"]))
            actual=[v for z in values for v in (z.real,z.imag)]
            self.assertEqual(len(actual),len(c["output"]))
            for i,(value,expected) in enumerate(zip(actual,c["output"])):
                with self.subTest(frequency=c["frequency"],layers=len(values),component=i):
                    if expected=="nan":self.assertTrue(math.isnan(value))
                    elif expected in ("inf","-inf"):self.assertEqual(value,float(expected))
                    else:self.assertEqual(struct.pack("<d",value),struct.pack("<d",expected),"Original coefficient bits")
                components+=1
        self.assertEqual(components,fixture["components"])

    def test_reader_resistivity_conversion_before_coefficient_loop(self):
        substrate=[dict(rho=10.,eps=11.9),dict(rho=1e12,eps=3.9)]
        actual=layer_coefficients(substrate,1e9)
        expected=_coefficient_records([(100000.,11.9),(1e16,3.9)],1e9)
        self.assertEqual(actual,expected)

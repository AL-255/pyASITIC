import json
import math
from pathlib import Path
import unittest
from reasitic.symmetric import factor_symmetric_upper,inverse_symmetric,_eigen2
from reasitic.green import _guard


class SymmetricTests(unittest.TestCase):
    def compare(self,actual,expected):
        if isinstance(expected,str):
            if expected=="nan":self.assertTrue(math.isnan(actual))
            else:self.assertEqual(actual,float(expected))
        else:self.assertAlmostEqual(actual,expected,delta=max(1e-12,abs(expected)*1e-10))

    def test_native_factors_pivots_and_inverse(self):
        cases=json.loads((Path(__file__).parent/"fixtures/symmetric.json").read_text())["cases"]
        for case in cases:
            a=[[complex(*z) for z in row] for row in case["matrix"]]
            with self.subTest(n=len(a),stride=case["stride"],status=case["S"]):
                if case["S"]:
                    with self.assertRaisesRegex(ValueError,"Singular"):inverse_symmetric(a)
                    continue
                factor,pivots=factor_symmetric_upper(a);self.assertEqual(pivots,case["P"])
                for actual,key in ((factor,"F"),(inverse_symmetric(a),"I")):
                    for i,row in enumerate(actual):
                        for j in range(i,len(a)):
                            for value,reference in zip((row[j].real,row[j].imag),case[key][i][j]):self.compare(value,reference)

    def test_native_eigen_rotations(self):
        cases=json.loads((Path(__file__).parent/"fixtures/symmetric.json").read_text())["eigen"]
        for case in cases:
            with self.subTest(values=case["input"]):
                actual=_guard(_eigen2)(*(complex(*z) for z in case["input"]))
                for z,expected in zip(actual,case["result"]):
                    for value,reference in zip((z.real,z.imag),expected):self.compare(value,reference)

import json
import math
from pathlib import Path
import struct
import unittest
from reasitic import Technology, build, resistance_dc, resistance_hf
from reasitic.inductance import inductance_estimate, coupling_estimate


class ReferenceAnalysisTests(unittest.TestCase):
    def test_connected_command_reports(self):
        cases = json.loads((Path(__file__).parent/"fixtures/analysis.json").read_text())["cases"]
        tech = Technology.default()
        for case in cases:
            params = dict(case["parameters"])
            for key in ("gap","angle"):
                if key in params:
                    params[key] = struct.unpack("f",struct.pack("f",math.radians(params[key])))[0]*180/math.pi
            with self.subTest(kind=case["kind"],parameters=params):
                shape = build(case["kind"],technology=tech,**params)
                expected = case["inductance_nh"]
                # Native %lg report: six significant digits.
                tolerance = 0.51*10**(math.floor(math.log10(abs(expected)))-5)
                self.assertAlmostEqual(inductance_estimate(shape,tech),expected,delta=tolerance)
                self.assertAlmostEqual(resistance_dc(shape,tech),case["dc"],delta=5.1e-7)
                for f,r in case["hf"]:
                    self.assertAlmostEqual(resistance_hf(shape,tech,f),r,delta=5.1e-7,msg=f"at {f:g} Hz")

    def test_coupling_translation_and_phase(self):
        tech = Technology.default()
        a = build("square",metal="M3",turns=2)
        b = build("square",metal="M4",turns=2)
        m,k = coupling_estimate(a,b,tech)
        self.assertGreater(k,0)
        self.assertLessEqual(k,1.01)
        flipped = build("square",metal="M4",turns=2,phase=-1)
        mf,kf = coupling_estimate(a,flipped,tech)
        self.assertAlmostEqual(m,-mf,places=9)
        self.assertAlmostEqual(k,-kf,places=9)
        b.origin[0] += 1000
        far_m,far_k = coupling_estimate(a,b,tech)
        self.assertLess(abs(far_m),abs(m))
        self.assertLess(abs(far_k),abs(k))


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import re
import unittest
from reasitic.bridge import handle,request_json

CASES=json.loads((Path(__file__).parent/"fixtures/pi_models.json").read_text())["cases"]


class PiModelTests(unittest.TestCase):
    def test_native_pi3_pi4_ports_and_printed_quality(self):
        for case in sorted(CASES,key=lambda c:c["frequency_hz"]):
            with self.subTest(model=case["model"],kind=case["kind"],frequency=case["frequency_hz"]):
                args={k:v for k,v in case.items() if k in ("kind","parameters","technology","ground","first_pad","second_pad","frequency_hz")}
                result=handle(dict(action=case["model"],**args))
                for key in ("admittance_matrix","scattering_matrix"):
                    for i,row in enumerate(result[key]):
                        for j,value in enumerate(row):
                            for axis,actual in enumerate(value):
                                expected=case[key][i][j][axis]
                                self.assertAlmostEqual(actual,expected,delta=max(1e-10,abs(expected)*1e-8),msg=f"{key} {i},{j}/{axis}")
                qualities=re.findall(r"Q =\s*([^,]+),([^,]+),([^\n]+)",case["model_stdout"])[-1]
                for key,value in zip(("q_first","q_second","q_differential"),qualities):
                    self.assertAlmostEqual(result["pi"][key],float(value),delta=.000501,msg=key)
                if case["model"]=="pi4":
                    self.assertGreaterEqual(result["filaments"],19)
                    self.assertEqual(len(result["pad_admittance_matrix"]),2)

    def test_ground_required_and_fast_pi_limit_is_explicit(self):
        result=json.loads(request_json(json.dumps(dict(action="pi3"))))
        self.assertIn("explicit ground",result["error"])
        result=json.loads(request_json(json.dumps(dict(action="pi"))))
        self.assertIn("native fast Pi",result["error"])

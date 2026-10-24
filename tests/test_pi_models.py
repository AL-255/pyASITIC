import json
from pathlib import Path
import re
import struct
import unittest
from reasitic.bridge import handle,request_json

CASES=json.loads((Path(__file__).parent/"fixtures/pi_models.json").read_text())["cases"]
CASES+=json.loads((Path(__file__).parent/"fixtures/pi_models_eddy.json").read_text())["cases"]
ORIGINAL=json.loads((Path(__file__).parent/"fixtures/pi_sessions_original.json").read_text())["cases"]
METRICS=json.loads((Path(__file__).parent/"fixtures/network_metrics_original.json").read_text())["cases"]
MODEL_S={c["session_index"]:bytes.fromhex(c["output_bits"])[160:224] for c in METRICS if "session_index" in c}

def original_matrices(case):
    # Pi3's type-0 reference differs from the later type-8 2PORT reference.
    # Use actual model-command Y, plus an independent original S conversion
    # at exactly that Y, rather than the unrelated repeated-command records.
    for index,c in enumerate(ORIGINAL):
        if c["request"]["action"]==case["model"] and c["request"]["parameters"]==case["parameters"] and c["request"]["frequency_hz"]==case["frequency_hz"] and c["request"].get("eddy",False)==case.get("eddy",False):
            v=[struct.unpack('<d',bytes.fromhex(bits))[0] for bits in c["model"]["Y"]]
            y=[[v[6:8],v[4:6]],[v[2:4],v[0:2]]]
            v=list(struct.unpack('<8d',MODEL_S[index]));s=[[v[0:2],v[2:4]],[v[4:6],v[6:8]]]
            return dict(admittance_matrix=y,scattering_matrix=s)
    raise AssertionError("Missing actual-original model command record")


class PiModelTests(unittest.TestCase):
    def test_native_pi3_pi4_ports_and_printed_quality(self):
        for case in sorted(CASES,key=lambda c:c["frequency_hz"]):
            with self.subTest(model=case["model"],kind=case["kind"],frequency=case["frequency_hz"]):
                args={k:v for k,v in case.items() if k in ("kind","parameters","technology","ground","first_pad","second_pad","frequency_hz","eddy")}
                result=handle(dict(action=case["model"],**args))
                matrices=original_matrices(case)
                for key in ("admittance_matrix","scattering_matrix"):
                    for i,row in enumerate(result[key]):
                        for j,value in enumerate(row):
                            for axis,actual in enumerate(value):
                                expected=matrices[key][i][j][axis]
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

import json
import math
from pathlib import Path
import unittest
from reasitic.resonance import search_self_resonance,solve_self_resonance
from reasitic import Technology,build
from reasitic.bridge import request_json


class ResonanceTests(unittest.TestCase):
    def test_native_search_traces_and_ignored_iteration_argument(self):
        cases=json.loads((Path(__file__).parent/"fixtures/resonance_search.json").read_text())["cases"]
        for case in cases:
            with self.subTest(kind=case["kind"],bounds=(case["first"],case["second"]),step=case["step"],differential=case["differential"],fast=case["fast"],fixed=case["fixed"]):
                analyses=[];observed=[]
                def analyze(frequency,fast):
                    analyses.append([frequency,int(fast)])
                    imag=(frequency-case["target"])*case["scale"] if case["kind"]==0 else float(case["fixed"])
                    return dict(y11=1+.5j,y12=.01+.02j,y21=.01+.02j,y22=complex(0 if case["kind"]==2 else 1,imag))
                result=search_self_resonance(analyze,case["first"],case["second"],case["step"],differential=case["differential"],fast=case["fast"],iteration_limit=case["iteration_limit"],observer=observed.append)
                self.assertEqual(analyses,case["analyses"])
                self.assertEqual(result["evaluations"],case["evaluations"])
                self.assertEqual(result["native_result_hz"],case["native_result_hz"])
                self.assertEqual(observed,result["trace"])
                self.assertEqual(len(result["trace"]),len(case["progress"]))
                if case["kind"]==2 and abs(case["fixed"])==100:
                    self.assertEqual(result["reason"],"frequency_step","Exactly 0.01 ohm does not satisfy the strict tolerance")
                for actual,expected in zip(result["trace"],case["progress"]):
                    values=[actual[k]/1e9 for k in ("lower_hz","upper_hz","frequency_hz")]+[actual["imaginary_impedance_ohm"]]
                    for value,reference in zip(values,expected):
                        if reference=="nan":self.assertTrue(math.isnan(value))
                        else:self.assertAlmostEqual(value,reference,delta=max(1e-12,abs(reference)*1e-12))
                if case["native_result_hz"]==-1:
                    self.assertEqual(result["reason"],"iteration_limit")
                    self.assertEqual(result["evaluations"],101)
                    self.assertIsNone(result["frequency_hz"])

    def test_invalid_inputs_and_native_fast_limitation(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=40,width=5)
        with self.assertRaisesRegex(ValueError,"fast SELFRES faults"):
            solve_self_resonance(shape,tech,1e9,2e9,1e8,fast=True)
        with self.assertRaisesRegex(ValueError,"positive"):
            solve_self_resonance(shape,tech,0,2e9,1e8)
        with self.assertRaisesRegex(ValueError,"finite"):
            search_self_resonance(None,1,2,math.nan)

    def test_complete_native_distributed_searches(self):
        cases=json.loads((Path(__file__).parent/"fixtures/resonance_physical.json").read_text())["cases"]
        for case in cases:
            with self.subTest(kind=case["kind"],process=case["process"],differential=case["differential"]):
                tech=Technology.from_text(case["technology"])
                shape=build(case["kind"],technology=tech,**case["parameters"])
                ground=build("wire",technology=tech,**case["ground"]["parameters"]) if case["ground"] else None
                progress=[]
                result=solve_self_resonance(shape,tech,case["first_hz"],case["last_hz"],case["step_hz"],
                                            ground=ground,differential=case["differential"],eddy=case["eddy"],observer=progress.append,**case["mesh"])
                self.assertEqual(progress,result["trace"])
                self.assertEqual(len(result["trace"]),len(case["progress"]))
                self.assertAlmostEqual(result["frequency_hz"]/1e9,case["frequency_ghz"],delta=1e-10)
                for actual,expected in zip(result["trace"],case["progress"]):
                    values=[actual[k]/1e9 for k in ("lower_hz","upper_hz","frequency_hz")]+[actual["imaginary_impedance_ohm"]]
                    for value,reference in zip(values,expected):
                        self.assertAlmostEqual(value,reference,delta=max(1e-8,abs(reference)*1e-8))

    def test_json_progress_and_unevaluated_reported_frequency(self):
        cases=json.loads((Path(__file__).parent/"fixtures/resonance_physical.json").read_text())["cases"]
        case=next(c for c in cases if c["ground"] is None and not c["differential"])
        payload={key:case[key] for key in ("kind","parameters","technology","ground","first_hz","last_hz","step_hz","differential","mesh")}
        points=[]
        response=json.loads(request_json(json.dumps(dict(action="selfres",**payload)),lambda point:points.append(json.loads(point))))
        result=response["result"]
        self.assertEqual(points,result["trace"])
        self.assertEqual(result["reason"],"frequency_step")
        self.assertNotEqual(result["frequency_hz"],result["last_evaluated_frequency_hz"])
        self.assertEqual(result["model"]["frequency_hz"],result["last_evaluated_frequency_hz"])

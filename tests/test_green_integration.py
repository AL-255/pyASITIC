import json
import math
from pathlib import Path
import unittest
from reasitic.green_integration import GreenLayers,GreenIntegrationState,green_integral


class GreenIntegrationTests(unittest.TestCase):
    def compare(self,actual,expected,label):
        if expected=="nan":self.assertTrue(math.isnan(actual),label)
        elif isinstance(expected,str):self.assertEqual(actual,float(expected),label)
        elif expected==0:self.assertEqual(actual,0,label)
        else:self.assertAlmostEqual(actual,expected,delta=max(1e-12,abs(expected)*1e-12),msg=label)

    def test_native_complete_integrals_and_callback_trace(self):
        cases=json.loads((Path(__file__).parent/"fixtures/green_integration.json").read_text())["cases"]
        for case in cases:
            with self.subTest(kernel=case["kernel"],frequency=case["frequency"],height=case["height"],separation=case["separation"],layers=(case["layer1"],case["layer2"])):
                state=GreenIntegrationState(GreenLayers(case["layer1"],case["layer2"],case["depth"]),case["kernel"])
                points=[]
                result=green_integral(case["frequency"],case["separation"],case["height"],case["z_offset"],state,observer=points.append)
                self.assertEqual(result.status,case["status"])
                self.assertEqual(result.observations,case["observations"])
                self.assertEqual(len(points),result.observations)
                self.compare(result.value,case["value"],"scaled integral")
                self.compare(points[0],case["first_point"],"first callback")
                self.compare(result.last_point,case["last_point"],"last callback")
                self.assertEqual([state.frequency,state.separation,state.height,state.z_offset],case["state"])
                for actual,expected in zip(state.history,case["history"]):self.compare(actual,expected,"history")
                self.assertEqual(result.method,"DQAGIE" if abs(case["separation"])<1e-10 else "DQAWFE")

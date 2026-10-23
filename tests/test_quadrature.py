from dataclasses import asdict
import json
import math
from pathlib import Path
import unittest
from reasitic.quadrature import integrate_infinite,infinite_rule

FIXTURE=json.loads((Path(__file__).parent/"fixtures/quadrature.json").read_text())


def callback(kind,scale):
    return [lambda x:1/((1+x)*(1+x)),lambda x:1/(1+x*x),lambda x:math.exp(-scale*x),
            lambda x:math.exp(-x*x),lambda x:math.sin(x)/(1+x*x),lambda x:1.,
            lambda x:math.exp(-x)/math.sqrt(x)][kind]


class QuadratureTests(unittest.TestCase):
    def test_native_infinite_integrations(self):
        for case in FIXTURE["cases"]:
            with self.subTest(kind=case["kind"],scale=case["scale"],direction=case["direction"],limit=case["limit"],relative=case["relative_tolerance"]):
                args={key:value for key,value in case.items() if key not in ("kind","scale","result")}
                result=asdict(integrate_infinite(callback(case["kind"],case["scale"]),**args))
                for key in ("status","evaluations","intervals"):
                    self.assertEqual(result[key],case["result"][key],key)
                for key in ("integral","error"):
                    expected=case["result"][key]
                    self.assertAlmostEqual(result[key],expected,delta=max(1e-13,abs(expected)*1e-12),msg=key)

    def test_native_transformed_rules(self):
        for case in FIXTURE["rules"]:
            with self.subTest(kind=case["kind"],scale=case["scale"],direction=case["direction"],a=case["a"],b=case["b"]):
                args={key:value for key,value in case.items() if key not in ("kind","scale","result")}
                result=asdict(infinite_rule(callback(case["kind"],case["scale"]),**args))
                for key,expected in case["result"].items():
                    self.assertAlmostEqual(result[key],expected,delta=max(1e-13,abs(expected)*1e-12),msg=key)

    def test_invalid_workspace_and_parameters(self):
        for args in (dict(limit=0),dict(limit=10001),dict(direction=0),dict(bound=math.inf)):
            with self.assertRaises(ValueError):
                integrate_infinite(lambda x:1/(1+x*x),**args)

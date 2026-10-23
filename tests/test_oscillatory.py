from dataclasses import asdict
import json
import math
from pathlib import Path
import unittest
from reasitic.oscillatory import (MomentCache,weighted_rule,chebyshev_transform,solve_tridiagonal,
                                  oscillatory_rule,integrate_oscillatory,integrate_fourier)
from reasitic.quadrature import _d

FIXTURE=json.loads((Path(__file__).parent/"fixtures/oscillatory.json").read_text())


def callback(kind):
    return [lambda x:1/(1+x*x),lambda x:math.exp(-x),lambda x:1/(1+x),lambda x:1.,
            lambda x:x*x*x,lambda x:abs(x-.37)][kind]


class OscillatoryTests(unittest.TestCase):
    def compare(self,actual,expected,label):
        if isinstance(expected,list):
            self.assertEqual(len(actual),len(expected),label)
            for i,(a,b) in enumerate(zip(actual,expected)):
                self.compare(a,b,label+f"[{i}]")
        elif expected=="nan":
            self.assertTrue(math.isnan(actual),label)
        elif isinstance(expected,str):
            self.assertEqual(actual,float(expected),label)
        else:
            # Cancellation-limited error estimates can differ by several
            # ulps of the underlying integral, even near a zero integral.
            floor=1e-12 if "error" in label else 1e-13
            relative=1e-10 if "error" in label else 1e-12
            self.assertAlmostEqual(actual,expected,delta=max(floor,abs(expected)*relative),msg=label)

    def test_native_weighted_and_moment_rules(self):
        for case in FIXTURE["rules"]:
            with self.subTest(kind=case["kind"],frequency=case["frequency"],selector=case["selector"],rows=case["rows"]):
                cache=MomentCache(case["rows"])
                result=oscillatory_rule(callback(case["kind"]),case["a"],case["b"],case["frequency"],case["selector"],0,False,cache)
                for key,value in asdict(result.value).items():
                    self.compare(value,case["result"][key],key)
                self.assertEqual(result.evaluations,case["result"]["evaluations"])
                self.assertEqual(cache.computed,case["result"]["computed"])
                self.compare(cache.data[0],case["moments"],"moments")
        for case in FIXTURE["weighted"]:
            with self.subTest(weighted=True,kind=case["kind"],frequency=case["frequency"],selector=case["selector"]):
                weight=lambda x:(math.sin if case["selector"]==2 else math.cos)(float(_d(case["frequency"])*_d(x)))
                result=weighted_rule(callback(case["kind"]),weight,case["a"],case["b"])
                for key,value in asdict(result).items():
                    self.compare(value,case["result"][key],key)

    def test_native_chebyshev_butterfly_and_pivoted_tridiagonal(self):
        for case in FIXTURE["chebyshev"]:
            samples=case["samples"].copy()
            y,z=chebyshev_transform(samples)
            self.compare(samples,case["overwritten"],"overwritten")
            self.compare(y,case["degree12"],"degree12")
            self.compare(z,case["degree24"],"degree24")
        for case in FIXTURE["tridiagonal"]:
            arrays=[case[key].copy() for key in ("c","d","e","rhs")]
            self.assertEqual(solve_tridiagonal(*arrays),case["status"])
            self.compare(arrays,case["overwritten"],"tridiagonal")

    def test_native_adaptive_oscillatory_integrals(self):
        for case in FIXTURE["oscillatory"]:
            with self.subTest(kind=case["kind"],frequency=case["frequency"],selector=case["selector"],limit=case["limit"]):
                cache=MomentCache(case["rows"])
                args={k:v for k,v in case.items() if k not in ("kind","rows","result")}
                result=asdict(integrate_oscillatory(callback(case["kind"]),cache=cache,**args))
                result["computed"]=cache.computed
                for key,expected in case["result"].items():
                    if key in ("evaluations","status","intervals","computed"):
                        self.assertEqual(result[key],expected,key)
                    else:
                        self.compare(result[key],expected,key)

    def test_native_fourier_cycles_and_extrapolation_history(self):
        for case in FIXTURE["fourier"]:
            with self.subTest(kind=case["kind"],frequency=case["frequency"],selector=case["selector"],cycle_limit=case["cycle_limit"]):
                args={k:v for k,v in case.items() if k not in ("kind","result","cycle_integrals","cycle_errors","cycle_statuses","history")}
                result=asdict(integrate_fourier(callback(case["kind"]),**args))
                for key,expected in case["result"].items():
                    if key in ("evaluations","status","cycles"):
                        self.assertEqual(result[key],expected,key)
                    else:
                        self.compare(result[key],expected,key)
                self.assertEqual(result["cycle_statuses"],case["cycle_statuses"])
                for key in ("cycle_integrals","cycle_errors","history"):
                    self.compare(result[key],case[key],key)

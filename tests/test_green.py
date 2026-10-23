import json
import math
from pathlib import Path
import unittest
from reasitic.green import (GreenLayers,propagation_constant,complex_tanh,reflection_imag,
                            oscillating_integrand,propagation_integrand,oscillating_kernel,reflection_kernel)


class GreenTests(unittest.TestCase):
    def test_native_eddy_kernels_and_nonfinite_classification(self):
        cases=json.loads((Path(__file__).parent/"fixtures/green.json").read_text())["cases"]
        for case in cases:
            with self.subTest(k=case["k"],frequency=case["frequency"],layers=(case["layer1"],case["layer2"],case["depth"]),height=case["height"],separation=case["separation"]):
                k,f=case["k"],case["frequency"]
                layers=GreenLayers(case["layer1"],case["layer2"],case["depth"])
                a,b=propagation_constant(k,f,layers.layer1),propagation_constant(k,f,layers.layer2)
                t=complex_tanh(complex(layers.depth*a.real,layers.depth*a.imag))
                result=dict(gamma_first=[a.real,a.imag],gamma_second=[b.real,b.imag],tanh=[t.real,t.imag],
                            reflection_imag=reflection_imag(k,f,layers.layer1),oscillating_integrand=oscillating_integrand(k,f,layers),
                            propagation_integrand=propagation_integrand(f,layers),
                            oscillating_kernel=oscillating_kernel(k,f,layers,case["height"],case["separation"]),
                            reflection_kernel=reflection_kernel(k,case["height"]))
                for key,value in result.items():
                    values=value if isinstance(value,list) else [value]
                    expected=case[key] if isinstance(case[key],list) else [case[key]]
                    for actual,reference in zip(values,expected):
                        if reference=="nan":
                            self.assertTrue(math.isnan(actual),key)
                        elif isinstance(reference,str):
                            self.assertEqual(actual,float(reference),key)
                        elif reference==0:
                            self.assertEqual(actual,0,key)
                        else:
                            floor=1e-300 if key=="reflection_kernel" or case["height"]==1 else 1e-14
                            self.assertAlmostEqual(actual,reference,delta=max(floor,abs(reference)*1e-12),msg=key)

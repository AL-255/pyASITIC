import json
from pathlib import Path
import unittest
from reasitic import Technology,build
from reasitic.solver import solve_impedance
from reasitic.eddy import configure_eddy
from reasitic.network import _join_for_pads


class EddyTests(unittest.TestCase):
    def test_native_nonfinite_joined_conductors_report_failure(self):
        cases=json.loads((Path(__file__).parent/"fixtures/eddy.json").read_text())["nonfinite_cases"]
        for case in cases:
            self.assertEqual(case["matrix"][0][1][0],"nan")
            tech=Technology.from_text(case["technology"])
            shape=_join_for_pads(build("wire",technology=tech,**case["first"]),build("wire",technology=tech,**case["second"]))
            with self.assertRaisesRegex(ValueError,"native eddy path produced a nonfinite impedance"):
                solve_impedance(shape,tech,1e9,eddy=True)

    def test_native_complete_eddy_lmat_matrices(self):
        cases=json.loads((Path(__file__).parent/"fixtures/eddy.json").read_text())["cases"]
        for case in cases:
            tech=Technology.from_text(case["technology"])
            shape=build(case["kind"],technology=tech,**case["parameters"])
            for f,mesh,key in ((1e9,{},"matrix_1ghz"),(2e9,dict(length_cell=50,width_cell=3,thickness_cell=.5),"matrix_fine_2ghz")):
                with self.subTest(kind=case["kind"],process=case["process"],frequency=f):
                    result=solve_impedance(shape,tech,f,eddy=True,**mesh)
                    self.assertTrue(result["eddy"])
                    self.assertEqual(len(result["matrix"]),len(case[key]))
                    for i,(row,expected) in enumerate(zip(result["matrix"],case[key])):
                        for j,(value,reference) in enumerate(zip(row,expected)):
                            for axis in range(2):
                                self.assertAlmostEqual(value[axis],reference[axis],delta=max(1e-8,abs(reference[axis])*1e-8),msg=f"{i},{j}/{axis}")
                    if f==2e9 and case["eddy_fine_2ghz"] is not None:
                        actual=result["eddy_details"]["matrix"]
                        for row,expected in zip(actual,case["eddy_fine_2ghz"]):
                            for value,reference in zip(row,expected):
                                self.assertAlmostEqual(value,reference,delta=max(1e-8,abs(reference)*1e-8))
                    if result["resistance_ohm"]<0:
                        self.assertTrue(any("negative total conductor" in warning for warning in result["warnings"]))

    def test_repeated_technology_eddy_layers_and_native_skip(self):
        cases=json.loads((Path(__file__).parent/"fixtures/eddy.json").read_text())["cases"]
        bicmos=Technology.from_text(next(c["technology"] for c in cases if c["process"]=="BiCMOS"))
        self.assertEqual(bicmos.eddy_layers,[0,1])
        state=configure_eddy(bicmos)
        self.assertEqual(state.layers.layer1,1000)
        self.assertEqual(state.layers.layer2,10)
        self.assertAlmostEqual(state.layers.depth,2e-6)
        tech=Technology.default();tech.eddy_layers=[]
        result=solve_impedance(build("square",technology=tech),tech,1e9,eddy=True)
        self.assertTrue(result["eddy_details"]["skipped"])
        self.assertTrue(any("No valid eddy" in warning for warning in result["warnings"]))

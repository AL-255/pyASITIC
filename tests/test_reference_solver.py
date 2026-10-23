import json
import math
from pathlib import Path
import struct
import unittest
from reasitic import Technology,build
from reasitic.solver import solve_impedance


class ReferenceSolverTests(unittest.TestCase):
    def test_connected_lmat_matrices(self):
        cases = json.loads((Path(__file__).parent/"fixtures/analysis.json").read_text())["cases"]
        tech = Technology.default()
        for case in cases:
            parameters = dict(case["parameters"])
            for key in ("gap","angle"):
                if key in parameters:
                    parameters[key]=struct.unpack("f",struct.pack("f",math.radians(parameters[key])))[0]*180/math.pi
            with self.subTest(kind=case["kind"],parameters=parameters):
                shape=build(case["kind"],technology=tech,**parameters)
                for frequency,options,key in [(1e9,{},"matrix_1ghz"),(2e9,dict(length_cell=50,width_cell=3,thickness_cell=.5),"matrix_fine_2ghz")]:
                    result=solve_impedance(shape,tech,frequency,**options)
                    expected=case[key]
                    self.assertEqual(len(result["matrix"]),len(expected))
                    for i,(row,reference) in enumerate(zip(result["matrix"],expected)):
                        for j,(z,e) in enumerate(zip(row,reference)):
                            for component in range(2):
                                self.assertAlmostEqual(z[component],e[component],delta=1e-8,msg=f"{key} matrix {i},{j} component {component}")

    def test_matrix_singularity_and_mesh_limit(self):
        tech=Technology.default()
        with self.assertRaisesRegex(ValueError,"filaments"):
            solve_impedance(build("square",technology=tech),tech,1e9,width_cell=.01,thickness_cell=.01)
        with self.assertRaisesRegex(ValueError,"metal segment"):
            solve_impedance(build("via",technology=tech),tech,1e9)

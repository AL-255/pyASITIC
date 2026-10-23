import json
import math
from pathlib import Path
import unittest
from reasitic import Technology,build_device,inductance_estimate,resistance_dc,resistance_hf,solve_impedance


class Transformer3DTests(unittest.TestCase):
    def test_connected_reference_sessions(self):
        cases=json.loads((Path(__file__).parent/"fixtures/transformer3d.json").read_text())["cases"]
        technology=Technology.default()
        names=[metal.name for metal in technology.metals]
        for case in cases:
            with self.subTest(parameters=case["parameters"]):
                for shape in build_device("transformer3d",technology=technology,**case["parameters"]):
                    expected=case["geometry"][shape.name]
                    self.assertEqual(len(shape.segments),len(expected))
                    for index,(segment,fields) in enumerate(zip(shape.segments,expected)):
                        self.assertEqual(names[segment.metal],fields["METAL"])
                        actual=dict(AX=segment.outer_start[0],AY=segment.outer_start[1],BX=segment.outer_end[0],BY=segment.outer_end[1],
                                    CX=segment.inner_start[0],CY=segment.inner_start[1],DX=segment.inner_end[0],DY=segment.inner_end[1],
                                    PORT1X=segment.start[0],PORT1Y=segment.start[1],PORT2X=segment.end[0],PORT2Y=segment.end[1],W=segment.width,T=segment.thickness)
                        for key,value in actual.items():
                            self.assertAlmostEqual(value,fields[key],delta=5.1e-7,msg=f"{shape.name} segment {index} {key}")
                    target=case["inductance"][shape.name]
                    tolerance=.51*10**(math.floor(math.log10(abs(target)))-5)
                    self.assertAlmostEqual(inductance_estimate(shape,technology),target,delta=tolerance)
                    self.assertAlmostEqual(resistance_dc(shape,technology),case["dc"][shape.name],delta=5.1e-7)
                    self.assertAlmostEqual(resistance_hf(shape,technology,2e9),case["hf"][shape.name],delta=5.1e-7)
                    matrix=solve_impedance(shape,technology,1e9)["matrix"]
                    target_matrix=case["matrices"][shape.name]
                    self.assertEqual(len(matrix),len(target_matrix))
                    for i,(row,reference) in enumerate(zip(matrix,target_matrix)):
                        for j,(value,expected_value) in enumerate(zip(row,reference)):
                            for axis in range(2):
                                self.assertAlmostEqual(value[axis],expected_value[axis],delta=1e-8,msg=f"{shape.name} matrix {i},{j} component {axis}")

    def test_creator_aliases_and_spacing_validation(self):
        technology=Technology.default()
        reference=build_device("transformer3d",technology=technology)
        for alias in ("3DTrans","3DMIRRORTRANS","Trans3D","TransMIM","mirror_transformer3d"):
            self.assertEqual([s.to_dict() for s in reference],[s.to_dict() for s in build_device(alias,technology=technology)])
        with self.assertRaisesRegex(ValueError,"Spacing too small"):
            build_device("transformer3d",technology=technology,spacing=1)
        with self.assertRaisesRegex(ValueError,"distinct metals"):
            build_device("transformer3d",technology=technology,metal="M4",secondary_metal="M4")

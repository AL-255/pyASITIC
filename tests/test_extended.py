import json
import struct
from pathlib import Path
import unittest
from reasitic.extended import stamp_extended_node_columns,solve_extended_node_equations,solve_pix
from reasitic import Technology,build
from reasitic.bridge import handle


class ExtendedTests(unittest.TestCase):
    # Every raw PiX Y/model/S/resonance record, including the earlier separate
    # square/polygon cases, is covered by test_pi_sessions's complete gate.
    def test_native_column_stamps_and_node_solutions(self):
        cases=json.loads((Path(__file__).parent/"fixtures/extended_nodes.json").read_text())["cases"]
        for case in cases:
            with self.subTest(n=len(case["cap"]),stride=case["stride"],stamp_only=case["stamp_only"]):
                cap,ind=([[complex(*z) for z in row] for row in case[key]] for key in ("cap","ind"))
                self.assertTrue(case["padding_untouched"])
                for matrix,key in ((cap,"SC"),(ind,"SZ")):
                    actual=stamp_extended_node_columns(matrix)
                    self.assertEqual([[[z.real,z.imag] for z in row] for row in actual],case[key])
                    for row,reference in zip(actual,case[key]):
                        for z,values in zip(row,reference):
                            for value,target in zip((z.real,z.imag),values):self.assertEqual(struct.pack('d',value),struct.pack('d',target),"Native stamp bits, including signed zero")
                if case["stamp_only"]:continue
                y,state=solve_extended_node_equations(cap,ind)
                values=[y[key] for key in ("y22","y21","y12","y11")]
                for actual,expected in zip(values,case["Y"]):
                    self.assertAlmostEqual(actual.real,expected[0],delta=max(1e-12,abs(expected[0])*1e-10))
                    self.assertAlmostEqual(actual.imag,expected[1],delta=max(1e-12,abs(expected[1])*1e-10))
                for actual,expected in zip(state["solutions"][0],case["V"]+case["I"]):
                    for value,reference in zip((actual.real,actual.imag),expected):
                        self.assertAlmostEqual(value,reference,delta=max(1e-12,abs(reference)*1e-10))

    def test_invalid_node_dimensions(self):
        with self.assertRaisesRegex(ValueError,"nonempty square"):
            stamp_extended_node_columns([])
        with self.assertRaisesRegex(ValueError,"match"):
            solve_extended_node_equations([[1j]],[])
        with self.assertRaisesRegex(ValueError,"finite"):
            stamp_extended_node_columns([[complex(float("nan"),0)]])

    def test_complete_native_pix_sessions(self):
        cases=json.loads((Path(__file__).parent/"fixtures/pix.json").read_text())["cases"]
        def matrix(actual,expected,floor,label):
            self.assertEqual(len(actual),len(expected),label)
            for i,(row,reference) in enumerate(zip(actual,expected)):
                self.assertEqual(len(row),len(reference),label)
                for j,(cell,values) in enumerate(zip(row,reference)):
                    for axis,(value,target) in enumerate(zip(cell,values)):
                        self.assertAlmostEqual(value,target,delta=max(floor,abs(target)*1e-8),msg=f"{label} {i},{j}/{axis}")
        for case in cases:
            with self.subTest(kind=case["kind"],process=case["process"],eddy=case["eddy"],mesh=case["mesh"]):
                tech=Technology.from_text(case["technology"])
                shape=build(case["kind"],technology=tech,**case["parameters"])
                ground=build("wire",technology=tech,**case["ground"]["parameters"]) if case["ground"] else None
                result=solve_pix(shape,tech,case["frequency_hz"],ground=ground,eddy=case["eddy"],include_matrices=True,**case["mesh"])
                self.assertEqual(len(result["filament_impedance_diagonal"]),len(case["filament_impedance_diagonal"]))
                for value,reference in zip(result["filament_impedance_diagonal"],case["filament_impedance_diagonal"]):
                    for actual,target in zip(value,reference):self.assertAlmostEqual(actual,target,delta=max(1e-14,abs(target)*1e-13),msg="Native filament self impedance")
                for key,floor in (("capacitance_matrix",1e-16),("inductive_impedance_matrix",1e-8),("currents_first",1e-10),("voltages_first",1e-10)):
                    matrix(result[key],case[key],floor,key)
                matrix(result["admittance_matrix"],case["direct_admittance_matrix"],1e-12,"Native PIX RHS Y")
                if case is cases[0]:
                    request={key:case[key] for key in ("kind","parameters","technology","ground","eddy","mesh","frequency_hz")}
                    api=handle(dict(action="pix",include_matrices=True,**request))
                    self.assertEqual(api["admittance_matrix"],result["admittance_matrix"])
                if case["admittance_matrix"] is not None:
                    matrix(result["admittance_matrix"],case["admittance_matrix"],1e-10,"Y")
                    matrix(result["scattering_matrix"],case["scattering_matrix"],1e-10,"S")
                p=result["pi"]
                for key,target in zip(("q_first","q_second","q_differential"),case["qualities"]):
                    if isinstance(target,str):self.assertIsNone(p[key])
                    else:self.assertAlmostEqual(p[key],target,delta=max(1e-9,abs(target)*1e-8),msg=key)
                keys=[("inductance_h",1e9),("resistance_ohm",1),("capacitance_first_f",1e15),("resistance_first_ohm",1),
                      ("capacitance_second_f",1e15),("resistance_second_ohm",1),("resonant_frequency_hz",1e-9)]
                for (key,scale),target in zip(keys,case["metrics"]):
                    if isinstance(target,str):self.assertIsNone(p[key])
                    else:self.assertAlmostEqual(p[key]*scale,target,delta=max(1e-9,abs(target)*1e-8),msg=key)
                for key,reference in zip(("input_impedance_first_ohm","input_impedance_second_ohm","differential_impedance_ohm"),case["input_impedances"]):
                    for actual,target in zip(result[key],reference):self.assertAlmostEqual(actual,target,delta=max(1e-8,abs(target)*1e-8),msg=key)

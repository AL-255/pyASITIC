import json
import math
from pathlib import Path
import re
import unittest
from reasitic import Technology,build
from reasitic.network import solve_pi2,solve_node_equations,convert_scattering
from reasitic.bridge import request_json


CASES=json.loads((Path(__file__).parent/"fixtures/network.json").read_text())["cases"]


class NetworkTests(unittest.TestCase):
    def assert_matrix(self,actual,expected,label):
        self.assertEqual(len(actual),len(expected),label)
        for i,(row,reference_row) in enumerate(zip(actual,expected)):
            self.assertEqual(len(row),len(reference_row),label)
            for j,(value,reference) in enumerate(zip(row,reference_row)):
                for axis in range(2):
                    self.assertAlmostEqual(value[axis],reference[axis],delta=max(1e-10,abs(reference[axis])*1e-8),msg=f"{label} {i},{j} axis {axis}")

    def test_native_distributed_pi2(self):
        for case in sorted(CASES,key=lambda item:(item["process"],item["frequency_hz"])):
            with self.subTest(kind=case["kind"],mesh=case["mesh"],ground=bool(case["ground"])):
                tech=Technology.from_text(case["technology"])
                shape=build(case["kind"],technology=tech,**case["parameters"])
                ground=build(case["ground"]["kind"],technology=tech,**case["ground"]["parameters"]) if case["ground"] else None
                result=solve_pi2(shape,tech,case["frequency_hz"],ground=ground,include_matrices=True,**case["mesh"])
                for key in ("capacitance_matrix","inductive_admittance_matrix","nodal_capacitance_matrix","admittance_matrix","scattering_matrix"):
                    self.assert_matrix(result[key],case[key],key)
                # Printed native values carry only 3 significant digits (Q and
                # resonance use fixed decimals), independent of Python's model.
                stdout=case["stdout"]
                qualities=re.search(r"Q =\s*([^,]+),([^,]+),([^\n]+)",stdout)
                for key,expected in zip(("q_first","q_second","q_differential"),map(float,qualities.groups())):
                    self.assertAlmostEqual(result["pi"][key],expected,delta=.000501,msg=key)
                fields=re.search(r"L\s*=\s*(\S+) nH\s*R\s*=\s*(\S+)\s+Cs1=\s*(\S+) fF\s*Rs1=\s*(\S+)\s+Cs2=\s*(\S+) fF\s*Rs2=\s*(\S+)\s+f_res =\s*(\S+)GHz",stdout)
                for token,key,scale in zip(fields.groups(),("inductance_h","resistance_ohm","capacitance_first_f","resistance_first_ohm","capacitance_second_f","resistance_second_ohm","resonant_frequency_hz"),(1e-9,1,1e-15,1,1e-15,1,1e9)):
                    expected=float(token)
                    tolerance=.00501 if key=="resonant_frequency_hz" else .00501*abs(expected) if expected else 1e-20
                    self.assertAlmostEqual(result["pi"][key]/scale,expected,delta=tolerance,msg=key)
                shunts=re.findall(r"The shunt resistance is (\S+) Ohms",stdout)
                for key,token in zip(("shunt_single_ohm","shunt_differential_ohm"),shunts):
                    expected=float(token)
                    if math.isfinite(expected):
                        self.assertAlmostEqual(result["pi"][key],expected,delta=max(5.1e-7,abs(expected)*1e-7),msg=key)
                    else:
                        self.assertIsNone(result["pi"][key],key)

    def test_native_node_equations_and_scattering_in_isolation(self):
        # Feed native snapshots directly so an end-to-end pass cannot conceal
        # compensating errors in the CAP, inductive and nodal stages.
        for case in CASES:
            with self.subTest(kind=case["kind"],mesh=case["mesh"]):
                matrix=lambda key:[[complex(*z) for z in row] for row in case[key]]
                y,nodal=solve_node_equations(matrix("capacitance_matrix"),matrix("inductive_admittance_matrix"))
                actual=[[y["y22"],y["y21"]],[y["y12"],y["y11"]]]
                pairs=lambda m:[[[z.real,z.imag] for z in row] for row in m]
                # Snapshot files have 10 significant digits, so the isolated
                # node comparison has a larger absolute rounding budget.
                for row,expected in zip(actual,case["admittance_matrix"]):
                    for value,reference in zip(row,expected):
                        self.assertLess(abs(value-complex(*reference)),2e-8)
                native=matrix("admittance_matrix")
                native_y=dict(y22=native[0][0],y21=native[0][1],y12=native[1][0],y11=native[1][1])
                self.assert_matrix(pairs(convert_scattering(native_y)),case["scattering_matrix"],"native S")

    def test_invalid_mesh_and_mismatched_nodes(self):
        tech=Technology.default()
        shape=build("wire",length=40,width=5,x=10,y=20,technology=tech)
        for sizes in (dict(length_cell=0),dict(capacitance_width_cell=math.nan),dict(thickness_cell=-1)):
            with self.assertRaisesRegex(ValueError,"finite and positive"):
                solve_pi2(shape,tech,1e9,**sizes)
        with self.assertRaisesRegex(ValueError,"matching"):
            solve_node_equations([[1j]],[[1,2],[3,4]])

    def test_json_bridge_units_and_undefined_metric(self):
        case=CASES[0]
        result=json.loads(request_json(json.dumps(dict(action="pi2",kind=case["kind"],parameters=case["parameters"],
                                                      technology=case["technology"],frequency_hz=case["frequency_hz"],mesh=case["mesh"]))))["result"]
        self.assert_matrix(result["admittance_matrix"],case["admittance_matrix"],"bridge Y")
        self.assertIsNone(result["pi"]["shunt_differential_ohm"])
        self.assertEqual(result["reference_impedance_ohm"],50)
        self.assertFalse(result["eddy"])

import json
import math
import struct
from pathlib import Path
import unittest
from reasitic.transformer import extract_transformer_equivalent,invert_transformer_admittance,solve_transformer,MODEL_KEYS
from reasitic.network import solve_node_equations,_complex_matrix,_pairs
from reasitic.bridge import handle,_shape
from reasitic import Technology

FIXTURE=Path(__file__).parent/"fixtures/transformer_network.json"

class TransformerTests(unittest.TestCase):
    def near(self,actual,target,floor=1e-12,relative=1e-10):
        if isinstance(target,list):
            self.assertEqual(len(actual),len(target))
            for a,b in zip(actual,target):self.near(a,b,floor,relative)
        elif isinstance(target,str):
            if target=="nan":self.assertTrue(math.isnan(actual))
            else:self.assertEqual(actual,float(target))
        else:self.assertAlmostEqual(actual,target,delta=max(floor,abs(target)*relative))

    def test_original_conversion_and_folded_nodes(self):
        for i,c in enumerate(json.loads(FIXTURE.read_text())["rules"]):
            with self.subTest(case=i):
                if "input" in c:y=dict(zip(("y11","y12","y21","y22"),(complex(float(z[0]),float(z[1])) for z in c["input"])))
                else:
                    y,nodal=solve_node_equations(*(_complex_matrix(c[k]) for k in ("capacitance","inductance")))
                    self.near([v for row in _pairs(nodal) for z in row for v in z],c["C"])
                self.near([v for key in ("y11","y12","y21","y22") for v in (y[key].real,y[key].imag)],c["Y"])
                inverse=invert_transformer_admittance(y)
                self.near([v for key in ("z11","z12","z21","z22") for v in (inverse[key].real,inverse[key].imag)],c["I"],1e-300)
                m,z=extract_transformer_equivalent(y,c["frequency_hz"])
                self.near([m[k] for k in MODEL_KEYS],c["M"],1e-300)
                self.near([v for key in ("z11","z12","z21","z22") for v in (z[key].real,z[key].imag)],c["Z"],1e-300)

    def test_original_complete_coupled_sessions(self):
        for i,c in enumerate(json.loads(FIXTURE.read_text())["cases"]):
            with self.subTest(case=i,kind=c["first"]["kind"],reference=c["reference_mode"],eddy=c["eddy"]):
                tech=Technology.from_text(c["technology"]);first,second=(_shape(c[k],tech) for k in ("first","second"))
                before=[first.to_dict(),second.to_dict()];ground=_shape(c["ground"],tech) if c["ground"] else None
                if c["nonfinite_model"]:
                    # The original emits all-NaN models for these invalid contact
                    # or inductive histories. Keep the bounded solver diagnostic.
                    with self.assertRaisesRegex(ValueError,"contact collapses|nonfinite inductive kernel"):
                        solve_transformer(first,second,tech,c["frequency_hz"],ground=ground,termination_ohm=c["termination_ohm"],eddy=c["eddy"],**c["mesh"])
                    continue
                r=solve_transformer(first,second,tech,c["frequency_hz"],ground=ground,termination_ohm=c["termination_ohm"],eddy=c["eddy"],include_matrices=True,**c["mesh"])
                self.assertEqual(before,[first.to_dict(),second.to_dict()],"Caller windings changed")
                for key in ("admittance_matrix","scattering_matrix","nodal_capacitance_matrix"):
                    self.near(r[key],c[key],1e-10 if key!="nodal_capacitance_matrix" else 1e-16,1e-8)
                keys=("first_inductance_h","first_resistance_ohm","second_inductance_h","second_resistance_ohm","mutual_h","coupling","ground_resistance_ohm")
                scales=(1e9,1,1e9,1,1e9,1,1)
                for key,scale,target in zip(keys,scales,c["metrics"]):
                    if isinstance(target,str):self.assertIsNone(r["model"][key])
                    else:self.near(r["model"][key]*scale,target,1e-9,1e-8)
                if i==3:
                    # This forced-reference wire amplified contact roundoff
                    # in its ground resistance. Require the original SI
                    # stores directly, without display-unit conversion.
                    y,z=r['admittance_matrix'],r['impedance_matrix']
                    actual=[v for cell in (y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1])for v in cell]
                    actual.extend(r['model'][key]for key in MODEL_KEYS)
                    self.assertEqual([struct.pack('<d',v).hex()for v in actual],c['raw_output_bits'])
                if i in (0,16):
                    request={key:c[key] for key in ("first","second","technology","frequency_hz","ground","mesh","eddy","termination_ohm")}
                    self.assertEqual(handle(dict(action="calctrans",**request))["model"],r["model"])

    def test_invalid_inputs_and_paired_request(self):
        tech=Technology.default();a=_shape(dict(kind="wire",parameters=dict(name="A",length=10,width=2)),tech);b=_shape(dict(kind="wire",parameters=dict(name="B",length=10,width=2,y=10)),tech)
        for f in (0,-1,math.inf,math.nan):
            with self.assertRaisesRegex(ValueError,"finite and positive"):solve_transformer(a,b,tech,f)
        with self.assertRaisesRegex(ValueError,"termination must be finite"):solve_transformer(a,b,tech,1e9,termination_ohm=math.inf)
        with self.assertRaisesRegex(ValueError,"two windings"):handle(dict(action="calctrans",kind="wire"))
        with self.assertRaisesRegex(ValueError,"two windings"):handle(dict(action="calctrans",kind="transformer",first_winding=0,second_winding=0))

import copy,json,math,struct,unittest
from pathlib import Path
from reasitic.mesh_counts import counts
from reasitic.solver import discretize,filament_counts
from reasitic.filament import record,filament_records
from reasitic import Technology,build,solve_impedance
from reasitic.mesh import mesh_information
from reasitic.bridge import handle


class MeshTests(unittest.TestCase):
    def test_count_and_fit_match_electrical_mesh(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=400,width=6,metal="M5",x=20,y=50)
        before=copy.deepcopy(shape.to_dict());cells=dict(length_cell=20,width_cell=.5,thickness_cell=.5,capacitance_length_cell=1000,capacitance_width_cell=1000)
        plan=mesh_information(shape,tech,cells)
        self.assertEqual(plan["filaments"],480);self.assertFalse(plan["within_limit"])
        self.assertEqual(mesh_information(shape,tech,dict(cells,max_width_cells=9))["filaments"],360)
        fitted=mesh_information(shape,tech,cells,fit=True)
        self.assertTrue(fitted["changed"]);self.assertEqual(fitted["filaments"],60)
        self.assertEqual(fitted["mesh"]["max_width_cells"],500)
        for key in ("capacitance_length_cell","capacitance_width_cell"):self.assertEqual(fitted["mesh"][key],cells[key])
        result=solve_impedance(shape,tech,1e9,**{k:fitted["mesh"][k] for k in ("length_cell","width_cell","thickness_cell")})
        self.assertEqual(result["filaments"],fitted["filaments"])
        self.assertEqual(before,shape.to_dict());self.assertEqual(cells["length_cell"],20)
        self.assertFalse(mesh_information(shape,tech,fitted["mesh"],fit=True)["changed"])

    def test_native_pad_and_explicit_winding_mesh_counts(self):
        wire=dict(kind="wire",parameters=dict(name="A",length=40,width=5,metal="M4",x=10,y=20))
        other=dict(kind="wire",parameters=dict(name="B",length=30,width=5,metal="M3",x=20,y=50))
        cells=dict(length_cell=1000,width_cell=1000,thickness_cell=1000)
        paired=dict(action="mesh",model="calctrans",first=wire,second=other,mesh=cells)
        self.assertEqual(handle(paired)["filaments"],2)
        self.assertEqual(handle(dict(paired,ground=wire))["filaments"],10)
        pads={key:dict(kind="wire",parameters=dict(name=key,length=20,width=5,metal="M4")) for key in ("first_pad","second_pad")}
        self.assertEqual(handle(dict(action="mesh",model="pi4",**wire,mesh=cells,**pads))["filaments"],19)

    def test_original_retained_counts(self):
        fixture=json.loads((Path(__file__).parent/"fixtures/filament_counts_original.json").read_text())
        self.assertEqual(fixture["control_before"],fixture["control_after"])
        for i,case in enumerate(fixture["cases"]):
            w,t=counts(*struct.unpack("<7d",bytes.fromhex(case["input_bits"])))
            total=(w*t+2**31)%2**32-2**31
            self.assertEqual([w,t,total,1,257],case["output"],i)

    def test_complete_original_maxnw_sessions(self):
        fixture=json.loads((Path(__file__).parent/"fixtures/mesh_sessions_original.json").read_text())
        tech=Technology.from_text(fixture["technology"])
        shape=build("wire",technology=tech,name="A",length=40,width=20,metal="M5",x=40,y=40,native_keyword=True)
        for case in fixture["cases"]:
            with self.subTest(maximum=case["maximum"]):
                self.assertEqual(case["signal"],0);self.assertEqual(case["pending"],0)
                self.assertEqual(len(case["counts"]),1);self.assertEqual(len(case["reports"]),1)
                c=case["counts"][0];cap=c["maxnw"]
                self.assertEqual(cap,500 if case["maximum"] is None else case["maximum"])
                self.assertEqual(c["control"],0x37f)
                width,thickness=(struct.unpack("<d",bytes.fromhex(c[k+"_cell_bits"]))[0]for k in("width","thickness"))
                mesh=discretize(shape,1000,1000);rows=[];sizes=[]
                for segment in mesh.segments:
                    w,t=filament_counts(segment,width,thickness,cap);sizes.append((w,t))
                    rows.extend(record(segment,shape.origin,i,j,w,t,width,cap,tech)for i in range(w)for j in range(t))
                self.assertEqual([w for w,t in sizes],c["width"]);self.assertEqual([t for w,t in sizes],c["thickness"])
                self.assertEqual(sum(w*t for w,t in sizes),c["total"])
                actual=filament_records(rows)
                # Compare every original construction, including repeated pair operands.
                for source in case["filaments"]:
                    expected=(*struct.unpack("<8d",bytes.fromhex(source["bits"])),source["metal"])
                    def equal(row):
                        return all(math.isnan(a) if math.isnan(b) else struct.pack("<d",a)==struct.pack("<d",b)for a,b in zip(row,expected))
                    self.assertTrue(any(equal(row)for row in actual),source)
                if cap==1:
                    self.assertTrue(math.isnan(struct.unpack("<d",bytes.fromhex(case["reports"][0]["bits"][:16]))[0]))
                    with self.assertRaisesRegex(ValueError,"Native edge mesh"):solve_impedance(shape,tech,1e9,width_cell=width,thickness_cell=thickness,max_width_cells=cap)
                else:
                    options={}if case["maximum"] is None else dict(max_width_cells=cap)
                    result=solve_impedance(shape,tech,1e9,width_cell=width,thickness_cell=thickness,**options)
                    self.assertEqual(struct.pack("<2d",result["inductance_h"],result["resistance_ohm"]).hex(),case["reports"][0]["bits"])

    def test_maxnw_default_override_and_fit_preservation(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=40,width=20,metal="M5",x=40,y=40)
        mesh=dict(length_cell=1000,width_cell=1,thickness_cell=1000)
        self.assertEqual(mesh_information(shape,tech,mesh,model="lmat")["filaments"],20)
        self.assertEqual(solve_impedance(shape,tech,1e9,**mesh)["filaments"],20)
        for cap in (1,9,10,500,65536,2147483647):
            self.assertEqual(mesh_information(shape,tech,dict(mesh,max_width_cells=cap),model="lmat")["filaments"],min(20,cap))
        fitted=mesh_information(shape,tech,dict(mesh,length_cell=1,max_width_cells=10),model="lmat",fit=True)
        self.assertTrue(fitted["within_limit"]);self.assertEqual(fitted["mesh"]["max_width_cells"],10)
        for value in (0,-1,1.5,True,float("nan"),float("inf"),2147483648):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,"MAXNW"):mesh_information(shape,tech,dict(mesh,max_width_cells=value))
                with self.assertRaisesRegex(ValueError,"MAXNW"):solve_impedance(shape,tech,1e9,**mesh,max_width_cells=value)

    def test_invalid_and_irreducible_meshes(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=40,width=5)
        for value in (0,-1,float("nan"),float("inf")):
            with self.assertRaisesRegex(ValueError,"finite and positive"):mesh_information(shape,tech,dict(width_cell=value))
        shape.segments=[copy.deepcopy(shape.segments[0]) for _ in range(300)]
        with self.assertRaisesRegex(ValueError,"coarsest.*300 filaments"):mesh_information(shape,tech,{},fit=True)
        with self.assertRaisesRegex(ValueError,"Unknown mesh analysis"):mesh_information(shape,tech,{},model="invalid")

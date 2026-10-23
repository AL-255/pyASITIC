import copy,unittest
from reasitic import Technology,build,solve_impedance
from reasitic.mesh import mesh_information
from reasitic.bridge import handle


class MeshTests(unittest.TestCase):
    def test_count_and_fit_match_electrical_mesh(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=400,width=6,metal="M5",x=20,y=50)
        before=copy.deepcopy(shape.to_dict());cells=dict(length_cell=20,width_cell=.5,thickness_cell=.5,capacitance_length_cell=1000,capacitance_width_cell=1000)
        plan=mesh_information(shape,tech,cells)
        self.assertEqual(plan["filaments"],360);self.assertFalse(plan["within_limit"])
        fitted=mesh_information(shape,tech,cells,fit=True)
        self.assertTrue(fitted["changed"]);self.assertEqual(fitted["filaments"],60)
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

    def test_invalid_and_irreducible_meshes(self):
        tech=Technology.default();shape=build("wire",technology=tech,length=40,width=5)
        for value in (0,-1,float("nan"),float("inf")):
            with self.assertRaisesRegex(ValueError,"finite and positive"):mesh_information(shape,tech,dict(width_cell=value))
        shape.segments=[copy.deepcopy(shape.segments[0]) for _ in range(300)]
        with self.assertRaisesRegex(ValueError,"coarsest.*300 filaments"):mesh_information(shape,tech,{},fit=True)
        with self.assertRaisesRegex(ValueError,"Unknown mesh analysis"):mesh_information(shape,tech,{},model="invalid")

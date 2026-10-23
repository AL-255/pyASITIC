import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from reasitic import Technology,build,write_gds,resistance_dc
from reasitic.presets import catalogue,load_preset,identify,DIRECTORY
from reasitic.bridge import handle,request_json
from reasitic.network import solve_pi2


class PresetTests(unittest.TestCase):
    def test_complete_published_stack_surface_and_nominal_resistance(self):
        presets=catalogue()
        self.assertEqual(len(presets),45)
        self.assertEqual({p["section"] for p in presets},{f"3.{i}" for i in range(1,46)})
        self.assertEqual(sum(len(p["variants"]) for p in presets),73)
        self.assertEqual(len({p["id"] for p in presets}),45)
        expected={(n,k,mim) for n in range(3,7) for k in (6,9,11,30) for mim in (("none","A") if n==3 else ("none","A","B"))}|{(2,30,"none")}
        self.assertEqual({(p["routing_metals"],p["top_metal_ka"],p["mim"]) for p in presets},expected)
        for preset in presets:
            for density in preset["variants"]:
                with self.subTest(preset=preset["id"],density=density):
                    tech=Technology.from_text(load_preset(preset["id"],density))
                    self.assertEqual(identify(tech)["id"],preset["id"])
                    for metal in tech.metals:
                        wire=build("wire",technology=tech,length=100,width=5,metal=metal.name)
                        nominal=.18 if metal.name=="MIM" else {6:.06,9:.04,11:.04,30:.0083}[preset["top_metal_ka"]] if metal.name==f"M{preset['routing_metals']}" else .09
                        self.assertAlmostEqual(resistance_dc(wire,tech),20*nominal,places=12)
                    self.assertTrue(all(tech.metals[v.bottom].height<tech.metals[v.top].height for v in tech.vias))
                    self.assertEqual(tech.substrate[2]["eps"],7)
                    self.assertEqual(tech.substrate[3]["eps"],1)

    def test_independent_cross_section_dimensions_and_mim_placement(self):
        # Read directly from sections 3.1, 3.17, 3.39, 3.43, 3.45 drawings.
        expected=[("gf180-1p3m-6ka-no-mim",[.86,2.01,3.16],.7025,4.5625),
                  ("gf180-1p4m-6ka-mim-b",[.86,2.01,3.16,3.752,4.61],.7025,6.0125),
                  ("gf180-1p5m-11ka-mim-a",[.86,2.01,2.602,3.46,4.61,5.76],1.1925,8.1525),
                  ("gf180-1p5m-11ka-mim-b",[.86,2.01,3.16,4.31,4.902,5.76],1.1925,8.1525),
                  ("gf180-1p2m-30ka-no-mim",[.86,2.01],3,5.31)]
        for identifier,heights,thickness,oxide_top in expected:
            tech=Technology.from_text(load_preset(identifier))
            self.assertEqual([m.height for m in tech.metals],heights)
            self.assertEqual(tech.metals[-1].thickness,thickness)
            self.assertEqual(tech.substrate[1]["t"],oxide_top)
        a=Technology.from_text(load_preset("gf180-1p5m-11ka-mim-b",1))
        self.assertEqual(a.metals[a.metal_index("MIM")].height,4.922)

    def test_json_selection_overrides_and_project_text_roundtrip(self):
        self.assertEqual(len(handle(dict(action="init"))["presets"]),46)
        for density in (1,1.5):
            response=handle(dict(action="technology",preset="gf180-1p6m-9ka-mim-b",mim_density=density,substrate_rho=15,substrate_thickness=300))
            self.assertEqual(response["technology"]["substrate"][0],dict(t=300,rho=15,eps=11.9))
            restored=handle(dict(action="init",technology=response["text"]))
            self.assertEqual(restored["technology"],response["technology"])
            self.assertEqual(restored["preset"],response["preset"])
        for request in (dict(preset="missing"),dict(preset="gf180-1p3m-6ka-mim-a",mim_density=2),
                        dict(preset="gf180-1p3m-6ka-no-mim",substrate_rho=0),dict(preset="gf180-1p3m-6ka-no-mim",substrate_thickness=math.inf)):
            self.assertIn("error",json.loads(request_json(json.dumps(dict(action="technology",**request)))))

    @unittest.skipUnless(importlib.util.find_spec("gdstk"),"Install gdstk for independent GDS readback")
    def test_foundry_layer_map_and_override(self):
        import gdstk
        tech=Technology.from_text(load_preset("gf180-1p6m-11ka-mim-b"))
        with tempfile.TemporaryDirectory() as directory:
            for name,layer in (("M1",34),("M2",36),("M3",42),("M4",46),("M5",81),("M6",53),("MIM",75)):
                shape=build("wire",technology=tech,length=20,width=5,metal=name)
                path=Path(directory)/"wire.gds";path.write_bytes(write_gds(shape,tech))
                self.assertEqual({(p.layer,p.datatype) for p in gdstk.read_gds(path).cells[0].polygons},{(layer,0)})
            shape=build("via",technology=tech,via="VIA5",nx=4,ny=4)
            path.write_bytes(write_gds(shape,tech));polygons=gdstk.read_gds(path).cells[0].polygons
            self.assertEqual({p.layer for p in polygons},{81,53,82})
            self.assertEqual(len([p for p in polygons if p.layer==82]),16)
            path.write_bytes(write_gds(shape,tech,{"VIA5":(123,9)}))
            self.assertIn((123,9),{(p.layer,p.datatype) for p in gdstk.read_gds(path).cells[0].polygons})

    def test_native_gf180_network_sessions(self):
        for case in json.loads((Path(__file__).parent/"fixtures/gf180_network.json").read_text())["cases"]:
            with self.subTest(preset=case["preset"]):
                self.assertEqual((DIRECTORY/case["filename"]).read_text(),case["technology"])
                tech=Technology.from_text(case["technology"]);shape=build(case["kind"],technology=tech,**case["parameters"])
                result=solve_pi2(shape,tech,case["frequency_hz"],include_matrices=True)
                for key in ("capacitance_matrix","inductive_admittance_matrix","admittance_matrix","scattering_matrix"):
                    self.assertEqual(len(result[key]),len(case[key]))
                    for row,expected in zip(result[key],case[key]):
                        for pair,target in zip(row,expected):
                            for value,reference in zip(pair,target):self.assertAlmostEqual(value,reference,delta=max(1e-16 if key=="capacitance_matrix" else 1e-10,abs(reference)*1e-8),msg=key)

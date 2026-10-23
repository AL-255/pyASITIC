"""Independent reader checks, enabled in CI with gdstk installed."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from reasitic import Technology,build,build_device,write_gds
from reasitic.gds import layout_polygons


@unittest.skipUnless(importlib.util.find_spec("gdstk"),"Install gdstk for independent stream validation")
class GdsTests(unittest.TestCase):
    def test_round_trip_all_generators(self):
        import gdstk
        tech=Technology.default()
        for kind in ("square","polygon","symmetric_square","symmetric_polygon","wire","capacitor","via","ring","multimetal"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                shape=build(kind,technology=tech,x=19.25,y=-7.5,metal="M4",exit_metal="M3",angle=32)
                destination=Path(directory)/"layout.gds"
                destination.write_bytes(write_gds(shape,tech))
                library=gdstk.read_gds(destination)
                self.assertAlmostEqual(library.unit,1e-6,places=15)
                self.assertAlmostEqual(library.precision,1e-9,places=18)
                self.assertEqual(len(library.cells),1)
                polygons=library.cells[0].polygons
                expected=list(layout_polygons(shape,tech))
                self.assertEqual(len(polygons),len(expected))
                for actual,(index,points) in zip(polygons,expected):
                    self.assertEqual(actual.layer,index+1 if index<len(tech.metals) else 100+index-len(tech.metals))
                    self.assertEqual(actual.datatype,0)
                    for p,q in zip(actual.points,points):
                        for axis in range(2):
                            self.assertAlmostEqual(p[axis],q[axis]+shape.origin[axis],delta=.000501)

    def test_layer_map_and_via_cut_area(self):
        import gdstk
        tech=Technology.default()
        shape=build("via",technology=tech,nx=3,ny=4,via="VIA1")
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/"via.gds"
            destination.write_bytes(write_gds(shape,tech,{"VIA1":(42,7)}))
            cuts=[p for p in gdstk.read_gds(destination).cells[0].polygons if p.layer==42]
            self.assertEqual(len(cuts),12)
            self.assertTrue(all(p.datatype==7 for p in cuts))
            self.assertAlmostEqual(sum(p.area() for p in cuts),12*.5**2)

    def test_paired_windings_export_together(self):
        import gdstk
        tech=Technology.default()
        for kind in ("transformer","balun"):
            shapes=build_device(kind,technology=tech,turns=3 if kind=="balun" else 1.5,
                                metal="M4",exit_metal="M3",x=123,y=47)
            expected=[(shape,index,points) for shape in shapes for index,points in layout_polygons(shape,tech)]
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                destination=Path(directory)/"pair.gds"
                destination.write_bytes(write_gds(shapes,tech))
                polygons=gdstk.read_gds(destination).cells[0].polygons
                self.assertEqual(len(polygons),len(expected))
                for polygon,(shape,index,points) in zip(polygons,expected):
                    for actual,local in zip(polygon.points,points):
                        for axis in range(2):
                            self.assertAlmostEqual(actual[axis],local[axis]+shape.origin[axis],delta=.000501)


class GdsRangeTests(unittest.TestCase):
    def test_coordinate_overflow_rejected(self):
        tech=Technology.default()
        with self.assertRaisesRegex(ValueError,"coordinate range"):
            write_gds(build("wire",x=3e6,technology=tech),tech)

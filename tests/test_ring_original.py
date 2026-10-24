"""Every captured original ring coordinate, keyword input and exported ribbon."""
import importlib.util
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from reasitic import Technology,build,write_gds
from reasitic.bridge import handle
from reasitic.command_numbers import angle_radians,length_um
from reasitic.ring import vertices

FIXTURE=Path(__file__).parent/'fixtures/ring_original.json'


class OriginalRingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(FIXTURE.read_text());cls.cases=cls.fixture['cases']
        assert len(cls.cases)==45

    def test_every_original_creator_xy_store(self):
        components=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i):
                saved=repr(c);rows=vertices(*c['config'])
                self.assertEqual(len(rows),len(c['rows']))
                for row,expected in zip(rows,c['rows']):self.assertEqual(struct.pack('<12d',*row).hex(),expected)
                components+=12*len(rows);self.assertEqual(repr(c),saved)
        self.assertEqual(components,12588)

    def test_native_keyword_inputs_and_complete_build_requests(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i):
                p=c['parameters'];saved=repr(p)
                parsed=[length_um(p['radius'],grid_size=.1),p['sides'],length_um(p['width'],grid_size=.1),angle_radians(p['gap']),angle_radians(p['angle'])]
                self.assertEqual(struct.pack('<5d',*parsed),struct.pack('<5d',*c['config']))
                origin=[length_um(p[k],grid_size=.1)for k in('x','y')]
                self.assertEqual(struct.pack('<2d',*origin),struct.pack('<2d',*c['origin']))
                r=handle(dict(action='build',kind='ring',parameters=p,technology=self.fixture['technology'],native_keyword=True))
                self.assertEqual(r['origin'],c['origin']);self.assertEqual(len(r['segments']),len(c['rows']))
                for s,expected in zip(r['segments'],c['rows']):
                    row=[v for key in('start','end','outer_start','outer_end','inner_start','inner_end')for v in s[key][:2]]
                    self.assertEqual(struct.pack('<12d',*row).hex(),expected)
                    self.assertEqual(s['width'],c['config'][2])
                self.assertEqual(repr(p),saved)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_gds_ribbons_against_original_coordinates(self):
        import gdstk
        tech=Technology.from_text(self.fixture['technology'])
        with tempfile.TemporaryDirectory()as directory:
            destination=Path(directory)/'ring.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i):
                    shape=build('ring',technology=tech,native_keyword=True,**c['parameters'])
                    destination.write_bytes(write_gds(shape,tech));library=gdstk.read_gds(destination)
                    self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                    polygons=library.cells[0].polygons;self.assertEqual(len(polygons),len(c['rows']))
                    for polygon,bits in zip(polygons,c['rows']):
                        row=struct.unpack('<12d',bytes.fromhex(bits));expected=[(round((row[k]+c['origin'][0])*1000),round((row[k+1]+c['origin'][1])*1000))for k in(4,6,10,8)]
                        actual=[tuple(round(v*1000)for v in point)for point in polygon.points]
                        self.assertEqual(actual,expected);self.assertEqual(polygon.layer,4);self.assertEqual(polygon.datatype,0)

    def test_typed_geometry_and_bounded_invalid_inputs(self):
        typed=build('ring',radius=40.1234567,width=3.25,x=12.3456789,y=23.456789)
        self.assertEqual(typed.origin,[12.3456789,23.456789]);self.assertEqual(typed.segments[0].width,3.25)
        native=build('ring',radius=40.1234567,width=3.25,x=12.3456789,y=23.456789,native_keyword=True)
        self.assertEqual(native.origin,[12.300000190734863,23.5]);self.assertEqual(native.segments[0].width,3.200000047683716)
        with self.assertRaisesRegex(ValueError,'gap exceeds'):build('ring',native_keyword=True,gap=-20)
        with self.assertRaisesRegex(ValueError,'currently supports ring'):handle(dict(action='build',kind='wire',native_keyword=True))
        for config in((40,2,3,0,0),(40,3.5,3,0,0),(40,1025,3,0,0),(40,16,-3,0,0),(40,16,3,math.nan,0),(40,16,3,0,math.inf)):
            with self.assertRaises(ValueError):vertices(*config)
        for grid in(0,-1,math.inf,math.nan):
            with self.assertRaises(ValueError):length_um(1,grid_size=grid)

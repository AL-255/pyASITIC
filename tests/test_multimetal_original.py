"""Exact original multi-metal fields, complete public builds and independent GDS."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from reasitic import Technology,build,write_gds
from reasitic.geometry import _multimetal
from reasitic.model import Shape

FIXTURE=Path(__file__).parent/'fixtures/multimetal_original.json'


class OriginalMultimetalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(FIXTURE.read_text());cls.cases=cls.fixture['cases']
        cls.tech=Technology.from_text(cls.fixture['technology'])
        assert len(cls.cases)==180

    def exact(self,shape,c):
        self.assertEqual(struct.pack('<2d',*shape.origin),struct.pack('<2d',*c['origin']))
        self.assertEqual(len(shape.segments),len(c['segments']))
        for i,(a,b)in enumerate(zip(shape.segments,c['segments'])):
            self.assertEqual(struct.pack('<18d',*(v for point in a.points for v in point)).hex(),b['coordinates_bits'],f'Segment {i}')
            self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def test_every_original_xyz_store_and_defined_segment_field(self):
        components=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c);p=c['config'];shape=Shape('A','multimetal',[p['x'],p['y']],{})
                _multimetal(shape,self.tech,p['metal'],p['exit_metal'],p['length'],p['height'],p['width'],p['spacing'],p['turns'],p['angle'],p['phase'])
                self.exact(shape,c);components+=18*len(shape.segments)
                self.assertEqual(repr(c),before)
        self.assertEqual(components,56214)

    def test_complete_native_keyword_and_typed_public_builds(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c['parameters'])
                shape=build('multimetal',technology=self.tech,native_keyword=c['native_keyword'],**c['parameters'])
                self.exact(shape,c);self.assertEqual(repr(c['parameters']),before)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_gds_against_original_conductors_and_via_counts(self):
        import gdstk
        metal_count=len(self.tech.metals)
        with tempfile.TemporaryDirectory()as directory:
            destination=Path(directory)/'multimetal.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    shape=build('multimetal',technology=self.tech,native_keyword=c['native_keyword'],**c['parameters'])
                    destination.write_bytes(write_gds(shape,self.tech));library=gdstk.read_gds(destination)
                    self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                    polygons=library.cells[0].polygons;position=0
                    for segment in c['segments']:
                        if segment['metal']<metal_count:
                            actual=polygons[position];position+=1;values=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']))
                            expected=[(round((values[k]+c['origin'][0])*1000),round((values[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in p)for p in actual.points],expected)
                            self.assertEqual(actual.layer,segment['metal']+1);self.assertEqual(actual.datatype,0)
                        else:
                            index=segment['metal']-metal_count;via=self.tech.vias[index];cuts=segment['nx']*segment['ny']
                            expected=[via.bottom+1,via.top+1]+[100+index]*cuts
                            self.assertEqual([p.layer for p in polygons[position:position+len(expected)]],expected)
                            for cut in polygons[position+2:position+2+cuts]:self.assertAlmostEqual(cut.area(),via.width**2,delta=.002)
                            position+=len(expected)
                    self.assertEqual(position,len(polygons))

    def test_interactive_rejections_and_typed_input_compatibility(self):
        retries=[c for c in self.cases if c['label'].startswith('interactive/')and float(c['label'].split('/')[-1])<1]
        self.assertEqual(len(retries),3)
        for c in retries:
            self.assertIn('Need at least 1.000000 truns.',c['stdout']);self.assertEqual(c['config']['turns'],1.)
        p=dict(length=120.125,width=3.25,spacing=2.125,turns=1.74999999)
        self.assertEqual(build('multimetal',**p).parameters['turns'],1.5)
        self.assertEqual(build('multimetal',native_keyword=True,**p).parameters['turns'],1.75)
        shape=build('multimetal',metal='M5',bottom_metal='M1',width=3.14159265358979,x=12.3456789,y=23.456789)
        self.assertEqual(shape.origin,[12.3456789,23.456789]);self.assertEqual(shape.segments[0].width,3.14159265358979)

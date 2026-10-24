"""Unchanged original wire input modes, every XYZ field and GDS geometry."""
import importlib.util,json
from pathlib import Path
import struct,tempfile,unittest
from reasitic import Technology,build,write_gds
from reasitic.bridge import handle
from reasitic.geometry import _wire
from reasitic.model import Shape


class OriginalWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/wire_original.json').read_text());cls.cases=cls.fixture['cases']
        cls.tech=Technology.from_text(cls.fixture['technology']);assert len(cls.cases)==101

    def exact(self,shape,c):
        self.assertEqual(struct.pack('<2d',*shape.origin),struct.pack('<2d',*c['origin']));self.assertEqual(len(shape.segments),1)
        a=shape.segments[0];b=c['segments'][0]
        self.assertEqual(struct.pack('<18d',*(v for point in a.points for v in point)).hex(),b['coordinates_bits'])
        for value,key in((a.width,'width_bits'),(a.thickness,'thickness_bits'),(a.width if a.primary_width is None else a.primary_width,'primary_width_bits'),(a.thickness if a.primary_thickness is None else a.primary_thickness,'primary_thickness_bits')):
            self.assertEqual(struct.pack('<d',value).hex(),b[key])
        self.assertEqual(a.metal,b['metal'])

    def test_every_original_store_and_complete_public_input_modes(self):
        for c in self.cases:
            with self.subTest(label=c['label']):
                before=repr(c);p=c['config'];shape=Shape('A','wire',[p['x'],p['y']],{})
                _wire(shape,self.tech,p['metal'],p['length'],p['width'],p['angle'],p['phase']);self.exact(shape,c)
                self.exact(build('wire',technology=self.tech,native_keyword=c['native_keyword'],native_interactive=c.get('native_interactive',False),**c['parameters']),c)
                self.assertEqual(repr(c),before)
        self.assertEqual(sum(len(c['segments'])*18 for c in self.cases),1818)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_independent_gds_against_original_ribbon_stores(self):
        import gdstk
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'wire.gds'
            for c in self.cases:
                with self.subTest(label=c['label']):
                    shape=build('wire',technology=self.tech,native_keyword=c['native_keyword'],native_interactive=c.get('native_interactive',False),**c['parameters'])
                    path.write_bytes(write_gds(shape,self.tech));library=gdstk.read_gds(path);self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                    polygons=library.cells[0].polygons;self.assertEqual(len(polygons),1);actual=polygons[0];segment=c['segments'][0];values=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']))
                    expected=[(round((values[k]+c['origin'][0])*1000),round((values[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                    self.assertEqual([tuple(round(v*1000)for v in p)for p in actual.points],expected);self.assertEqual(actual.layer,segment['metal']+1);self.assertEqual(actual.datatype,0)

    def test_default_origin_phase_rules_and_typed_degree_compatibility(self):
        defaults=[c for c in self.cases if'/defaults/'in c['label']];self.assertEqual(len(defaults),4)
        for c in defaults:
            shape=build('wire',technology=self.tech,native_keyword=True,**c['parameters']);self.exact(shape,c)
            if'y'not in c['parameters']:self.assertEqual(c['config']['y'],c['config']['width'])
        phases=[c for c in self.cases if'/phase/'in c['label']];self.assertEqual([c['config']['phase']for c in phases],[1,1,-2])
        interactive=[c for c in self.cases if c.get('native_interactive')];self.assertEqual(len(interactive),16)
        for c in interactive:self.assertEqual(c['config']['angle'],c['parameters']['angle'])
        p=dict(name='A',length=80.123456789,width=.01,metal='M4',x=12.3456789,y=23.456789,angle=37,phase=1)
        typed=build('wire',technology=self.tech,**p);native=build('wire',technology=self.tech,native_interactive=True,**p)
        self.assertEqual(typed.segments[0].width,.01);self.assertNotEqual(typed.segments[0].end,native.segments[0].end)
        request=dict(action='build',kind='wire',parameters=p,native_interactive=True,technology=self.fixture['technology'])
        result=handle(request);self.assertEqual(result['segments'][0]['end'],native.segments[0].end)

    def test_bounded_invalid_native_inputs_and_mutually_exclusive_modes(self):
        for c in self.fixture['invalid_cases']:
            self.assertIn('Wire dimensions too small',c['stdout'])
            with self.assertRaisesRegex(ValueError,'Wire dimensions too small'):build('wire',technology=self.tech,native_keyword=True,**c['parameters'])
        with self.assertRaisesRegex(ValueError,'one native input mode'):build('wire',native_keyword=True,native_interactive=True)
        square=build('square',native_interactive=True)
        self.assertEqual((square.parameters['angle'],square.parameters['phase']),(0.,1))
        polygon=build('polygon',native_interactive=True)
        self.assertEqual((polygon.parameters['angle'],polygon.parameters['phase']),(0.,1))
        for phase in(0,2,-.5):
            with self.assertRaisesRegex(ValueError,'phase must be'):build('wire',native_interactive=True,phase=phase)
        with self.assertRaisesRegex(ValueError,'integer range'):build('wire',native_keyword=True,phase=2**31)
        with self.assertRaisesRegex(ValueError,'chip size'):build('wire',native_interactive=True,length=513)
        with self.assertRaisesRegex(ValueError,'outside chip'):build('wire',native_interactive=True,x=-1)

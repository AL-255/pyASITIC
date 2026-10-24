"""Actual interactive radial creators, valid wide rings, failures and GDS streams."""
import copy,gzip,importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds
from reasitic.bridge import handle
from reasitic.radial_inputs import gap_radians


class OriginalRadialInteractiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/radial_interactive_original.json.gz').read_bytes()));cls.tech=Technology.from_text(cls.fixture['technology'])

    def shape(self,c):
        return build(c['kind'],technology=self.tech,native_keyword=c['native_keyword'],native_interactive=not c['native_keyword'],**c['parameters'])

    def test_every_original_creation_store_and_failure(self):
        valid=failed=components=0
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index,label=c['label']):
                before=copy.deepcopy(c)
                if not c['returned']:
                    with self.assertRaisesRegex(ValueError,'gap exceeds'if c['entered']else'Ring dimensions exceed'):self.shape(c)
                    self.assertIn('Gap too large'if c['entered']else'Ring dimensions exceed',c['stdout']);failed+=1;continue
                shape=self.shape(c);self.assertEqual(shape.name,c['created_name']);self.assertEqual(struct.pack('<2d',*shape.origin).hex(),c['origin_bits']);self.assertEqual(len(shape.segments),len(c['segments']))
                for actual,expected in zip(shape.segments,c['segments']):
                    self.assertEqual(struct.pack('<18d',*(v for point in actual.points for v in point)).hex(),expected['coordinates_bits'])
                    self.assertEqual(struct.pack('<d',actual.width).hex(),expected['width_bits']);self.assertEqual(struct.pack('<d',actual.thickness).hex(),expected['thickness_bits']);self.assertEqual(actual.metal,expected['metal']);components+=18
                self.assertEqual(c['control_before'],0x37f);self.assertEqual(c['control_after'],0x37f)
                if not c['native_keyword']:
                    self.assertEqual(shape.parameters['angle'],0);self.assertEqual(shape.parameters['phase'],1)
                    if c['kind']=='polygon':self.assertEqual(struct.pack('<d',shape.parameters['turns']).hex(),c['config']['turns'])
                    else:self.assertEqual(struct.pack('<d',gap_radians(c['parameters']['gap'])).hex(),c['config']['gap'])
                    if c['sides']==4:self.assertIn('You can also use the <Square> command for a square spiral.',shape.warnings)
                self.assertEqual(c,before);valid+=1
        self.assertEqual((valid,failed,components),(109,11,65268))

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_original_ribbons_through_independent_gds_reader(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'radial.gds'
            for index,c in enumerate(self.fixture['cases']):
                if not c['returned']:continue
                with self.subTest(index=index):
                    path.write_bytes(write_gds(self.shape(c),self.tech));library=gdstk.read_gds(path);polygons=library.cells[0].polygons
                    self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9);self.assertEqual(len(polygons),len(c['segments']))
                    ox,oy=struct.unpack('<2d',bytes.fromhex(c['origin_bits']))
                    for polygon,s in zip(polygons,c['segments']):
                        values=struct.unpack('<18d',bytes.fromhex(s['coordinates_bits']));expected=[(round((values[k]+ox)*1000),round((values[k+1]+oy)*1000))for k in(6,9,15,12)]
                        self.assertEqual([tuple(round(v*1000)for v in point)for point in polygon.points],expected);self.assertEqual(polygon.layer,s['metal']+1);self.assertEqual(polygon.datatype,0)

    def test_public_bridge_precision_limits_and_typed_distinction(self):
        for kind in('ring','polygon'):
            request=dict(action='build',kind=kind,native_interactive=True,parameters=dict(radius=40.123456789,width=3.14159265358979,spacing=2.71828182845905,sides=7,turns=1.7142857142857142,gap=720.1234567,angle=999,phase=-1,x=12.3456789,y=23.456789))
            actual=handle(request);self.assertEqual(actual['origin'],[12.3456789,23.456789]);self.assertEqual(actual['parameters']['angle'],0);self.assertEqual(actual['parameters']['phase'],1)
            for key,value in(('radius',513),('width',41),('sides',2),('x',-1),('y',513),('width',1e-11)):
                with self.subTest(kind=kind,key=key,value=value):
                    with self.assertRaises(ValueError):handle(dict(request,parameters=dict(request['parameters'],**{key:value})))
            if kind=='polygon':
                for key,value in(('spacing',0),('spacing',41),('turns',.99)):
                    with self.assertRaises(ValueError):handle(dict(request,parameters=dict(request['parameters'],**{key:value})))
        with self.assertRaisesRegex(ValueError,'positive inner radius'):build('ring',radius=40,width=40,sides=4)
        self.assertTrue(build('ring',native_interactive=True,radius=40,width=40,sides=4).segments)

"""Original capacitor/VIA stores, input failures, independent GDS and bounds."""
import importlib.util,json,math,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds
from reasitic.geometry import _capacitor,_via
from reasitic.model import Shape
from reasitic.bridge import handle


class OriginalPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/primitive_original.json').read_text());cls.cases=cls.fixture['cases']
        cls.tech=Technology.from_text(cls.fixture['technology']);assert len(cls.cases)==84

    def exact(self,s,c):
        self.assertEqual(struct.pack('<2d',*s.origin).hex(),c['origin_bits']);self.assertEqual(len(s.segments),len(c['segments']))
        for i,(a,b)in enumerate(zip(s.segments,c['segments'])):
            self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits'],i)
            self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def test_private_original_constructor_stores(self):
        total=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                p=c['config'];s=Shape('A',c['kind'],[p['x'],p['y']],{})
                if c['kind']=='capacitor':_capacitor(s,self.tech,p['metal'],p['exit_metal'],p['length'],p['width'],p['angle'])
                else:
                    s.segments.append(_via(self.tech,p['metal']-len(self.tech.metals),p['nx'],p['ny']))
                    if p['phase']<0:s.segments[0].reverse()
                self.exact(s,c);total+=18*len(s.segments)
        self.assertEqual(total,2520)

    def test_public_native_keyword_and_interactive_inputs(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                saved=repr(c);s=build(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters'])
                self.exact(s,c);self.assertEqual(repr(c),saved)

    def test_original_keyword_failures_and_interactive_retries(self):
        self.assertEqual(len(self.fixture['keyword_rejections']),64)
        for c in self.fixture['keyword_rejections']:
            self.assertIn('Error:  Unknown argument type.',c['stdout'])
            with self.assertRaisesRegex(ValueError,'Unknown argument type'):handle(dict(action='build',kind='via',native_keyword=True,parameters=c['parameters']))
        self.assertEqual(len(self.fixture['invalid_capacitors']),2)
        for c in self.fixture['invalid_capacitors']:
            with self.assertRaises(ValueError):build('capacitor',native_keyword=True,**c['parameters'])
        retry=next(c for c in self.cases if'retry-count'in c['label'])
        for prompt in ['How many vias in parallel in x-dir?','How many vias in parallel in y-dir?','Via Current Flowing Down']:
            self.assertGreaterEqual(retry['stdout'].count(prompt),2)

    def test_typed_compatibility_and_native_bounds(self):
        typed=build('capacitor',length=40,width=3.14159265358979,x=12.3456789)
        self.assertEqual(typed.origin,[12.3456789,0.]);self.assertEqual(typed.segments[0].width,3.14159265358979)
        with self.assertRaisesRegex(ValueError,'distinct'):build('capacitor',metal='M3',bottom_metal='M3')
        with self.assertRaisesRegex(ValueError,'integers'):build('via',nx=2.9,ny=3)
        native=build('via',native_interactive=True,nx=2.9,ny=3.9);self.assertEqual((native.segments[0].nx,native.segments[0].ny),(2,3))
        for p in [dict(nx=0),dict(nx=1001),dict(phase=0),dict(x=-1),dict(x=513)]:
            with self.assertRaises(ValueError):build('via',native_interactive=True,**p)
        with self.assertRaises(ValueError):build('capacitor',native_interactive=True,length=513,width=5)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_gds_against_original_conductors_and_via_counts(self):
        import gdstk
        metal_count=len(self.tech.metals)
        with tempfile.TemporaryDirectory()as directory:
            destination=Path(directory)/'primitive.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    shape=build(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters'])
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
                            raw=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']))
                            sx=-1 if raw[9]<raw[6]else 1;sy=-1 if raw[7]<raw[13]else 1;step=via.width+via.spacing
                            for ix in range(segment['nx']):
                                for iy in range(segment['ny']):
                                    cut=polygons[position+2+ix*segment['ny']+iy]
                                    expected_cut=[(round((raw[12]+sx*(ix*step+dx)+c['origin'][0])*1000),round((raw[13]+sy*(iy*step+dy)+c['origin'][1])*1000))for dx,dy in [(0,0),(via.width,0),(via.width,via.width),(0,via.width)]]
                                    self.assertEqual([tuple(round(v*1000)for v in point)for point in cut.points],expected_cut)
                                    self.assertAlmostEqual(cut.area(),via.width**2,delta=.002)
                            position+=len(expected)
                    self.assertEqual(position,len(polygons))

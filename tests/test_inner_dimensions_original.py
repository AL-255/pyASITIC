"""Intact-original inner-opening square and multi-metal input/geometry stores."""
import importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds
from reasitic.geometry import _square,_multimetal
from reasitic.model import Shape


class OriginalInnerDimensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/inner_dimensions_original.json').read_text());cls.cases=cls.fixture['cases'];cls.tech=Technology.from_text(cls.fixture['technology']);assert len(cls.cases)==134

    def exact(self,s,c):
        self.assertEqual(s.name,c['name']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),c['origin_bits']);self.assertEqual(len(s.segments),len(c['segments']))
        for a,b in zip(s.segments,c['segments']):
            self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);self.assertEqual(a.metal,b['metal']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits'])
            if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def test_every_original_constructor_store(self):
        total=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                p=c['config'];s=Shape(p['name'],c['kind'],[p['x'],p['y']],{})
                function=_square if c['kind']=='square'else _multimetal
                function(s,self.tech,p['metal'],p['exit_metal'],p['length'],p['height'],p['width'],p['spacing'],p['turns'],p['angle'],p['phase']);self.exact(s,c);total+=18*len(s.segments)
        self.assertEqual(total,45072)

    def test_public_native_descriptors_and_geometry(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                saved=repr(c);s=build(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters']);self.exact(s,c)
                for key in ['length','height','width','spacing','turns','phase']:self.assertEqual(struct.pack('<d',s.parameters[key]),struct.pack('<d',c['config'][key]),key)
                self.assertEqual(repr(c),saved)

    def test_existing_original_outer_prompt_inputs(self):
        count=0
        for kind,filename in [('square','square_original.json'),('multimetal','multimetal_original.json')]:
            f=json.loads((Path(__file__).parent/'fixtures'/filename).read_text());tech=Technology.from_text(f['technology'])
            for c in f['cases']:
                if c['native_keyword']:continue
                s=build(kind,technology=tech,native_interactive=True,**c['parameters']);count+=1
                self.assertEqual(struct.pack('<2d',*s.origin),struct.pack('<2d',*c['origin']));self.assertEqual(len(s.segments),len(c['segments']))
                self.assertEqual([struct.pack('<18d',*(v for p in a.points for v in p)).hex()for a in s.segments],[a['coordinates_bits']for a in c['segments']])
        self.assertEqual(count,18)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS validation')
    def test_independent_gds(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'inner.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    s=build(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters']);path.write_bytes(write_gds([s],self.tech));lib=gdstk.read_gds(path);self.assertEqual(lib.unit,1e-6);self.assertEqual(lib.precision,1e-9)
                    polygons=lib.cells[0].polygons;position=0
                    for segment in c['segments']:
                        if segment['metal']<len(self.tech.metals):
                            values=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']));expected=[(round((values[k]+c['origin'][0])*1000),round((values[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in point)for point in polygons[position].points],expected);self.assertEqual(polygons[position].layer,segment['metal']+1);position+=1
                        else:
                            index=segment['metal']-len(self.tech.metals);via=self.tech.vias[index];expected=[via.bottom+1,via.top+1]+[100+index]*(segment['nx']*segment['ny'])
                            self.assertEqual([p.layer for p in polygons[position:position+len(expected)]],expected);position+=len(expected)
                    self.assertEqual(position,len(polygons))

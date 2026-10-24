"""Exact intact-original 3D descriptors, constructor stores and combined GDS."""
import importlib.util,json,math,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build_device,write_gds
from reasitic.bridge import handle
from reasitic.model import Shape
from reasitic.transformer3d import build_3d


class OriginalTransformer3DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/transformer3d_original.json').read_text());cls.cases=cls.fixture['cases']
        cls.tech=Technology.from_text(cls.fixture['technology']);assert len(cls.cases)==96

    def exact(self,shapes,c):
        self.assertEqual(len(shapes),2)
        for s,w in zip(shapes,c['windings']):
            self.assertEqual(s.name,w['name']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),w['origin_bits']);self.assertEqual(len(s.segments),len(w['segments']))
            self.assertEqual(w['auxiliary'],0)
            for a,b in zip(s.segments,w['segments']):
                self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);self.assertEqual(a.metal,b['metal'])
                for key in ['width','thickness','primary_width','primary_thickness']:self.assertEqual(struct.pack('<d',getattr(a,key)).hex(),b[key+'_bits'])

    def test_every_original_constructor_store(self):
        total=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                saved=repr(c);shapes=[Shape(d['name'],'transformer3d',[d['x'],d['y']],{key:d[key]for key in ['length','height','width','spacing','turns','angle','phase','metal']})for d in c['configs']]
                build_3d(*shapes,self.tech);self.exact(shapes,c);self.assertEqual(repr(c),saved);total+=sum(18*len(w['segments'])for w in c['windings'])
        self.assertEqual(total,94824)

    def test_public_native_prompt_inputs(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                self.exact(build_device('transformer3d',technology=self.tech,native_interactive=True,**c['parameters']),c)
                for j,w in enumerate(c['windings']):
                    r=handle(dict(action='build',kind='transformer3d',parameters=c['parameters'],native_interactive=True,winding=j,technology=self.fixture['technology']))
                    self.assertEqual(r['name'],w['name']);self.assertEqual(len(r['segments']),len(w['segments']))
                    self.assertEqual([struct.pack('<18d',*(v for key in ['start','end','outer_start','outer_end','inner_start','inner_end']for v in s[key])).hex()for s in r['segments']],[s['coordinates_bits']for s in w['segments']])

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS validation')
    def test_independent_combined_gds(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'3d.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    ss=build_device('transformer3d',technology=self.tech,native_interactive=True,**c['parameters']);path.write_bytes(write_gds(ss,self.tech));lib=gdstk.read_gds(path)
                    self.assertEqual(lib.unit,1e-6);self.assertEqual(lib.precision,1e-9);polygons=iter(lib.cells[0].polygons)
                    for w in c['windings']:
                        for s in w['segments']:
                            raw=struct.unpack('<18d',bytes.fromhex(s['coordinates_bits']));p=next(polygons)
                            expected=[(round((raw[k]+w['origin'][0])*1000),round((raw[k+1]+w['origin'][1])*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in point)for point in p.points],expected);self.assertEqual(p.layer,s['metal']+1);self.assertEqual(p.datatype,0)
                    self.assertIsNone(next(polygons,None))

    def test_spacing_retries_and_native_aliases(self):
        for c in self.cases:
            if c['label'].startswith('spacing-boundary'):
                if c['accepted']:self.assertNotIn('Spacing Too Small.',c['stdout'])
                else:
                    self.assertIn('Spacing Too Small.',c['stdout'])
                    with self.assertRaisesRegex(ValueError,'Spacing too small'):build_device('transformer3d',technology=self.tech,native_interactive=True,**dict(c['parameters'],spacing=c['attempted_spacing']))
        retries=self.cases[-1];self.assertGreaterEqual(retries['stdout'].count('Width?'),2);self.assertGreaterEqual(retries['stdout'].count('Turns (fractions okay)?'),2)
        c=self.cases[0]
        for alias in ['3DTrans','3DMIRRORTRANS','Trans3D','TransMIM','mirror_transformer3d']:
            self.exact(build_device(alias,technology=self.tech,native_interactive=True,**c['parameters']),c)
            self.assertEqual(handle(dict(action='build',kind=alias,native_interactive=True,parameters=c['parameters']))['name'],'P')
        self.assertEqual(len(self.fixture['invalid_keywords']),12)
        self.assertEqual(sum('Invalid Argument(s):'in c['stdout']for c in self.fixture['invalid_keywords']),3)
        self.assertEqual(sum('Unknown or Mistyped Commnd'in c['stdout']for c in self.fixture['invalid_keywords']),9)
        for invalid in self.fixture['invalid_keywords']:
            self.assertEqual(invalid['returncode'],0);self.assertTrue(any(t in invalid['stdout']for t in ['Invalid Argument(s):','Unknown or Mistyped Commnd']));self.assertNotIn('Primary Name?',invalid['stdout'])
        with self.assertRaisesRegex(ValueError,'interactive and accepts no keyword'):build_device('transformer3d',native_keyword=True)
        with self.assertRaisesRegex(ValueError,'interactive and accepts no keyword'):handle(dict(kind='3DTrans',native_keyword=True))
        with self.assertRaisesRegex(ValueError,'at least 1e-10'):build_device('transformer3d',native_interactive=True,width=math.nextafter(1e-10,0))
        with self.assertRaisesRegex(ValueError,'Choose one'):build_device('transformer3d',native_interactive=True,native_keyword=True)

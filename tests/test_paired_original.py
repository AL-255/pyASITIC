"""Both unchanged-original paired windings, input modes and combined GDS."""
import importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build_device,write_gds
from reasitic.paired_geometry import construct


class OriginalPairedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/paired_original.json').read_text());cls.cases=cls.fixture['cases']
        cls.tech=Technology.from_text(cls.fixture['technology']);assert len(cls.cases)==98

    def exact(self,shapes,c):
        self.assertEqual(len(shapes),2);self.assertTrue(c['paired_links'])
        for s,w in zip(shapes,c['windings']):
            self.assertEqual(s.name,w['name']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),w['origin_bits']);self.assertEqual(len(s.segments),len(w['segments']))
            for a,b in zip(s.segments,w['segments']):
                self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits'])
                self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
                if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
                else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def test_every_original_constructor_store(self):
        total=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                saved=repr(c);ss=construct(c['kind'],self.tech,c['configs']);self.exact(ss,c);self.assertEqual(repr(c),saved);total+=sum(18*len(s.segments)for s in ss)
        self.assertEqual(total,38592)

    def test_complete_original_keyword_and_interactive_builds(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                saved=repr(c['parameters']);ss=build_device(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters'])
                self.exact(ss,c);self.assertEqual(repr(c['parameters']),saved)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS validation')
    def test_combined_gds_against_both_original_windings(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'paired.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    shapes=build_device(c['kind'],technology=self.tech,native_keyword=c.get('native_keyword',False),native_interactive=c.get('native_interactive',False),**c['parameters'])
                    path.write_bytes(write_gds(shapes,self.tech));lib=gdstk.read_gds(path);self.assertEqual(lib.unit,1e-6);self.assertEqual(lib.precision,1e-9)
                    polygons=lib.cells[0].polygons;position=0
                    for w in c['windings']:
                        for s in w['segments']:
                            if s['metal']<len(self.tech.metals):
                                values=struct.unpack('<18d',bytes.fromhex(s['coordinates_bits']))
                                expected=[(round((values[k]+w['origin'][0])*1000),round((values[k+1]+w['origin'][1])*1000))for k in(6,9,15,12)]
                                self.assertEqual([tuple(round(v*1000)for v in p)for p in polygons[position].points],expected);self.assertEqual(polygons[position].layer,s['metal']+1);position+=1
                            else:
                                index=s['metal']-len(self.tech.metals);v=self.tech.vias[index];expected=[v.bottom+1,v.top+1]+[100+index]*(s['nx']*s['ny'])
                                self.assertEqual([p.layer for p in polygons[position:position+len(expected)]],expected);position+=len(expected)
                    self.assertEqual(position,len(polygons))

    def test_native_name_defaults_width_warning_and_prompt_capacity(self):
        defaults=[c for c in self.cases if c['label'].startswith('defaults/trans/')]
        self.assertEqual([w['name']for c in defaults for w in c['windings']],['TX-p','TX-s','AA-p','AA-s','TX','BB','AA','AA'])
        warning=next(c for c in self.cases if'ignored-secondary-width'in c['label'])
        self.assertIn('WS!=WP',warning['stdout']);ss=build_device('transformer',technology=self.tech,native_keyword=True,**warning['parameters']);self.assertIn('WS!=WP',' '.join(ss[0].warnings))
        for label in ['interactive/trans/6.25','interactive/balun/13.75']:
            c=next(c for c in self.cases if c['label']==label);self.exact(build_device(c['kind'],technology=self.tech,native_interactive=True,**c['parameters']),c)
            with self.assertRaises(ValueError):build_device(c['kind'],technology=self.tech,native_keyword=True,**c['parameters'])
        with self.assertRaisesRegex(ValueError,'Choose one'):build_device('transformer',native_keyword=True,native_interactive=True)

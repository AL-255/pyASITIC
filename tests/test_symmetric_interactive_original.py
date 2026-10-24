"""Actual original prompt inputs, warnings, failures and every geometry store."""
import importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds


class OriginalSymmetricInteractiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/symmetric_interactive_original.json').read_text())
        assert len(cls.fixture['cases'])==36 and len(cls.fixture['failed_cases'])==11

    def exact(self,s,c):
        self.assertEqual(s.name,c['config']['name']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),c['origin_bits']);self.assertEqual(len(s.segments),len(c['segments']))
        self.assertEqual(c['control_before'],0x37f);self.assertEqual(c['control_after'],0x37f)
        for key in ['width','spacing','turns','angle','phase','sides','length'if c['kind']=='symmetric_square'else'radius']:
            self.assertEqual(struct.pack('<d',float(s.parameters[key])),struct.pack('<d',float(c['config'][key])),key)
        self.assertEqual(struct.pack('<d',s.parameters['inner_gap']),struct.pack('<d',c['config']['height']))
        for a,b in zip(s.segments,c['segments']):
            self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def test_all_original_creators_and_prompt_stores(self):
        total=0
        for i,c in enumerate(self.fixture['cases']):
            with self.subTest(case=i,label=c['label']):
                before=repr(c);t=Technology.from_text(c['technology']);s=build(c['kind'],technology=t,native_interactive=True,**c['parameters']);self.exact(s,c);total+=18*len(s.segments);self.assertEqual(repr(c),before)
                for warning in s.warnings:self.assertIn(warning,next(b['stdout']for b in self.fixture['batches']if b['technology']==c['technology']))
                if c['parameters'].get('inner_gap',1)<0:self.assertIn('Warning:  Dimension less than  0.00',s.warnings)
                if 'SMIN=1/'in c['label']and c['parameters']['spacing']<1:self.assertIn('Warning:  Dimension less than  1.00',s.warnings)
                if 'SMIN=1/'in c['label']and 'inner_gap'not in c['parameters']:self.assertIn('Warning:  Transition metal width less than WMIN specified in technology file',s.warnings)
        self.assertEqual(total,10386)

    def test_native_repeated_prompt_evidence_and_errors(self):
        for c in self.fixture['failed_cases']:
            with self.subTest(label=c['label']):
                o=c['observed'];self.assertTrue(o['bounded_stop']);self.assertEqual(o['scan_count'],1200);self.assertEqual(o['signal'],0)
                self.assertNotIn(c['parameters']['name'],o['records'])
                if c['kind']=='symmetric_polygon':self.assertTrue(any(name.startswith('H')for name in o['records']),'Original keyword prelude must have reached construction')
                message='Error: Dimension exceeds maximum dimension'if c['kind']=='symmetric_polygon'else'Need more space for transitions'
                self.assertGreater(c['stdout'].count(message),10)
                expected='maximum-zero spacing/transition prompt'if c['kind']=='symmetric_polygon'else'Need more space for transitions'
                with self.assertRaisesRegex(ValueError,expected):build(c['kind'],technology=Technology.from_text(c['technology']),native_interactive=True,**c['parameters'])

    def test_existing_original_prompt_histories(self):
        f=json.loads((Path(__file__).parent/'fixtures/symmetric_geometry_original.json').read_text());count=0
        for c in f['cases']:
            if c['native_keyword']:continue
            s=build(c['kind'],technology=Technology.from_text(f['technology']),native_interactive=True,**c['parameters'])
            case=dict(c,origin_bits=struct.pack('<2d',*c['origin']).hex(),config=dict(c['config'],name=c['parameters']['name']))
            self.exact(s,case);count+=1
        self.assertEqual(count,6)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS validation')
    def test_all_original_gds(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'interactive.gds'
            for i,c in enumerate(self.fixture['cases']):
                with self.subTest(case=i,label=c['label']):
                    t=Technology.from_text(c['technology']);s=build(c['kind'],technology=t,native_interactive=True,**c['parameters']);path.write_bytes(write_gds(s,t));library=gdstk.read_gds(path);self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9);polygons=library.cells[0].polygons;at=0
                    for r in c['segments']:
                        if r['metal']<len(t.metals):
                            v=struct.unpack('<18d',bytes.fromhex(r['coordinates_bits']));expected=[(round((v[k]+c['origin'][0])*1000),round((v[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in p)for p in polygons[at].points],expected);self.assertEqual(polygons[at].layer,r['metal']+1);at+=1
                        else:
                            index=r['metal']-len(t.metals);via=t.vias[index];expected=[via.bottom+1,via.top+1]+[100+index]*(r['nx']*r['ny'])
                            self.assertEqual([p.layer for p in polygons[at:at+len(expected)]],expected);at+=len(expected)
                    self.assertEqual(at,len(polygons))

"""Intact-original symmetric keyword decisions, stores, geometry and GDS."""
import importlib.util,json,math,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds
from reasitic.symmetric_inputs import transition


class OriginalTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/transition_original.json').read_text())
        cls.cases=cls.fixture['cases'];cls.tech=Technology.from_text(cls.fixture['technology'])
        assert len(cls.cases)==840 and sum(c['accepted']for c in cls.cases)==682

    def test_explicit_validation_and_binary64_stores(self):
        count=0
        for i,c in enumerate(self.cases):
            if 'inner_gap'not in c['parameters']:continue
            with self.subTest(case=i,label=c['label']):
                w,s,y=(struct.unpack('<d',bytes.fromhex(c[k]))[0]for k in('width_bits','spacing_bits','gap_bits'))
                result=transition(w,s,y);self.assertEqual(result['reject'],c['reject']);count+=1
                self.assertEqual(c['control_before'],0x37f);self.assertEqual(c['control_after'],0x37f)
                self.assertEqual(c['comparison_mask']==0,c['reject'])
                for key,field in [('radius64','radius_bits'),('acos64','acos_bits'),('tangent64','tangent_bits')]:
                    expected=struct.unpack('<d',bytes.fromhex(c[field]))[0];actual=result[key]
                    if math.isnan(expected):self.assertTrue(math.isnan(actual))
                    else:self.assertEqual(struct.pack('<d',actual).hex(),c[field])
                for actual,bits in [(result['radius'],c['points']['radius80']),
                                    (result['extent'],c['points']['compare80'][0]),
                                    (result['limit'],c['points']['compare80'][1])]:
                    significand,exponent=struct.unpack('<QH',bytes.fromhex(bits))
                    if exponent&0x7fff==0x7fff:self.assertEqual(actual.kind,1 if significand==1<<63 else 2)
                    else:self.assertEqual(struct.pack('<IIH',*actual.words()).hex(),bits)
        self.assertEqual(count,780)

    def exact(self,shape,c):
        self.assertEqual(shape.name,c['config']['name']);self.assertEqual(struct.pack('<2d',*shape.origin).hex(),c['origin_bits'])
        self.assertEqual(c['geometry_control'],0x37f);self.assertEqual(len(shape.segments),len(c['segments']))
        for actual,expected in zip(shape.segments,c['segments']):
            self.assertEqual(struct.pack('<18d',*(v for p in actual.points for v in p)).hex(),expected['coordinates_bits'])
            self.assertEqual(struct.pack('<d',actual.width).hex(),expected['width_bits']);self.assertEqual(actual.metal,expected['metal'])
            if 'thickness_bits'in expected:self.assertEqual(struct.pack('<d',actual.thickness).hex(),expected['thickness_bits'])
            else:self.assertEqual((actual.nx,actual.ny),(expected['nx'],expected['ny']))

    def test_public_acceptance_and_every_geometry_store(self):
        components=0;defaults=0;unordered=0;signed=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c)
                if not c['accepted']:
                    with self.assertRaisesRegex(ValueError,'Need more space for transitions'):
                        build(c['kind'],technology=self.tech,native_keyword=True,**c['parameters'])
                else:
                    shape=build(c['kind'],technology=self.tech,native_keyword=True,**c['parameters']);self.exact(shape,c)
                    components+=18*len(shape.segments)
                    if 'inner_gap'not in c['parameters']:defaults+=1
                    else:
                        unordered+=c['comparison_mask']==0x45;signed+=c['parameters']['inner_gap']<=0
                self.assertEqual(repr(c),before)
        self.assertEqual(components,92070);self.assertEqual(defaults,60);self.assertGreater(unordered,0);self.assertGreater(signed,0)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS validation')
    def test_every_accepted_gds(self):
        import gdstk
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'transition.gds'
            for i,c in enumerate(self.cases):
                if not c['accepted']:continue
                with self.subTest(case=i,label=c['label']):
                    shape=build(c['kind'],technology=self.tech,native_keyword=True,**c['parameters']);path.write_bytes(write_gds(shape,self.tech));library=gdstk.read_gds(path)
                    self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                    polygons=library.cells[0].polygons;self.assertEqual(len(polygons),len(c['segments']))
                    for polygon,segment in zip(polygons,c['segments']):
                        # This batch has one turn; every observed record is metal.
                        self.assertLess(segment['metal'],len(self.tech.metals))
                        values=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']))
                        expected=[(round((values[k]+c['origin'][0])*1000),round((values[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                        self.assertEqual([tuple(round(v*1000)for v in p)for p in polygon.points],expected)
                        self.assertEqual(polygon.layer,segment['metal']+1);self.assertEqual(polygon.datatype,0)

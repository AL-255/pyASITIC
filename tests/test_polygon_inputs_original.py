"""Original polygon keyword/interactive boundaries, complete XYZ and GDS."""
import importlib.util,json
from pathlib import Path
import struct,tempfile,unittest
from reasitic import Technology,build,write_gds
from reasitic.geometry import _polygon
from reasitic.model import Shape


class OriginalPolygonInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/polygon_inputs_original.json').read_text())
        cls.tech=Technology.from_text(cls.fixture['technology']);cls.cases=cls.fixture['cases']
        assert len(cls.cases)==77

    def exact(self,shape,c):
        self.assertEqual(struct.pack('<2d',*shape.origin),struct.pack('<2d',*c['origin']))
        self.assertEqual(len(shape.segments),len(c['segments']))
        for i,(a,b)in enumerate(zip(shape.segments,c['segments'])):
            self.assertEqual(struct.pack('<18d',*(v for point in a.points for v in point)).hex(),b['coordinates_bits'],f'Segment {i}')
            self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])

    def test_complete_native_keyword_and_interactive_public_builds(self):
        components=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c);p=c['config'];shape=Shape('A','polygon',[p['x'],p['y']],{})
                _polygon(shape,self.tech,p['metal'],p['radius'],p['sides'],p['width'],p['spacing'],p['turns'],p['angle'])
                self.exact(shape,c)
                shape=build('polygon',technology=self.tech,native_keyword=c['native_keyword'],**c['parameters']);self.exact(shape,c)
                self.assertEqual(shape.parameters['turns'],p['turns']);self.assertEqual(repr(c),before)
                components+=18*len(shape.segments)
        self.assertEqual(components,34758)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_gds_against_every_original_conductor(self):
        import gdstk
        with tempfile.TemporaryDirectory()as directory:
            destination=Path(directory)/'polygon.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    shape=build('polygon',technology=self.tech,native_keyword=c['native_keyword'],**c['parameters'])
                    destination.write_bytes(write_gds(shape,self.tech));library=gdstk.read_gds(destination)
                    self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                    polygons=library.cells[0].polygons;self.assertEqual(len(polygons),len(c['segments']))
                    for actual,segment in zip(polygons,c['segments']):
                        values=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']))
                        expected=[(round((values[k]+c['origin'][0])*1000),round((values[k+1]+c['origin'][1])*1000))for k in(6,9,15,12)]
                        self.assertEqual([tuple(round(v*1000)for v in p)for p in actual.points],expected)
                        self.assertEqual(actual.layer,segment['metal']+1);self.assertEqual(actual.datatype,0)

    def test_native_turn_boundaries_defaults_typed_dimensions_and_rejections(self):
        boundaries=[c for c in self.cases if'turn-boundary'in c['label']];self.assertEqual(len(boundaries),18)
        self.assertEqual([c['config']['turns']for c in boundaries],[2.]*5+[2+1/3]+[2.]*5+[2+1/7]+[2.0625,2.0625,2.,2.0625,2.0625,2.0625])
        maximum=[c for c in self.cases if'/maximum/'in c['label']]
        self.assertEqual([c['config']['turns']for c in maximum],[2.,6+3/7,6+4/7,4.625])
        typed=[c for c in self.cases if not c['native_keyword']]
        self.assertEqual([c['config']['turns']for c in typed],[1.,1+4/7,2.375,2.96875])
        for c in typed:
            shape=build('polygon',technology=self.tech,**c['parameters'])
            self.assertEqual(shape.origin,[12.3456789,23.456789]);self.assertEqual(shape.segments[0].width,3.14159265358979)
        self.assertEqual(len(self.fixture['invalid_cases']),3)
        for c,message in zip(self.fixture['invalid_cases'],('support at most','exceed chip dimension','support at most')):
            self.assertIn('Error:',c['stdout'])
            with self.assertRaisesRegex(ValueError,message):build('polygon',technology=self.tech,native_keyword=True,**c['parameters'])

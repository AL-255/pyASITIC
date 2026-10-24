"""Every defined original symmetric geometry store and independent GDS stream."""
import importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,write_gds
from reasitic.model import Shape
from reasitic.symmetric_geometry import symmetric_square,symmetric_polygon


class OriginalSymmetricGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/symmetric_geometry_original.json').read_text())
        cls.cases=cls.fixture['cases'];cls.tech=Technology.from_text(cls.fixture['technology'])
        assert len(cls.cases)==114

    def exact(self,shape,c):
        self.assertEqual(struct.pack('<2d',*shape.origin),struct.pack('<2d',*c['origin']))
        self.assertEqual(len(shape.segments),len(c['segments']))
        for i,(a,b)in enumerate(zip(shape.segments,c['segments'])):
            self.assertEqual(struct.pack('<18d',*(v for point in a.points for v in point)).hex(),b['coordinates_bits'],f'Segment {i}')
            self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            if 'thickness_bits'in b:self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))


    def test_every_original_creator_xyz_and_defined_field(self):
        components=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c);p=c['config'];shape=Shape('A',c['kind'],[p['x'],p['y']],{})
                dimension=[p['length']]if c['kind']=='symmetric_square'else[p['radius'],p['sides']]
                create=symmetric_square if c['kind']=='symmetric_square'else symmetric_polygon
                create(shape,self.tech,p['metal'],p['exit_metal'],*dimension,p['height'],p['width'],p['spacing'],p['turns'],p['angle'],p['phase'])
                self.exact(shape,c);components+=18*len(shape.segments);self.assertEqual(repr(c),before)
        self.assertEqual(components,60804)

    def test_complete_public_keyword_and_binary64_builds(self):
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c['parameters'])
                shape=build(c['kind'],technology=self.tech,native_keyword=c['native_keyword'],**c['parameters'])
                self.exact(shape,c);self.assertEqual(repr(c['parameters']),before)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent stream validation')
    def test_gds_against_original_conductors_and_via_counts(self):
        import gdstk
        metal_count=len(self.tech.metals)
        with tempfile.TemporaryDirectory()as directory:
            destination=Path(directory)/'symmetric.gds'
            for i,c in enumerate(self.cases):
                with self.subTest(case=i,label=c['label']):
                    shape=build(c['kind'],technology=self.tech,native_keyword=c['native_keyword'],**c['parameters'])
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

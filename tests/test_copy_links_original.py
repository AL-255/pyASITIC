"""Unchanged-original copy/name/link states, materials, GDS and rejection paths."""
import copy,gzip,hashlib,importlib.util,json,struct,tempfile,unittest
from collections import Counter
from pathlib import Path
from reasitic import Technology,write_gds
from reasitic.bridge import _shapes,handle,request_json

ROOT=Path(__file__).parent/'fixtures'
def fixture():return json.loads(gzip.decompress((ROOT/'copy_links_original.json.gz').read_bytes()))


class OriginalCopyLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixture();assert len(cls.fixture['cases'])==17 and sum(len(c['states'])for c in cls.fixture['cases'])==229
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((ROOT/(name+'.json')).read_bytes()).hexdigest()==digest

    def states(self):
        for c in self.fixture['cases']:
            tech=Technology.from_text(c['technology'])
            for index,event in enumerate(c['states']):
                request=dict(c['public'],edits=c['operations'][:index],technology=c['technology'])
                yield c,index,event,tech,request

    def test_every_original_name_link_coordinate_and_material_store(self):
        total=valid=rejected=0;saved=copy.deepcopy(self.fixture)
        for c,index,event,tech,request in self.states():
            with self.subTest(case=c['label'],state=index):
                self.assertEqual((event['control'],c['signal']),(0x37f,0))
                if c['label']=='copy-used'and index==2:
                    rejected+=1;self.assertEqual(Counter(s['name']for s in event['shapes']),Counter(A=2,B=1));self.assertEqual([len(s['segments'])for s in event['shapes']],[0,1,1])
                    message='Cannot copy using a spiral name which is already in use.';self.assertIn(message,c['stdout'])
                    with self.assertRaisesRegex(ValueError,message):_shapes(request,tech)
                    self.assertIn(message,json.loads(request_json(json.dumps(dict(request,action='build'))))['error']);continue
                shapes,links=_shapes(request,tech,with_links=True);expected={s['name']:s for s in event['shapes']};self.assertEqual(len(shapes),len(expected));valid+=1
                for i,shape in enumerate(shapes):
                    native=expected[shape.name];self.assertEqual(struct.pack('<2d',*shape.origin).hex(),native['origin_bits']);self.assertEqual(len(shape.segments),len(native['segments']))
                    self.assertEqual(shapes[links[i]].name if links[i]is not None else None,native['partner'])
                    for s,r in zip(shape.segments,native['segments']):
                        self.assertEqual(struct.pack('<18d',*(v for p in s.points for v in p)).hex(),r['coordinates_bits']);total+=18
                        self.assertEqual(struct.pack('<d',s.width).hex(),r['width_bits']);self.assertEqual(s.metal,r['metal'])
                        if 'thickness_bits'in r:
                            self.assertEqual(struct.pack('<d',s.thickness).hex(),r['thickness_bits'])
                            self.assertEqual(struct.pack('<d',s.primary_width if s.primary_width is not None else s.width).hex(),r['primary_width_bits'])
                            self.assertEqual(struct.pack('<d',s.primary_thickness if s.primary_thickness is not None else s.thickness).hex(),r['primary_thickness_bits'])
                        else:self.assertEqual((s.nx,s.ny),(r['nx'],r['ny']))
                data=handle(dict(request,action='build'));self.assertEqual(data['partners'],links);self.assertEqual(data['windings'],[s.name for s in shapes])
        self.assertEqual((valid,rejected,total),(228,1,117630));self.assertEqual(self.fixture,saved)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_every_valid_scene_through_independent_gds_reader(self):
        import gdstk
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'copies.gds'
            for c,index,event,tech,request in self.states():
                if c['label']=='copy-used'and index==2:
                    with self.assertRaisesRegex(ValueError,'Cannot copy using'):_shapes(request,tech)
                    continue
                shapes=_shapes(request,tech);path.write_bytes(write_gds(shapes,tech));library=gdstk.read_gds(path);polygons=library.cells[0].polygons;position=0;expected={s['name']:s for s in event['shapes']}
                self.assertEqual((library.unit,library.precision),(1e-6,1e-9))
                for shape in shapes:
                    native=expected[shape.name];ox,oy=struct.unpack('<2d',bytes.fromhex(native['origin_bits']))
                    for s in native['segments']:
                        if s['metal']<len(tech.metals):
                            values=struct.unpack('<18d',bytes.fromhex(s['coordinates_bits']));points=[(round((values[k]+ox)*1000),round((values[k+1]+oy)*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in p)for p in polygons[position].points],points);self.assertEqual((polygons[position].layer,polygons[position].datatype),(s['metal']+1,0));position+=1
                        else:
                            index=s['metal']-len(tech.metals);v=tech.vias[index];layers=[v.bottom+1,v.top+1]+[100+index]*(s['nx']*s['ny'])
                            self.assertEqual([p.layer for p in polygons[position:position+len(layers)]],layers);position+=len(layers)
                self.assertEqual(position,len(polygons))

    def test_native_rejection_messages_and_metadata_without_regeneration(self):
        for c in self.fixture['cases'][-5:-1]:
            r=handle(dict(c['public'],action='build',edits=c['operations'],technology=c['technology']))
            self.assertTrue(r['warnings']);self.assertIn(r['warnings'][-1],c['stdout'])
        c=self.fixture['cases'][0];original=handle(dict(c['public'],action='build',technology=c['technology']))
        request=dict(c['public'],action='build',edits=[dict(command='COPY',name='c')],winding=1,technology=c['technology'])
        self.assertEqual(handle(request)['name'],'C')
        with self.assertRaisesRegex(ValueError,'Invalid winding'):handle(dict(request,edits=[]))
        restored=handle(dict(request,edits=[],reset_missing_winding=True));self.assertEqual(restored['winding'],0);self.assertEqual(restored['segments'],original['segments'])
        with self.assertRaisesRegex(ValueError,'Invalid winding'):handle(dict(request,edits=[],action='lmat',reset_missing_winding=True))
        for change in[dict(name=''),dict(name='a b'),dict(name='a,b'),dict(name='a'*80),dict(name='x',y=1),dict(name='x',x=1),dict(name='x',metal='invalid')]:
            with self.subTest(change=change):
                self.assertIn('error',json.loads(request_json(json.dumps(dict(c['public'],action='build',edits=[dict(command='COPY',**change)])))))

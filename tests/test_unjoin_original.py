"""Actual original split geometry, header arithmetic, transfers and fault outcomes."""
import copy,gzip,hashlib,json,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle,request_json
import test_erase_original as erase


class OriginalUnjoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'unjoin_original.json.gz').read_bytes()))
        assert len(cls.fixture['cases'])==44 and sum(len(c['states'])for c in cls.fixture['cases'])==178
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest

    def states(self):
        for c in self.fixture['cases']:
            tech=Technology.from_text(c['technology'])
            for i,event in enumerate(c['states']):yield c,i,event,tech,dict(c['public'],technology=c['technology'],edits=c['operations'][:i])

    def test_every_original_coordinate_material_header_and_link(self):
        saved=copy.deepcopy(self.fixture);total=0;empty=0
        kinds=dict(square=0,polygon=1,wire=2,transformer=3,balun=5,transformer3d=10,via=14,symmetric_square=16,symmetric_polygon=17,capacitor=21,multimetal=21,joined=21,ring=22)
        for c,index,event,tech,r in self.states():
            with self.subTest(label=c['label'],state=index):
                self.assertEqual(event['control'],0x37f);shapes,links=_shapes(r,tech,with_links=True);expected={s['name']:s for s in event['shapes']};self.assertEqual({s.name for s in shapes},set(expected))
                for i,s in enumerate(shapes):
                    n=expected[s.name];self.assertEqual(kinds[s.kind],n['native_kind']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(len(s.segments),len(n['segments']))
                    self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(bool(shapes.dangling_partners[i]),n['dangling_partner'])
                    if c['public']['kind']=='capacitor'and n['attributes']>0:self.assertGreater(s.electrical_phase,0)
                    else:self.assertEqual(s.electrical_phase,n['attributes'])
                    if hasattr(s,'_native_divisions'):
                        self.assertEqual(s._native_divisions,n['native_n'])
                        if s._native_turns is not None:self.assertEqual(struct.pack('<d',s._native_turns).hex(),n['turns_bits'])
                        else:self.assertEqual(c['public']['kind'],'ring')
                    for a,b in zip(s.segments,n['segments']):
                        self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);total+=18
                        self.assertEqual(a.metal,b['metal']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits'])
                        if 'thickness_bits'in b:
                            for value,key in((a.thickness,'thickness_bits'),(a.width if a.primary_width is None else a.primary_width,'primary_width_bits'),(a.thickness if a.primary_thickness is None else a.primary_thickness,'primary_thickness_bits')):self.assertEqual(struct.pack('<d',value).hex(),b[key])
                        else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))
                    result=handle(dict(r,action='build',winding=i));self.assertEqual(result['windings'],[s.name for s in shapes]);self.assertEqual(result['partners'],links)
                    if not s.segments:
                        empty+=1;self.assertEqual(result['bounds'],[1e15,1e15,-1e15,-1e15]);self.assertEqual([result[k]for k in('length','area','metal_area','dc_ohm')],[0.,0.,0.,0.])
        self.assertEqual(total,33084);self.assertGreater(empty,0);self.assertEqual(self.fixture,saved)

    test_every_split_scene_through_independent_gds=erase.OriginalEraseTests.test_every_erased_scene_including_empty_through_gds_reader

    def test_all_selected_plain_outcomes_rejections_and_aliases(self):
        faults=[]
        for c in self.fixture['cases']:
            with self.subTest(label=c['label']):
                r=dict(c['public'],action='build',technology=c['technology'],edits=c['operations'])
                if c['signal']:
                    faults.append(c['label']);self.assertEqual((c['signal'],c['plain']['returncode']),(11,-11));self.assertEqual(len(c['states']),len(c['operations']))
                    with self.assertRaisesRegex(ValueError,'(?i)original.*faults on an empty segment chain'):handle(r)
                else:
                    self.assertEqual(c['plain']['returncode'],0);self.assertEqual(len(c['states']),len(c['operations'])+1);handle(r)
                for op in c['operations']:
                    if op.get('expect_rejection',False):self.assertIn('Error:',c['plain']['stdout'])
        self.assertEqual(set(faults),{'empty/'+name for name in('unjoin','copy','erase','flip','join')})
        c=next(c for c in self.fixture['cases']if c['label']=='series/square');r=dict(c['public'],action='build',technology=c['technology'],edits=c['operations'][:1]);expected=handle(r)
        for alias in('UNJOIN','SPLIT','BREAK','CUT'):
            aliased=copy.deepcopy(r);aliased['edits'][0]['command']=alias;self.assertEqual(handle(aliased),expected)
        for index in(None,True,1<<31,-(1<<31)-1,'bad'):
            invalid=copy.deepcopy(r);invalid['edits'][0]['index']=index;self.assertIn('error',json.loads(request_json(json.dumps(invalid))))
        for name in('','two names','a'*80):
            invalid=copy.deepcopy(r);invalid['edits'][0]['name']=name;self.assertIn('error',json.loads(request_json(json.dumps(invalid))))
        c=next(c for c in self.fixture['cases']if c['label']=='series/wire');r=dict(c['public'],technology=c['technology'],edits=c['operations'],winding=1)
        for action in('pi2','lmat','selfres','mesh'):
            with self.assertRaisesRegex(ValueError,'contains no segments'):handle(dict(r,action=action))

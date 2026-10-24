"""Every original series-JOIN history, copied record and descriptor lifetime."""
import copy,gzip,hashlib,json,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle,request_json
import test_erase_original as erase


class OriginalJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'join_original.json.gz').read_bytes()))
        assert len(cls.fixture['cases'])==20 and sum(len(c['states'])for c in cls.fixture['cases'])==189
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest()==digest

    def states(self):
        for c in self.fixture['cases']:
            tech=Technology.from_text(c['technology'])
            for i,event in enumerate(c['states']):yield c,i,event,tech,dict(c['public'],technology=c['technology'],edits=c['operations'][:i])

    def test_every_original_coordinate_material_phase_and_link(self):
        total=0;saved=copy.deepcopy(self.fixture)
        kinds=dict(square=0,polygon=1,wire=2,transformer=3,balun=5,transformer3d=10,via=14,symmetric_square=16,symmetric_polygon=17,capacitor=21,multimetal=21,joined=21,ring=22)
        for c,index,event,tech,r in self.states():
            with self.subTest(label=c['label'],state=index):
                self.assertEqual((c['signal'],event['control']),(0,0x37f));shapes,links=_shapes(r,tech,with_links=True);expected={s['name']:s for s in event['shapes']};self.assertEqual({s.name for s in shapes},set(expected))
                for i,s in enumerate(shapes):
                    n=expected[s.name];self.assertEqual(kinds[s.kind],n['native_kind']);self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(len(s.segments),len(n['segments']))
                    self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(bool(shapes.dangling_partners[i]),n['dangling_partner'])
                    if c['label']=='series/capacitor'and n['attributes']==c['states'][0]['shapes'][0]['attributes']:
                        # The original interactive CAP's uninitialized positive
                        # phase word propagates through copies and JOIN.
                        self.assertGreater(n['attributes'],0);self.assertGreater(s.electrical_phase,0)
                    else:self.assertEqual(s.electrical_phase,n['attributes'])
                    for a,b in zip(s.segments,n['segments']):
                        self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);total+=18
                        self.assertEqual(a.metal,b['metal']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits'])
                        if 'thickness_bits'in b:
                            for value,key in((a.thickness,'thickness_bits'),(a.width if a.primary_width is None else a.primary_width,'primary_width_bits'),(a.thickness if a.primary_thickness is None else a.primary_thickness,'primary_thickness_bits')):self.assertEqual(struct.pack('<d',value).hex(),b[key])
                        else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))
                result=handle(dict(r,action='build'));self.assertEqual(result['windings'],[s.name for s in shapes]);self.assertEqual(result['partners'],links)
        self.assertEqual(total,75924);self.assertEqual(self.fixture,saved)

    test_independent_gds_after_every_join_and_reused_link=erase.OriginalEraseTests.test_every_erased_scene_including_empty_through_gds_reader

    def test_aliases_parser_rejections_and_input_validation(self):
        case=next(c for c in self.fixture['cases']if c['label']=='series/wire');r=dict(case['public'],technology=case['technology'],action='build',edits=case['operations'][:4]);expected=handle(r)
        for alias in('JOIN','ADD','MATE','COUPLE'):
            aliased=copy.deepcopy(r);aliased['edits'][-1]['command']=alias;self.assertEqual(handle(aliased),expected)
        for indices in([],None,[True],[-1],[.5],[99]):
            invalid=copy.deepcopy(r);invalid['edits'][-1]['others']=indices;self.assertIn('error',json.loads(request_json(json.dumps(invalid))))
        for label,message in [('duplicates','Error:  Cannot join a spiral to itslef.'),('argument-count/15','Error:  Unknown argument type.'),('series/via','Error:  Via layer 3 can only join to metals 4 or 3.')]:
            c=next(c for c in self.fixture['cases']if c['label']==label);result=handle(dict(c['public'],action='build',edits=c['operations'],technology=c['technology']));self.assertIn(message,result['warnings']);self.assertIn(message,c['stdout'])

    def test_original_assembly_and_instruction_capture_provenance(self):
        from reasitic.retained_scalar import Real as R
        from reasitic.impedance import TAU,NANO
        root=Path(__file__).parent/'fixtures';assembly_path=root/'join_assembly_original.json.gz';model_path=root/'join_sessions_original.json.gz'
        f=json.loads(gzip.decompress(assembly_path.read_bytes()));self.assertEqual(hashlib.sha256(model_path.read_bytes()).hexdigest(),f['parent_sha256']);self.assertEqual(len(f['cases']),1)
        a=f['cases'][0];self.assertEqual((a['n'],a['control_before'],a['control_after']),(50,0x37f,0x37f));self.assertEqual(len(a['records']),50)
        upper=bytes.fromhex(a['upper_bits']);self.assertEqual(len(upper),50*51//2*16)
        traces=json.loads(gzip.decompress((root/'join_mutual_traces_original.json.gz').read_bytes()))
        for name,digest in traces['parents'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
        self.assertEqual([(c['first'],c['second'])for c in traces['cases']],[(12,45),(12,48)])
        omega=float(R(NANO)*R(float(R(TAU)*R(a['frequency']))))
        for c in traces['cases']:
            i,j=c['first'],c['second'];self.assertEqual(c['input_bits'],a['records'][i]['wire_bits']+a['records'][j]['wire_bits']);self.assertEqual((c['control_before'],c['control_after']),(0x37f,0x37f))
            scaled=float(R(omega)*R(struct.unpack('<d',bytes.fromhex(c['output_bits']))[0]));at=(j*(j+1)//2+i)*16+8
            self.assertEqual(struct.pack('<d',scaled),upper[at:at+8])

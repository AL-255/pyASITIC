"""Original PHASE predicates and exact endpoint/material stores, all generators."""
import copy,gzip,hashlib,json,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle,request_json
import test_copy_links_original as copies

class OriginalPhaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'phase_original.json.gz').read_bytes()));assert len(cls.fixture['cases'])==20 and sum(len(c['states'])for c in cls.fixture['cases'])==320
  for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest()==digest
 def states(self):
  for c in self.fixture['cases']:
   tech=Technology.from_text(c['technology'])
   for index,event in enumerate(c['states']):yield c,index,event,tech,dict(c['public'],edits=c['operations'][:index],technology=c['technology'])
 def test_all_original_phase_endpoints_materials_and_sticky_words(self):
  total=0;saved=copy.deepcopy(self.fixture)
  for c,index,event,tech,request in self.states():
   with self.subTest(label=c['label'],state=index):
    self.assertEqual((c['signal'],event['control']),(0,0x37f));shapes,links=_shapes(request,tech,with_links=True);expected={s['name']:s for s in event['shapes']};self.assertEqual(len(shapes),len(expected))
    for i,shape in enumerate(shapes):
     native=expected[shape.name];self.assertEqual(struct.pack('<2d',*shape.origin).hex(),native['origin_bits']);self.assertEqual(len(shape.segments),len(native['segments']));self.assertEqual(shapes[links[i]].name if links[i]is not None else None,native['partner'])
     if c['label']=='capacitor'and index==0:
      # Native interactive CAP leaves this word uninitialized. Only its
      # observed sign is an input to PHASE; never invent its numeric address.
      self.assertGreater(native['attributes'],0);self.assertGreater(shape.electrical_phase,0)
     else:self.assertEqual(shape.electrical_phase,native['attributes'])
     for s,r in zip(shape.segments,native['segments']):
      self.assertEqual(struct.pack('<18d',*(v for p in s.points for v in p)).hex(),r['coordinates_bits']);total+=18
      self.assertEqual(struct.pack('<d',s.width).hex(),r['width_bits']);self.assertEqual(s.metal,r['metal'])
      if'thickness_bits'in r:
       self.assertEqual(struct.pack('<d',s.thickness).hex(),r['thickness_bits']);self.assertEqual(struct.pack('<d',s.primary_width if s.primary_width is not None else s.width).hex(),r['primary_width_bits']);self.assertEqual(struct.pack('<d',s.primary_thickness if s.primary_thickness is not None else s.thickness).hex(),r['primary_thickness_bits'])
      else:self.assertEqual((s.nx,s.ny),(r['nx'],r['ny']))
    public=handle(dict(request,action='build'));self.assertEqual(public['electrical_phase'],shapes[0].electrical_phase)
  self.assertEqual(total,98190);self.assertEqual(self.fixture,saved)
 def test_all_phased_scenes_through_independent_gds_reader(self):
  copies.OriginalCopyLinkTests.test_every_valid_scene_through_independent_gds_reader(self)
 def test_integer_phase_boundary_and_source_parameters(self):
  c=self.fixture['cases'][0];r=dict(c['public'],technology=c['technology']);before=copy.deepcopy(r)
  actual=handle(dict(r,action='build',edits=[dict(command='PH',phase=-1)]));self.assertEqual(actual['parameters'],handle(dict(r,action='build'))['parameters']);self.assertEqual(actual['electrical_phase'],-1);self.assertEqual(r,before)
  for value in(True,None,'bad',float('nan'),float('inf'),-2147483649,2147483648):
   with self.subTest(value=value):self.assertIn('Phase must be a signed 32-bit integer',json.loads(request_json(json.dumps(dict(r,action='build',edits=[dict(command='PHASE',phase=value)]))))['error'])

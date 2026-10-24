"""Complete unchanged-original erasure scenes, descriptor lifetimes and GDS."""
import copy,gzip,hashlib,importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,write_gds
from reasitic.bridge import _shapes,handle,request_json

class OriginalEraseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  root=Path(__file__).parent/'fixtures';cls.fixtures=[json.loads(gzip.decompress((root/(n+'.json.gz')).read_bytes()))for n in('phase_erase_original','erase_pool_original')]
  assert [sum(len(c['states'])for c in f['cases'])for f in cls.fixtures]==[210,526]
  for f in cls.fixtures:
   for n,d in f['parents'].items():assert hashlib.sha256((root/(n+'.json')).read_bytes()).hexdigest()==d
 def states(self):
  for f in self.fixtures:
   for c in f['cases']:
    tech=Technology.from_text(c['technology'])
    for i,e in enumerate(c['states']):yield c,i,e,tech,dict(c['public'],technology=c['technology'],edits=c['operations'][:i])
 def test_every_original_live_erased_reused_coordinate_and_link(self):
  total=0;before=copy.deepcopy(self.fixtures)
  for c,index,e,tech,r in self.states():
   with self.subTest(label=c['label'],state=index):
    self.assertEqual((c['signal'],e['control']),(0,0x37f));shapes,links=_shapes(r,tech,with_links=True);expected={s['name']:s for s in e['shapes']};self.assertEqual(len(shapes),len(expected))
    for i,s in enumerate(shapes):
     n=expected[s.name];self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(len(s.segments),len(n['segments']));self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(bool(shapes.dangling_partners[i]),n['dangling_partner'])
     if c['label']=='capacitor'and index==0:self.assertGreater(s.electrical_phase,0);self.assertGreater(n['attributes'],0)
     else:self.assertEqual(s.electrical_phase,n['attributes'])
     for a,b in zip(s.segments,n['segments']):
      self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);total+=18;self.assertEqual(a.metal,b['metal']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits'])
      if'thickness_bits'in b:
       self.assertEqual(struct.pack('<d',a.thickness).hex(),b['thickness_bits']);self.assertEqual(struct.pack('<d',a.primary_width if a.primary_width is not None else a.width).hex(),b['primary_width_bits']);self.assertEqual(struct.pack('<d',a.primary_thickness if a.primary_thickness is not None else a.thickness).hex(),b['primary_thickness_bits'])
      else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))
    result=handle(dict(r,action='build'));self.assertEqual(result['windings'],[s.name for s in shapes]);self.assertEqual(result['partners'],links)
    if c['label']=='pool/15'and index>=61:self.assertIn('Error:  Unknown argument type.',result['warnings']);self.assertIn('Error:  Unknown argument type.',c['stdout'])
  self.assertEqual(total,843264);self.assertEqual(self.fixtures,before)
 @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
 def test_every_erased_scene_including_empty_through_gds_reader(self):
  import gdstk
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'erase.gds'
   for c,index,e,tech,r in self.states():
    shapes=_shapes(r,tech);path.write_bytes(write_gds(shapes,tech));library=gdstk.read_gds(path);polys=library.cells[0].polygons;pos=0;expected={s['name']:s for s in e['shapes']}
    for s in shapes:
     n=expected[s.name];ox,oy=struct.unpack('<2d',bytes.fromhex(n['origin_bits']))
     for a in n['segments']:
      if a['metal']<len(tech.metals):
       values=struct.unpack('<18d',bytes.fromhex(a['coordinates_bits']));points=[(round((values[k]+ox)*1000),round((values[k+1]+oy)*1000))for k in(6,9,15,12)];self.assertEqual([tuple(round(v*1000)for v in p)for p in polys[pos].points],points);self.assertEqual(polys[pos].layer,a['metal']+1);pos+=1
      else:
       idx=a['metal']-len(tech.metals);via=tech.vias[idx];layers=[via.bottom+1,via.top+1]+[100+idx]*(a['nx']*a['ny']);self.assertEqual([p.layer for p in polys[pos:pos+len(layers)]],layers);pos+=len(layers)
    self.assertEqual(pos,len(polys))
 def test_empty_scene_analysis_selection_and_atomic_input_validation(self):
  r=dict(kind='wire',parameters=dict(name='A',length=40,width=5,metal='M4'),edits=[dict(command='ERASE',windings=[0])]);self.assertEqual(handle(dict(r,action='build'))['windings'],[])
  for action in('simulate','lmat','pi2','capacitance'):
   with self.assertRaisesRegex(ValueError,'No windings remain'):handle(dict(r,action=action))
  self.assertTrue(handle(dict(r,action='gds'))['base64'])
  for indices in([],None,[True],[-1],[.5],[99]):
   with self.subTest(indices=indices):self.assertIn('error',json.loads(request_json(json.dumps(dict(r,action='build',edits=[dict(command='ERASE',windings=indices)])))))
  r['edits']=[dict(command='COPY',name='B'),dict(command='COPY',name='C'),dict(command='ERASE',windings=[0])]
  selected=handle(dict(r,action='build',winding=2,reset_missing_winding=True,select_name='C'));self.assertEqual((selected['name'],selected['winding']),('C',1))

 def test_original_repeated_descriptor_fault(self):
  root=Path(__file__).parent/'fixtures';f=json.loads(gzip.decompress((root/'erase_faults_original.json.gz').read_bytes()));self.assertEqual(len(f['cases']),1)
  for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest(),digest)
  c=f['cases'][0];self.assertEqual(c['signal'],11);self.assertEqual(len(c['states']),1)
  r=dict(c['public'],action='build',edits=c['operations'],technology=c['technology'])
  with self.assertRaisesRegex(ValueError,'original ERASE faults'):handle(r)
  self.assertIn('original ERASE faults',json.loads(request_json(json.dumps(r)))['error'])

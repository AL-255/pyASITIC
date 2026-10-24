"""Complete original model/port outputs after endpoint phase changes."""
import gzip,hashlib,json,struct
from pathlib import Path
import test_spatial_sessions_original as spatial
import test_copy_sessions_original as copies
from reasitic import Technology
from reasitic.bridge import _shapes,handle

class OriginalPhaseSessionTests(spatial.OriginalSpatialSessionTests):
 @classmethod
 def setUpClass(cls):
  root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'phase_sessions_original.json.gz').read_bytes()));assert len(cls.fixture['cases'])==6
  for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
 def test_final_native_phase_geometry_and_metadata(self):
  for c in self.fixture['cases']:
   with self.subTest(label=c['label']):
    r=c['request'];shapes,links=_shapes(r,Technology.from_text(r['technology']),with_links=True);event=c['geometry_states'][0];self.assertEqual(event['control'],0x37f);native={s['name']:s for s in event['shapes']};self.assertEqual(len(shapes),len(native))
    for i,shape in enumerate(shapes):
     n=native[shape.name];self.assertEqual(shape.electrical_phase,n['attributes']);self.assertEqual(struct.pack('<2d',*shape.origin).hex(),n['origin_bits']);self.assertEqual(len(shape.segments),len(n['segments']));self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner'])
     for s,t in zip(shape.segments,n['segments']):self.assertEqual(struct.pack('<18d',*(v for p in s.points for v in p)).hex(),t['coordinates_bits']);self.assertEqual(s.metal,t['metal']);self.assertEqual(struct.pack('<d',s.width).hex(),t['width_bits'])
    public=handle(dict(r,action='build'));self.assertEqual(public['electrical_phase'],shapes[r['winding']].electrical_phase)
 def test_original_nonfinite_cap_reference(self):
  copies.OriginalCopySessionTests.test_original_converted_via_nonfinite_cap_reference(self)

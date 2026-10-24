"""Every original electrical output after ERASE and recycled friend movement."""
import gzip,hashlib,json,struct
from pathlib import Path
import test_spatial_sessions_original as spatial
from reasitic import Technology
from reasitic.bridge import _shapes,handle

class OriginalEraseSessionTests(spatial.OriginalSpatialSessionTests):
 @classmethod
 def setUpClass(cls):
  root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'erase_sessions_original.json.gz').read_bytes()));assert len(cls.fixture['cases'])==4
  for n,d in cls.fixture['parents'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==d
 def test_complete_native_post_erase_descriptors(self):
  for c in self.fixture['cases']:
   with self.subTest(label=c['label']):
    r=c['request'];shapes,links=_shapes(r,Technology.from_text(r['technology']),with_links=True);event=c['geometry_states'][0];expected={s['name']:s for s in event['shapes']};self.assertEqual(len(shapes),len(expected));self.assertEqual(event['control'],0x37f)
    for i,s in enumerate(shapes):
     n=expected[s.name];self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(s.electrical_phase,n['attributes']);self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(len(s.segments),len(n['segments']))
     for a,b in zip(s.segments,n['segments']):self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits']);self.assertEqual(a.metal,b['metal']);self.assertEqual(struct.pack('<d',a.width).hex(),b['width_bits'])
    self.assertEqual(handle(dict(r,action='build'))['name'],shapes[r['winding']].name)

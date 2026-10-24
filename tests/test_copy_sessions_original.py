"""Complete original models and descriptors for copied windings in a scene."""
import gzip,hashlib,json,struct
from pathlib import Path
import test_spatial_sessions_original as spatial
from reasitic import Technology
from reasitic.bridge import _shapes,handle,request_json


class OriginalCopySessionTests(spatial.OriginalSpatialSessionTests):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'copy_sessions_original.json.gz').read_bytes()));assert len(cls.fixture['cases'])==5
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest

    def test_all_final_native_copied_scene_descriptors(self):
        for c in self.fixture['cases']:
            request=c['request'];tech=Technology.from_text(request['technology']);shapes,links=_shapes(request,tech,with_links=True);event=c['geometry_states'][0];self.assertEqual(event['control'],0x37f)
            expected={s['name']:s for s in event['shapes']};count=2 if request['kind']=='via'else 3;self.assertEqual((len(shapes),len(expected)),(count,count))
            for i,a in enumerate(shapes):
                b=expected[a.name];self.assertEqual(struct.pack('<2d',*a.origin).hex(),b['origin_bits']);self.assertEqual(len(a.segments),len(b['segments']));self.assertEqual(shapes[links[i]].name if links[i]is not None else None,b['partner'])
                for s,t in zip(a.segments,b['segments']):
                    self.assertEqual(struct.pack('<18d',*(v for p in s.points for v in p)).hex(),t['coordinates_bits']);self.assertEqual(struct.pack('<d',s.width).hex(),t['width_bits']);self.assertEqual(s.metal,t['metal'])
                    if'thickness_bits'in t:self.assertEqual(struct.pack('<d',s.thickness).hex(),t['thickness_bits'])
                    else:self.assertEqual((s.nx,s.ny),(t['nx'],t['ny']))
            public=handle(dict(request,action='build'));index=request['winding'];self.assertEqual(public['winding'],index);self.assertEqual(public['name'],shapes[index].name)

    def test_original_converted_via_nonfinite_cap_reference(self):
        cases=self.fixture['cap_reference_failures'];self.assertEqual(len(cases),1)
        for c in cases:
            self.assertEqual(c['returncode'],0);self.assertIn('Total Capacitance =  -nan',c['stdout']);self.assertIn('Total Resistance =  -nan',c['stdout'])
            with self.assertRaisesRegex(ValueError,'Original CAP reduction is nonfinite'):handle(c['request'])
            self.assertIn('Original CAP reduction is nonfinite',json.loads(request_json(json.dumps(c['request'])))['error'])

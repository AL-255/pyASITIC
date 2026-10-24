"""Raw original models after JOIN, plus every selected untouched outcome."""
import gzip,hashlib,json,math,struct
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle
import test_spatial_sessions_original as spatial


class OriginalJoinSessionTests(spatial.OriginalSpatialSessionTests):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'join_sessions_original.json.gz').read_bytes()));cls.plain=json.loads(gzip.decompress((root/'join_plain_outcomes_original.json.gz').read_bytes()))
        assert len(cls.fixture['cases'])==7 and len(cls.plain['cases'])==8
        for f in(cls.fixture,cls.plain):
            for name,digest in f['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest

    def test_complete_edited_models_and_native_node_matrices(self):
        finite=[];nonfinite=[]
        for c in self.fixture['cases']:
            words=c['model']['Y']if c['request']['action']=='pi2'else c['raw_output_bits'][:8]
            if all(math.isfinite(struct.unpack('<d',bytes.fromhex(w))[0])for w in words):finite.append(c)
            else:
                nonfinite.append(c);self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(w))[0])for w in words))
                scattering=c['scattering']['S']if c['request']['action']=='pi2'else c['records'][0]['S']
                self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(w))[0])for w in scattering))
                with self.assertRaisesRegex(ValueError,'contact collapses or exceeds the FFT grid'):handle(c['request'])
        self.assertEqual(len(finite),4);self.assertEqual(len(nonfinite),3)
        spatial.assert_original_models(self,finite)

    def test_complete_original_descriptors_and_all_plain_outcomes(self):
        successful={c['label']for c in self.plain['cases']if c['produced_model']};self.assertEqual(successful,{c['label']for c in self.fixture['cases']})
        failed=[c for c in self.plain['cases']if not c['produced_model']];self.assertEqual(len(failed),1);c=failed[0];self.assertEqual((c['label'],c['returncode']),('wire/pi2',0));self.assertIn('Error:  Coordinate out of range.',c['stdout'])
        with self.assertRaises(ValueError):handle(c['request'])
        for c in self.fixture['cases']:
            r=c['request'];shapes,links=_shapes(r,Technology.from_text(r['technology']),with_links=True);expected={s['name']:s for s in c['geometry_states'][0]['shapes']};self.assertEqual({s.name for s in shapes},set(expected))
            self.assertEqual(next(p['request']for p in self.plain['cases']if p['label']==c['label']),r)
            for i,s in enumerate(shapes):
                n=expected[s.name];self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(s.electrical_phase,n['attributes']);self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(len(s.segments),len(n['segments']))
                for a,b in zip(s.segments,n['segments']):self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits'])

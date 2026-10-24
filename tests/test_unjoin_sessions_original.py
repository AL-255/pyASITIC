"""Complete unchanged-original models after splitting both device halves."""
import gzip,hashlib,json,struct
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle
import test_spatial_sessions_original as spatial


class OriginalUnjoinSessionTests(spatial.OriginalSpatialSessionTests):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'unjoin_sessions_original.json.gz').read_bytes()));cls.plain=json.loads(gzip.decompress((root/'unjoin_plain_outcomes_original.json.gz').read_bytes()))
        assert len(cls.fixture['cases'])==8 and len(cls.plain['cases'])==9
        for f in(cls.fixture,cls.plain):
            for name,digest in f['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest

    def test_complete_original_descriptors_and_empty_analysis_fault(self):
        self.assertEqual({c['label']for c in self.plain['cases']if c['produced_model']},{c['label']for c in self.fixture['cases']})
        failed=[c for c in self.plain['cases']if not c['produced_model']];self.assertEqual(len(failed),1);c=failed[0];self.assertEqual((c['label'],c['returncode']),('wire/empty/pi2',-11))
        with self.assertRaisesRegex(ValueError,'contains no segments'):handle(c['request'])
        for c in self.fixture['cases']:
            self.assertEqual(next(p['request']for p in self.plain['cases']if p['label']==c['label']),c['request']);r=c['request'];shapes,links=_shapes(r,Technology.from_text(r['technology']),with_links=True);expected={s['name']:s for s in c['geometry_states'][0]['shapes']};self.assertEqual({s.name for s in shapes},set(expected))
            for i,s in enumerate(shapes):
                n=expected[s.name];self.assertEqual(struct.pack('<2d',*s.origin).hex(),n['origin_bits']);self.assertEqual(s.electrical_phase,n['attributes']);self.assertEqual(shapes[links[i]].name if links[i]is not None else None,n['partner']);self.assertEqual(len(s.segments),len(n['segments']))
                for a,b in zip(s.segments,n['segments']):self.assertEqual(struct.pack('<18d',*(v for p in a.points for v in p)).hex(),b['coordinates_bits'])

    def test_actual_via_stamps_and_defined_matrix_boundary(self):
        from reasitic.vias import stamp as stamp_vias
        from reasitic.bridge import _frequency
        root=Path(__file__).parent/'fixtures';f=json.loads(gzip.decompress((root/'unjoin_vias_original.json.gz').read_bytes()));self.assertEqual(hashlib.sha256((root/'unjoin_sessions_original.json.gz').read_bytes()).hexdigest(),f['parent_sha256']);self.assertEqual(len(f['cases']),2)
        for c in f['cases']:
            model=next(m for m in self.fixture['cases']if m['label']==c['label']);tech=Technology.from_text(model['request']['technology']);n=c['n'];self.assertEqual((c['return_status'],c['control_before'],c['control_after']),(1,0x37f,0x37f));self.assertEqual(c['stride'],n)
            records=[bytes.fromhex(s)for s in c['segments']];vias=[s for s in records if struct.unpack_from('<i',s,0xdc)[0]>=len(tech.metals)];self.assertEqual(len(vias),len(c['indices']));self.assertIn(n,c['indices'])
            defined=bytearray.fromhex(c['before'])
            for s,k,before,after in zip(vias,c['indices'],c['cell_before'],c['cell_after']):
                self.assertEqual((before['index'],after['index']),(k,k));metal=struct.unpack_from('<i',s,0xdc)[0];via=tech.vias[metal-len(tech.metals)];z=struct.unpack('<2d',bytes.fromhex(before['words']));start,end=(struct.unpack_from('<d',s,o)[0]for o in(16,40));nx,ny=struct.unpack_from('<2i',s,0xe0)
                actual=stamp_vias([[_frequency(model['request']),start,end,via.width,via.resistance,nx,ny,*z]])[0];self.assertEqual(struct.pack('<2d',actual.real,actual.imag).hex(),after['words'])
                if k<n:defined[(k*n+k)*16:(k*n+k+1)*16]=bytes.fromhex(after['words'])
                else:
                    node=c['node'];offset=after['address']-node['cap_address'];self.assertEqual(offset,16*(n-1));self.assertEqual(bytes.fromhex(node['capacitance'])[offset:offset+16].hex(),after['words']);self.assertNotEqual(before['words'],after['words'])
            self.assertEqual(defined.hex(),c['after'])

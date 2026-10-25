"""Every original shunt model, node matrix, filament group and upper assembly."""
import gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_shunt_models_original import run as models
from audit_shunt_assembly_original import run as assembly
from reasitic.bridge import handle


class ShuntSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture,cls.plain,cls.assembly=(json.loads(gzip.decompress((ROOT/('tests/fixtures/'+name+'.json.gz')).read_bytes()))for name in('shunt_sessions_original','shunt_plain_outcomes_original','shunt_assembly_original'))

    def test_all_selected_plain_outcomes_provenance_and_complete_node_inputs(self):
        import capture_shunt_assembly_original as capture
        self.assertEqual(self.assembly['gdb_commands'],capture.COMMANDS)
        for f in(self.fixture,self.plain,self.assembly):
            self.assertEqual(len(f['cases']),12)
            for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual({c['label']for c in self.plain['cases']if c['produced_model']},{c['label']for c in self.fixture['cases']})
        for c in self.fixture['cases']:
            p=next(p for p in self.plain['cases']if p['label']==c['label']);a=next(a for a in self.assembly['cases']if a['label']==c['label']);self.assertEqual(p['returncode'],0);self.assertEqual(len(c['nodes']),2)
            for key in('request','script','stdin'):self.assertEqual(c[key],p[key]);self.assertEqual(c[key],a[key])
            for node in c['nodes']:
                for key in('capacitance','inductance'):self.assertEqual(len(bytes.fromhex(node[key])),16*node['size']**2)
            self.assertEqual((a['control_before'],a['control_after']),(0x37f,0x37f))
            plan=handle(dict(c['request'],action='mesh',model=c['request']['action']))
            self.assertEqual((plan['filaments'],plan['segments']),(a['n'],a['group_count']))

    def test_complete_original_models_ports_and_both_node_matrices(self):
        report=models(self.fixture);self.assertEqual(report['cases'],12);self.assertEqual(report['differences'],0,json.dumps([r for r in report['results']if r['differences']],indent=2))

    def test_original_upper_entries_and_actual_production_filaments_groups_materials(self):
        report=assembly(self.assembly);self.assertEqual(report['cases'],12);self.assertEqual(report['differences'],0,json.dumps([r for r in report['results']if r['upper']['differences']or r['production']['differences']],indent=2))


if __name__=='__main__':unittest.main()

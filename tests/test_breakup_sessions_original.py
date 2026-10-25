"""Complete original electrical results on converted individual segments."""
import gzip,hashlib,json,unittest
from pathlib import Path
from reasitic.bridge import handle
from test_spatial_sessions_original import assert_original_models

ROOT=Path(__file__).resolve().parents[1]


class BreakupSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/breakup_sessions_original.json.gz').read_bytes()));cls.plain=json.loads(gzip.decompress((ROOT/'tests/fixtures/breakup_plain_outcomes_original.json.gz').read_bytes()))

    def test_all_selected_plain_outcomes_and_provenance(self):
        self.assertEqual(len(self.plain['cases']),8);self.assertEqual(len(self.fixture['cases']),7)
        for f in(self.fixture,self.plain):
            for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual({c['label']for c in self.plain['cases']if c['produced_model']},{c['label']for c in self.fixture['cases']})
        for c in self.fixture['cases']:
            p=next(p for p in self.plain['cases']if p['label']==c['label']);self.assertEqual(p['returncode'],0)
            for key in('request','script','stdin'):self.assertEqual(c[key],p[key])
        faults=[c for c in self.plain['cases']if not c['produced_model']];self.assertEqual(len(faults),1);c=faults[0];self.assertEqual((c['label'],c['returncode']),('square/via/pi2',-11))
        with self.assertRaises(ValueError):handle(c['request'])

    def test_complete_original_models_ports_and_node_matrices(self):
        assert_original_models(self,self.fixture['cases'])


if __name__=='__main__':unittest.main()

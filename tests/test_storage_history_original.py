"""Earlier memory preconditions and continuous source stores through node entry."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_storage_history_original import compare
from project_initial_storage_memory_original import expand


class StorageHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent_raw=(ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz').read_bytes()
        cls.parent=json.loads(gzip.decompress(cls.parent_raw))
        cls.initial=json.loads(gzip.decompress((ROOT/'tests/fixtures/initial_storage_memory_original.json.gz').read_bytes()))

    def test_all_earlier_heap_bytes_match_original_manifests_without_later_selection(self):
        fixture=self.initial;self.assertEqual(fixture['parent_sha256'],hashlib.sha256(self.parent_raw).hexdigest())
        self.assertEqual(fixture['full_capture_sha256'],self.parent['full_capture_sha256'])
        self.assertEqual(len(fixture['cases']),130);self.assertEqual(len(fixture['pages']),860)
        for key,data in fixture['pages'].items():
            raw=bytes.fromhex(data);self.assertEqual(len(raw),4096);self.assertEqual(hashlib.sha256(raw).hexdigest(),key)
        total=0
        for case,entry in zip(self.parent['cases'],fixture['cases']):
            with self.subTest(label=case['label'],mode=case['cache_mode']):
                self.assertEqual((case['label'],case['cache_mode']),(entry['label'],entry['cache_mode']))
                state=next(s for s in case['allocator_states']if s['label']=='scope');regions=expand(fixture,entry)
                manifests=[dict(address=p,size=len(data),sha256=hashlib.sha256(data).hexdigest())for p,data in regions]
                self.assertEqual(manifests,state['full_heap_manifest']);total+=sum(len(data)for p,data in regions)
        self.assertEqual(total,35676160)

    def test_portable_first_complete_native_histories_without_via_seed(self):
        # Every larger case is required by the separate packaged full replay.
        for case,entry in zip(self.parent['cases'][:2],self.initial['cases'][:2]):
            with self.subTest(mode=case['cache_mode']):
                result=compare(case,expand(self.initial,entry));self.assertEqual(result['differences'],[])
                self.assertEqual((result['allocations_checked'],result['stores_checked'],result['faults_checked']),(24,1,0))
                self.assertEqual((result['cap_input_words_checked'],result['ind_input_words_checked'],result['cap_words_checked'],result['ind_words_checked']),(2,2,2,2))

    def test_changed_observed_via_word_is_not_a_calculation_input(self):
        case=copy.deepcopy(self.parent['cases'][0]);event=next(e for e in case['events']if e['kind']=='via_write')
        raw=bytearray.fromhex(event['before']);raw[0]^=1;event['before']=raw.hex()
        result=compare(case,expand(self.initial,self.initial['cases'][0]))
        self.assertEqual([d['kind']for d in result['differences']],['before-store'])
        self.assertEqual(result['stores_checked'],1)

    def test_missing_initial_padding_is_unknown_instead_of_zero(self):
        result=compare(self.parent['cases'][0],[])
        self.assertTrue(any(d['kind']in ('unknown-target','unknown-allocator-read')for d in result['differences']))

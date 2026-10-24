"""Source cache metadata stores before via entry and continuous read backing."""
import copy,gzip,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_cache_stores_original import compare
from reasitic.heap import Heap
from reasitic.memory import Memory,MemoryFault


class CacheStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz').read_bytes()))

    def test_all_cache_words_from_source_history_at_every_pre_via_boundary(self):
        self.assertEqual(len(self.fixture['cases']),130)
        results=[compare(case)for case in self.fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        for key,expected in (('boundaries',390),('cache_words_checked',47304),('events_checked',16764),('allocations_checked',8902)):
            self.assertEqual(sum(r[key]for r in results),expected)

    def test_read_back_handoff_keeps_generated_bytes_and_damaged_links(self):
        case=self.fixture['cases'][0];result,heap,memory=compare(case,return_state=True);self.assertEqual(result['differences'],[])
        key=case['allocator_states'][0]['tcache_key'];original=[list(chain)for chain in heap.tcache]
        before=memory.read(heap.cache_address,384)
        # The handoff cannot substitute another snapshot's memory or key.
        with self.assertRaisesRegex(ValueError,'continue'):heap.attach_cache_memory(Memory(heap.address_space),key)
        with self.assertRaisesRegex(ValueError,'continue'):heap.attach_cache_memory(memory,key^1)
        heap.attach_cache_memory(memory,key)
        self.assertEqual(heap.tcache,original);self.assertEqual(memory.read(heap.cache_address,384),before)
        with self.assertRaisesRegex(ValueError,'before'):heap.observe_cache_stores(memory,key)
        index=next(i for i,chain in enumerate(original)if chain);entry=original[index][0]+8
        # A subsequent guest store is observed by reads, rather than repaired
        # from the old logical chain. The address is deliberately unmapped.
        bad=0x2000;self.assertFalse(heap.address_space.contains(bad,4))
        memory.put_u32(entry,bad^(entry>>12));chains,errors=heap.cache_state()
        self.assertEqual(chains[index],[entry-8]);self.assertTrue(any(error.get('address')==bad and error['reason']=='unmapped'for error in errors))

    def test_store_observation_preserves_os_mapping_zero_and_release_effects(self):
        case=next(c for c in self.fixture['cases']if c['label']=='square/16/filaments'and c['cache_mode']=='cold')
        state=next(s for s in case['allocator_states']if s['label']=='via_entry')
        heap=Heap(state);memory=Memory(heap.address_space);heap.observe_cache_stores(memory,state['tcache_key'])
        mapped=state['mapped_chunks'][0];address=mapped['address']+8
        memory.write(address,b'abcdefgh');heap.free(address)
        with self.assertRaises(MemoryFault):memory.read(address,8)
        replacement=heap.malloc(mapped['request']+8192)
        self.assertLessEqual(replacement,address);self.assertEqual(memory.read(address,8),b'\0'*8)

    def test_incomplete_initial_cache_is_not_reconstructed_as_valid(self):
        state=copy.deepcopy(self.fixture['cases'][0]['allocator_states'][0]);state['tcache_counts'][0]+=1
        heap=Heap(state);memory=Memory(heap.address_space)
        with self.assertRaisesRegex(ValueError,'complete'):heap.observe_cache_stores(memory,state['tcache_key'])

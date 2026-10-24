"""Shared native via stores and tcache bytes, including damaged chains."""
import collections,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_allocator_original as arena
import capture_shared_memory_original as capture
from audit_shared_heap_original import compare,seed,normalized_errors
from reasitic.heap import Heap,AddressSpace
from reasitic.memory import Memory,MemoryFault,UnknownMemory,ComplexView
from reasitic.vias import stamp_memory


class SharedHeapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shared_heap_original.json.gz').read_bytes()))

    def test_all_selected_inputs_and_exact_projection_fields(self):
        fixture=self.fixture;parent_path=ROOT/'tests/fixtures/allocator_mappings_original.json.gz';parent=json.loads(gzip.decompress(parent_path.read_bytes()))
        self.assertEqual(fixture['shared_parent_sha256'],hashlib.sha256(parent_path.read_bytes()).hexdigest())
        self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],arena.commands(Path(directory),capture.OBSERVER))
        for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(len(fixture['cases']),130);states=0
        for cold,warm in zip(fixture['cases'][::2],fixture['cases'][1::2]):
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['cache_after_plain'],warm['initial_cache'])
        for case,previous in zip(fixture['cases'],parent['cases']):
            with self.subTest(label=case['label'],mode=case['cache_mode']):
                for key in ('label','cache_mode','request','script','stdin','variant'):self.assertEqual(case[key],previous[key])
                commands=fixture['gdb_commands'].encode();self.assertEqual(case['initial_files']['capture.gdb'],dict(size=len(commands),sha256=hashlib.sha256(commands).hexdigest()))
                for key in ('process.tek','input.asit','answers.txt'):self.assertEqual(case['initial_files'][key],previous['initial_files'][key])
                for output in (case['stdout'],case['plain']['stdout']):self.assertEqual('Generating data at'in output,case['cache_mode']=='cold')
                for state in case['allocator_states']:
                    states+=1;heap=Heap(state);memory=Memory(heap.address_space);seed(memory,state);heap.attach_cache_memory(memory,state['tcache_key'])
                    self.assertEqual(heap.tcache,[[p-8 for p in chain]for chain in state['tcache']])
                    self.assertEqual(normalized_errors(heap.cache_state()[1]),normalized_errors(state['errors']))
                    for chunk in state['chunks']:
                        self.assertEqual(memory.read(chunk['address'],8),struct.pack('<2I',chunk['prev_size'],chunk['size_word']))
                        self.assertEqual(len(memory.read(chunk['address']+8,8)),8)
                    self.assertTrue(state['full_heap_manifest']);self.assertNotIn('heap_regions',state)
        self.assertEqual(states,389)

    def test_all_native_stores_aliases_cache_bytes_and_faults(self):
        results=[compare(case)for case in self.fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        for field,value in (('allocations_checked',3117),('events_checked',12877),('stores_checked',131),('faults_checked',1),('cache_boundaries',259),('cache_words_checked',39524),('cap_words_checked',118948)):
            self.assertEqual(sum(result[field]for result in results),value)
        errors=[(r['label'],r['cache_mode'],e['address'])for r in results for e in r['predicted_cache_errors']]
        self.assertEqual(errors,[('square/1/filaments','cold',0x8100),('pilot-width3/1/filaments','warm',0x8100),('pilot-boundary/1/filaments','cold',0x8100),('pilot-boundary/1/filaments','warm',0x811b)])
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:123,-6:5,-11:2})

    def test_existing_balun_native_input_reinversion(self):
        for case in self.fixture['cases'][-4:]:
            with self.subTest(label=case['label'],mode=case['cache_mode']):
                result=compare(case,invert=True);self.assertEqual(result['differences'],[])
                self.assertEqual(result['ind_words_checked'],2*case['node']['size']**2)

    def test_guest_aliases_unknown_bytes_and_partial_native_store_order(self):
        case=json.loads((ROOT/'tests/fixtures/vias_original.json').read_text())['cases'][0]
        record=case['input'][:5]+[int(value)for value in case['input'][5:7]]
        # The reference stores the real component before loading imaginary.
        space=AddressSpace([dict(start=0x1000,end=0x1008)]);memory=Memory(space)
        with self.assertRaises(UnknownMemory):memory.read(0x1000,8)
        memory.write(0x1000,struct.pack('<d',case['input'][7]))
        with self.assertRaises(MemoryFault)as fault:stamp_memory(memory,0x1000,record)
        self.assertEqual(fault.exception.address,0x1008)
        self.assertEqual(memory.read(0x1000,8).hex(),case['output_bits'][0])
        space.ranges.append((0x1008,0x1040));memory.zero(0x1008,0x38)
        first=ComplexView(memory,0x1000,1);alias=ComplexView(memory,0x1010,1)
        first.set(1,0,3+4j);self.assertEqual(first.get(1,0),alias.get(0,0))
        memory.forget(0x1010,16)
        with self.assertRaises(UnknownMemory):alias.get(0,0)
        inactive=record.copy();inactive[1:3]=[0.,0.]
        self.assertFalse(stamp_memory(memory,0x8000,inactive))

    def test_released_mapping_contents_are_discarded_and_new_pages_are_zero(self):
        case=next(c for c in self.fixture['cases']if c['label']=='square/16/filaments'and c['cache_mode']=='cold')
        state=next(s for s in case['allocator_states']if s['label']=='via_entry')
        heap=Heap(state);memory=Memory(heap.address_space);seed(memory,state);heap.attach_cache_memory(memory,state['tcache_key'])
        mapped=state['mapped_chunks'][0];address=mapped['address']+8
        memory.write(address,b'abcdefgh');heap.free(address)
        with self.assertRaises(MemoryFault):memory.read(address,8)
        # A larger new anonymous mapping overlaps the released range.
        replacement=heap.malloc(mapped['request']+8192)
        self.assertLessEqual(replacement,address);self.assertEqual(memory.read(address,8),b'\0'*8)

"""Source-derived contact/cache history and continuous shared-memory state."""
import collections,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_cap_prelude_original as capture
import capture_cap_prelude_shared_original as combined_capture
import capture_cap_prelude_modes_original as modes_capture
import capture_trailing_via_heap_original as lifetime
from audit_cap_prelude_original import compare
from audit_cap_prelude_shared_original import compare as combined_compare


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class CapPreludeTests(unittest.TestCase):
    def test_complete_capture_inputs_and_cache_pair_provenance(self):
        for name,observer,builder in (('cap_prelude_original.json.gz',capture.OBSERVER,capture.commands),('cap_prelude_shared_original.json.gz',combined_capture.OBSERVER,capture.commands)):
            fixture=load(name);self.assertEqual(len(fixture['cases']),130)
            self.assertEqual(fixture['allocator_provenance']['observer'],observer)
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],builder(Path(directory),observer))
            for parent,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest(),digest)
            for i,job in enumerate(lifetime.jobs()):
                cold,warm=fixture['cases'][2*i:2*i+2]
                self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['cache_after_plain'],warm['initial_cache'])
                for case,mode in ((cold,'cold'),(warm,'warm')):
                    with self.subTest(fixture=name,label=job['label'],mode=mode):
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode);self.assertEqual((case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0))
                        self.assertEqual(case['allocator_states'][0]['label'],'contacts_entry')
                        self.assertEqual(case['allocator_states'][0]['io_abi'],dict(file_plus=152,wide_data=140,lock=12,buffer_default=8192,filesystem_block_size=4096))
                        for filename,text in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                            self.assertEqual(case['initial_files'][filename],dict(size=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest()))
                        for output in (case['stdout'],case['plain']['stdout']):self.assertEqual('Generating data at'in output,mode=='cold')
        allocation=load('cap_prelude_original.json.gz');combined=load('cap_prelude_shared_original.json.gz')
        self.assertEqual(allocation['prelude_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/allocator_mappings_original.json.gz').read_bytes()).hexdigest())
        for parent,digest in combined['prelude_shared_parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest(),digest)

    def test_every_prelude_request_address_free_and_contact_owner(self):
        fixture=load('cap_prelude_original.json.gz');results=[compare(case)for case in fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        self.assertEqual(sum(r['events']for r in results),7732);self.assertEqual(sum(r['allocations_checked']for r in results),6302)
        self.assertEqual(sum(r['contacts']+r['contact_groups']for r in results),4872)
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in fixture['cases']),{0:124,-6:5,-11:1})

    def test_continuous_heap_through_all_selected_node_or_fault_boundaries(self):
        fixture=load('cap_prelude_shared_original.json.gz');results=[combined_compare(case)for case in fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        self.assertEqual(sum(r['prefix']['events']+r['body']['events_checked']for r in results),20609)
        self.assertEqual(sum(r['prefix']['allocations_checked']+r['body']['allocations_checked']for r in results),9419)
        self.assertEqual(sum(r['body']['stores_checked']for r in results),131);self.assertEqual(sum(r['body']['faults_checked']for r in results),1)
        self.assertEqual(sum(r['body']['via_records_checked']for r in results),132)
        self.assertEqual(sum(r['body']['via_index_words_checked']for r in results),132)
        self.assertEqual(sum(r['body']['cap_words_checked']for r in results),118948)
        errors=[(r['label'],r['cache_mode'],e['address'])for r in results for e in r['body']['predicted_cache_errors']]
        self.assertEqual(errors,[('pilot-width3/1/filaments','cold',0x8100),('pilot-width3/1/filaments','warm',0x8100),('pilot-boundary/1/filaments','warm',0x8100)])
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in fixture['cases']),{0:128,-6:1,-11:1})

    def test_second_native_invocations_memory_cache_and_disabled_io(self):
        fixture=load('cap_prelude_modes_original.json.gz');self.assertEqual(len(fixture['cases']),4)
        self.assertEqual(fixture['reference'],modes_capture.REFERENCE)
        self.assertEqual(fixture['allocator_provenance']['observer'],modes_capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],modes_capture.commands(Path(directory)))
        self.assertEqual(fixture['prelude_modes_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/cap_prelude_original.json.gz').read_bytes()).hexdigest())
        for i,job in enumerate(modes_capture.jobs()):
            for case in fixture['cases'][2*i:2*i+2]:
                with self.subTest(label=case['label'],mode=case['cache_mode']):
                    for key in ('label','request','script','stdin','prelude_cache_mode'):self.assertEqual(case[key],job[key])
                    self.assertEqual((case['plain']['returncode'],case['signal']),(0,0));self.assertEqual(compare(case)['differences'],[])
                    state=case['allocator_states'][0]['cache_state'];self.assertEqual(state['visit'],2)
                    self.assertEqual(state['enabled'],case['prelude_cache_mode']=='memory')
                    if case['prelude_cache_mode']=='memory':self.assertEqual(struct.unpack('<d',bytes.fromhex(state['frequency_bits']))[0],250e6)
        results=[compare(case)for case in fixture['cases']]
        self.assertEqual(sum(r['events']for r in results),68);self.assertEqual(sum(r['allocations_checked']for r in results),38)

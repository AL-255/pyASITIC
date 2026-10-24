"""Mapped ASITIC allocations and independent native libc allocation histories."""
import collections,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_allocator_original as arena
import capture_mapping_allocator_original as capture
import capture_mmap_sequences_native as sequences
import capture_trailing_via_heap_original as lifetime
from audit_allocator_original import compare,state_differences
from audit_trailing_via_heap import compare as compare_lifetimes
from reasitic.heap import Heap


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class OriginalMappingHeapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=load('allocator_mappings_original.json.gz')

    def test_complete_original_inputs_cache_states_and_policy_provenance(self):
        fixture=self.fixture;old=load('allocator_state_original.json.gz')
        self.assertEqual(fixture['mapping_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/allocator_state_original.json.gz').read_bytes()).hexdigest())
        for key in ('libc_build_id','libc_sha256','debug_sha256','parent_sha256'):
            self.assertEqual(fixture['allocator_provenance'][key],old['allocator_provenance'][key])
        self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],arena.commands(Path(directory),capture.OBSERVER))
        for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(len(fixture['cases']),130)
        for i,job in enumerate(lifetime.jobs()):
            cold,warm=fixture['cases'][2*i:2*i+2]
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['cache_after_plain'],warm['initial_cache'])
            for case,mode in ((cold,'cold'),(warm,'warm')):
                with self.subTest(label=job['label'],mode=mode):
                    for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                    self.assertEqual(case['cache_mode'],mode);self.assertEqual(case['pending'],0)
                    for name,text in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                        self.assertEqual(case['initial_files'][name],dict(size=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest()))
                    for output in (case['stdout'],case['plain']['stdout']):self.assertEqual('Generating data at'in output,mode=='cold')
                    self.assertEqual(compare_lifetimes(case),[])
                    for state in case['allocator_states']:
                        policy=state['mapping_policy'];self.assertEqual(policy['personality'],0x440000)
                        self.assertEqual((policy['page_size'],policy['stack_limit'],policy['stack_guard_gap_pages'],policy['legacy_va_layout'],policy['mmap_min_addr']),(4096,8388608,256,0,65536))
                        self.assertEqual(policy['kernel_release'],'7.0.0-38-generic');self.assertIn('[madvise]',policy['transparent_hugepage'])

    def test_all_addresses_ranges_parameters_headers_and_fault_target(self):
        results=[compare(case)for case in self.fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):
                self.assertEqual(result['differences'],[]);self.assertIsNone(result['system_boundary'])
        self.assertEqual(sum(r['allocations_checked']for r in results),3117)
        self.assertEqual(sum(r['events_checked']for r in results),12877)
        self.assertEqual(collections.Counter(b for r in results for b in r['boundaries_checked']),{'scope':130,'via_entry':130,'node':129})
        self.assertEqual(sum(len(r['targets'])for r in results),132)
        unmapped=[(r['label'],r['cache_mode'],t['index'])for r in results for t in r['targets']if not t['mapped']]
        self.assertEqual(unmapped,[('square/64/contacts','cold',64)])
        errors=[(r['label'],r['cache_mode'],e['boundary'],e['section'])for r in results for e in r['native_metadata_errors']]
        self.assertEqual(errors,[('square/1/filaments','cold','node','tcache.1'),('pilot-width3/1/filaments','warm','node','tcache.1'),('pilot-boundary/1/filaments','warm','node','tcache.1')])
        # Errors remain strict-audit failures: matching addresses does not
        # claim that actual numerical writes to free-list memory are modeled.
        self.assertEqual(sum(bool(r['native_metadata_errors'])for r in results),3)
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:123,-6:5,-11:2})


class NativeMmapHistoryTests(unittest.TestCase):
    def test_native_repeated_mapping_holes_thresholds_and_arena_interleaving(self):
        fixture=load('mmap_sequences_native.json.gz');original=load('allocator_mappings_original.json.gz')
        self.assertEqual(fixture['source'],sequences.source());self.assertEqual(fixture['startup_source'],sequences.START)
        self.assertEqual(fixture['observer'],capture.OBSERVER);self.assertEqual(fixture['libc_build_id'],arena.BUILD_ID)
        for key in ('libc_sha256','debug_sha256'):self.assertEqual(fixture[key],original['allocator_provenance'][key])
        self.assertEqual(len(fixture['cases']),6);events=0;allocations=0
        for ordinal,(case,job)in enumerate(zip(fixture['cases'],sequences.jobs())):
            with self.subTest(label=case['label']):
                self.assertEqual(case['label'],job['label']);self.assertEqual(case['operations'],job['operations'])
                directory=case['commands'].splitlines()[0].split('set debug-file-directory ',1)[1]
                self.assertEqual(case['commands'],sequences.commands(Path(directory),ordinal))
                self.assertEqual((case['plain']['returncode'],case['exit_code']),(0,0))
                self.assertEqual(len(case['states']),len(case['operations'])+1);self.assertEqual(len(case['events']),len(case['operations']))
                heap=Heap(case['states'][0]);addresses={}
                for op,observed,state in zip(case['operations'],case['events'],case['states'][1:]):
                    events+=1;self.assertEqual(op['kind'],observed['kind']);self.assertEqual(op['slot'],observed['slot'])
                    if op['kind']=='allocate':
                        allocations+=1;self.assertEqual(op['request'],observed['request'])
                        address=heap.malloc(op['request']);self.assertEqual(address,observed['address']);addresses[op['slot']]=address
                    else:
                        address=addresses.pop(op['slot']);self.assertEqual(address,observed['address']);heap.free(address)
                    self.assertEqual(state['errors'],[]);self.assertEqual(state_differences(heap,state),[])
                self.assertEqual(addresses,{})
        self.assertEqual((events,allocations),(58,29))
        repeated=fixture['cases'][0]['states']
        self.assertEqual(len(repeated[1]['mapped_chunks']),1);self.assertEqual(repeated[3]['mapped_chunks'],[])
        self.assertGreater(repeated[2]['parameters']['mmap_threshold'],repeated[0]['parameters']['mmap_threshold'])
        holes=fixture['cases'][1]['events'];self.assertGreaterEqual(holes[4]['address'],holes[1]['address']);self.assertLess(holes[4]['address'],holes[1]['address']+900000)

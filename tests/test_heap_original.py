"""Native allocator provenance and exact supported address/free-list prefixes.

The separate strict audit also requires the unresolved mmap and damaged-list
cases; these prefix tests do not declare those complete.
"""
import collections,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_allocator_original as capture
import capture_trailing_via_heap_original as lifetime
from audit_allocator_original import compare
from audit_trailing_via_heap import compare as compare_lifetimes


class OriginalHeapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/allocator_state_original.json.gz').read_bytes()))

    def test_all_inputs_cache_pairs_and_symbol_provenance(self):
        fixture=self.fixture;provenance=fixture['allocator_provenance']
        self.assertEqual(provenance['libc_build_id'],capture.BUILD_ID)
        self.assertEqual(provenance['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        self.assertEqual(provenance['debug_sha256'],'7c6519a15e10cad42658418fd3c5654c773f1c4160d1d93aa00dec2c6690061e')
        self.assertEqual(provenance['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/trailing_via_heap_original.json.gz').read_bytes()).hexdigest())
        self.assertEqual((provenance['pointer_bytes'],provenance['alignment']),(4,16))
        self.assertEqual(provenance['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
        for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        jobs=list(lifetime.jobs());self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(len(jobs),65)
        for i,job in enumerate(jobs):
            cold,warm=fixture['cases'][2*i:2*i+2]
            for case,mode in ((cold,'cold'),(warm,'warm')):
                with self.subTest(label=job['label'],mode=mode):
                    for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                    self.assertEqual(case['cache_mode'],mode);self.assertEqual(case['pending'],0)
                    for name,text in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                        self.assertEqual(case['initial_files'][name],dict(size=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest()))
                    self.assertEqual('Generating data at'in case['stdout'],mode=='cold')
                    self.assertEqual('Generating data at'in case['plain']['stdout'],mode=='cold')
                    self.assertEqual(compare_lifetimes(case),[])
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['initial_cache'],warm['cache_after_plain'])

    def test_raw_arena_headers_and_every_observed_state(self):
        states=0;errors=[]
        for case in self.fixture['cases']:
            self.assertEqual([s['label']for s in case['allocator_states']],['scope','via_entry']+(['node']if case['node']else []))
            for state in case['allocator_states']:
                states+=1;raw=bytes.fromhex(state['arena_bytes']);self.assertEqual(len(raw),1116)
                word=lambda offset:struct.unpack_from('<I',raw,offset)[0]
                self.assertEqual(word(56),state['top']);self.assertEqual(word(60),state['last_remainder']);self.assertEqual(word(8),state['have_fastchunks'])
                chunks={c['address']:c for c in state['chunks']};self.assertIn(state['top'],chunks)
                for i,chain in enumerate(state['bins']):
                    head=state['arena_address']+56+8*i
                    self.assertEqual(word(64+8*i),chain[0]if chain else head);self.assertEqual(word(68+8*i),chain[-1]if chain else head)
                    for p in chain:
                        self.assertIn(p,chunks);following=chunks[p+(chunks[p]['size_word']&~7)]
                        self.assertEqual(following['size_word']&1,0);self.assertEqual(following['prev_size'],chunks[p]['size_word']&~7)
                for i,chain in enumerate(state['fastbins']):
                    self.assertEqual(word(12+4*i),chain[0]if chain else 0)
                    for p in chain:self.assertEqual(((chunks[p]['size_word']&~7)>>3)-2,i)
                for i,chain in enumerate(state['tcache']):
                    self.assertEqual(len(chain),state['tcache_counts'][i])
                    for p in chain:self.assertEqual((p%16,chunks[p-8]['size_word']&~7),(0,16+16*i))
                errors.extend((case['label'],case['cache_mode'],state['label'],e['section'])for e in state['errors'])
        self.assertEqual(states,389)
        self.assertEqual(errors,[('square/1/filaments','warm','node','tcache.1'),('pilot-width3/1/filaments','warm','node','tcache.1')])

    def test_exact_arena_prefixes_with_explicit_unresolved_cases(self):
        results=[compare(c)for c in self.fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):
                self.assertEqual(result['differences'],[])
                if result['system_boundary']:self.assertIn('mmap required',result['system_boundary']['reason'])
        self.assertEqual(sum(r['allocations_checked']for r in results),2772)
        self.assertEqual(sum(r['events_checked']for r in results),9900)
        self.assertEqual(collections.Counter(b for r in results for b in r['boundaries_checked']),{'scope':130,'via_entry':110,'node':110})
        self.assertEqual(sum(bool(r['system_boundary'])for r in results),20)
        self.assertEqual(sum(bool(r['native_metadata_errors'])for r in results),2)
        # Both previously failing balun jobs have complete placement matches.
        # Their electrical solves still need derived prelude state and writes.
        for result in results[-4:]:
            self.assertIsNone(result['system_boundary']);self.assertEqual(result['boundaries_checked'],['scope','via_entry','node'])

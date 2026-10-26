"""Independent complete caller/malloc targets and earlier input causality."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_malloc_storage_original as capture
from audit_malloc_storage_original import compare,engine
from audit_loader_lookup_original import data
from reasitic.memory import UnknownMemory


class MallocStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/malloc_storage_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['allocation_calls'])

    def test_every_original_history_and_complete_guarded_capture(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['malloc_storage_provenance']['observer'],capture.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['allocation_calls']:
                self.assertEqual(set(call),{'entry','malloc','allocated','return'});a=call['entry'];self.assertTrue(a['profile']['malloc_abi'])
                self.assertLessEqual(set(a['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                for point in call.values():
                    self.assertIn('heap',point)
                    for region in point['regions']:data(f,region)
                s=a['registers']['esp'];stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(sum(not c['allocation_calls']for c in f['cases']),133)

    def test_all_native_regions_registers_fp_and_heap_boundaries(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in (('operations_checked',3),('words_checked',605328),('registers_checked',51),('fp_bytes_checked',7320),('heap_boundaries_checked',3)):
            self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_malloc_results_are_assertions_only(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);b=c['allocation_calls'][0]['allocated'];s=b['registers']['esp'];address=s-16
        region=next(r for r in b['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region['sha256']=key
        b['registers']['eax']^=16;b['xstate']='00'+b['xstate'][2:];b['heap']['top']^=16
        kinds=collections.Counter(d['kind']for d in compare(f,c)['differences'])
        self.assertEqual(kinds['malloc-memory-word'],1);self.assertEqual(kinds['malloc-register'],1);self.assertEqual(kinds['malloc-fp-byte'],1);self.assertEqual(kinds['state'],1)
        b['regions'].pop();self.assertIn('malloc-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_earlier_caller_registers_and_request_drive_source(self):
        call=self.case['allocation_calls'][0];a=call['malloc'];h,m,storage=engine(self.fixture,a,call['entry']);registers=dict(a['registers'],ebx=0x12345678,ebp=0x76543210)
        storage.enter(registers);pointer=h.malloc(m.u32(registers['esp']+4));result=storage.returned(pointer)
        self.assertEqual(m.u32(registers['esp']-16),registers['ebx']);self.assertEqual(m.u32(registers['esp']-4),registers['ebp'])
        self.assertEqual(result['ebx'],registers['ebx']);self.assertEqual(result['ebp'],registers['ebp']);self.assertEqual(result['eax'],pointer)
        h,m,storage=engine(self.fixture,a,call['entry']);m.put_u32(registers['esp']+4,8192)
        storage.enter(registers);pointer=h.malloc(8192);result=storage.returned(pointer)
        self.assertEqual(result['eax'],pointer);self.assertEqual(h.chunks[pointer-8].size,8208)
        self.assertEqual(m.u32(pointer-4)&~7,8208)

    def test_missing_earlier_malloc_control_is_not_filled_from_later_state(self):
        call=self.case['allocation_calls'][0];a=copy.deepcopy(call['malloc']);h,m,storage=engine(self.fixture,a,call['entry']);m.forget(storage.got+0x78,4)
        with self.assertRaises(UnknownMemory):storage.enter(a['registers'])

    def test_every_additional_later_heap_field_remains_required(self):
        case=copy.deepcopy(self.case);target=case['allocation_calls'][0]['allocated']['heap']
        target['parameters']['top_pad']^=16;target['flags']^=1;target['tcache_counts'][0]+=1
        raw=bytearray.fromhex(target['arena_bytes']);raw[0]^=1;target['arena_bytes']=raw.hex();target['maps'][0]['permissions']='---p'
        target['event_count']+=1;target['errors'].append(dict(section='tcache.0',reason='injected'))
        kinds=collections.Counter(d['kind']for d in compare(self.fixture,case)['differences'])
        self.assertEqual(kinds['malloc-heap-field'],3);self.assertEqual(kinds['malloc-arena-image'],1)
        self.assertEqual(kinds['malloc-mappings'],1);self.assertEqual(kinds['malloc-observer-event-count'],1);self.assertEqual(kinds['malloc-additional-native-heap-error'],1)

    def test_native_corrupt_header_walk_is_preserved(self):
        call=self.case['allocation_calls'][0];a=call['malloc'];h,m,storage=engine(self.fixture,a,call['entry'])
        self.assertTrue([e for e in a['heap']['errors']if e['section']=='chunks'])
        storage.enter(a['registers']);pointer=h.malloc(m.u32(a['registers']['esp']+4));storage.returned(pointer)
        from audit_allocator_original import state_differences
        self.assertEqual(state_differences(h,call['allocated']['heap'],memory=m),[])


if __name__=='__main__':unittest.main()

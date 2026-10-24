"""Unchanged original pre-CAP workspace/stdio bytes and capture provenance."""
import collections,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_prelude_storage_original as capture
import capture_prelude_storage_extended_original as extended
from project_prelude_storage_original import expand_case
from audit_prelude_storage_original import compare
from reasitic.heap import AddressSpace
from reasitic.memory import Memory,UnknownMemory
from reasitic.file_buffer_storage import FileBytes,read_buffer,write_buffer


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class PreludeStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=load('prelude_storage_original.json.gz');cls.extended=load('prelude_storage_extended_original.json.gz')

    def test_complete_inputs_read_only_observers_and_lossless_storage_banks(self):
        for fixture,jobs,parent in ((self.original,list(capture.geometry.arena.lifetime.jobs()),'geometry_setup_original.json.gz'),(self.extended,list(extended.jobs()),'prelude_storage_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['prelude_storage_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            for bank in ('storage_pages','storage_blobs'):
                for key,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),key)
            for i,job in enumerate(jobs):
                cold,warm=fixture['cases'][2*i:2*i+2]
                self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain'])
                for entry,mode in ((cold,'cold'),(warm,'warm')):
                    case=expand_case(fixture,entry)
                    with self.subTest(label=job['label'],mode=mode):
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode)
                        self.assertEqual((case['setup_pending'],case['setup_interfaces'],case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0,0,0))
                        for label,regions in (('driver_entry',case['setup_context']['memory_regions']),('scope',case['prelude_final_heap'])):
                            state=next(s for s in case['allocator_states']if s['label']==label)
                            self.assertEqual([(r['address'],len(r['data'])//2)for r in regions],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
                        frees=[i for i,e in enumerate(case['prefix_events'])if e['kind']=='free']
                        self.assertEqual([r['event_index']for r in case['prelude_storage']],frees)
                        for record in case['prelude_storage']:
                            event=case['prefix_events'][record['event_index']];self.assertEqual(record['address'],event['address'])
                            allocation=next(e for e in reversed(case['prefix_events'][:record['event_index']])if e['kind']=='allocate'and e['address']==record['address'])
                            self.assertEqual(record['size'],allocation['request']);self.assertEqual(len(record['data']),2*record['size'])
                        for filename,text in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                            self.assertEqual(case['initial_files'][filename],dict(size=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest()))
        self.assertEqual(sum(len(c['prelude_storage'])for c in self.original['cases']),1430)
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.original['cases']),{0:123,-6:6,-11:1})
        self.assertEqual(self.original['full_capture_sha256'],'b36a0c4e32972ccbe60cd413712eba9b4ffb6488a4bcb4385f22840fe6e288eb')

    def test_all_small_native_square_and_rectangular_buffers_portably(self):
        reports=[compare(expand_case(self.extended,c))for c in self.extended['cases']]
        for report in reports:
            with self.subTest(label=report['label'],mode=report['cache_mode']):self.assertEqual(report['differences'],[])
        self.assertEqual(sum(r['workspaces_checked']for r in reports),30)
        self.assertEqual(sum(r['file_buffers_checked']for r in reports),4)
        self.assertEqual(sum(r['bytes_checked']for r in reports),27904)
        # Preserve the actual native plain crash and its non-UTF8 bytes. The
        # read-only observer stopped earlier, at node entry, without a fault.
        case=self.extended['cases'][2]
        self.assertEqual((case['plain']['returncode'],case['signal']),(-6,0));self.assertIsNotNone(case['node'])
        self.assertTrue(any(0xdc80<=ord(c)<=0xdcff for c in case['plain']['stdout']))
        raw=case['plain']['stdout'].encode('utf8','surrogateescape')
        self.assertEqual(raw.decode('utf8','surrogateescape'),case['plain']['stdout'])

    def test_expected_buffers_and_final_heap_do_not_seed_calculation(self):
        case=expand_case(self.extended,self.extended['cases'][0]);native=case['prelude_storage'][1]['data']
        self.assertEqual(case['prelude_storage'][1]['size'],256)
        changed=bytearray.fromhex(native);changed[0]^=1;case['prelude_storage'][1]['data']=changed.hex()
        case['prelude_final_heap']=None
        result=compare(case);self.assertEqual(len(result['differences']),1)
        self.assertEqual(result['differences'][0]['actual'],native[:16]);self.assertEqual(result['differences'][0]['offset'],0)

    def test_unknown_header_and_unused_tail_are_not_filled_with_zero(self):
        for operation in (write_buffer,read_buffer):
            memory=Memory(AddressSpace([dict(start=0,end=4096)]));memory.write(256,b'\xa5'*128)
            file=FileBytes([(None,4),(b'abcd',4)]);operation(memory,256,128,file)
            with self.assertRaises(UnknownMemory):memory.read(256,4)
            self.assertEqual(memory.read(260,4),b'abcd');self.assertEqual(memory.read(264,120),b'\xa5'*120)


if __name__=='__main__':unittest.main()

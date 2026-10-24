"""Defined native contact stores, unknown bytes, and later matrix numbering."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_contact_storage_original as capture
import capture_trailing_via_heap_original as lifetime
from audit_contact_storage_original import compare,ported_records
from audit_cap_prelude_original import compare as prelude
from reasitic.contact_storage import write_prepared,number_contacts,number_groups
from reasitic.heap import AddressSpace
from reasitic.memory import Memory,MemoryFault,UnknownMemory


class ContactStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/contact_storage_original.json.gz').read_bytes()))

    def test_every_selected_input_cache_state_and_read_only_observer(self):
        fixture=self.fixture;self.assertEqual(len(fixture['cases']),130)
        self.assertEqual(fixture['original_sha256'],lifetime.ORIGINAL_SHA256)
        self.assertEqual(fixture['legacy_sha256'],lifetime.LEGACY_SHA256)
        self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
        parent=ROOT/'tests/fixtures/cap_prelude_original.json.gz'
        self.assertEqual(fixture['contact_storage_parent_sha256'],hashlib.sha256(parent.read_bytes()).hexdigest())
        for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for i,job in enumerate(lifetime.jobs()):
            cold,warm=fixture['cases'][2*i:2*i+2]
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['initial_cache'],warm['cache_after_plain'])
            for case,mode in ((cold,'cold'),(warm,'warm')):
                with self.subTest(label=job['label'],mode=mode):
                    for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                    self.assertEqual(case['cache_mode'],mode);self.assertEqual((case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0))
                    self.assertEqual(case['events'][0]['control'],0x37f)
                    self.assertEqual([state['label']for state in case['contact_storage']],['prepared','numbered'])
                    for name,value in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                        self.assertEqual(case['initial_files'][name],dict(size=len(value.encode()),sha256=hashlib.sha256(value.encode()).hexdigest()))
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in fixture['cases']),{0:126,-6:3,-11:1})
        self.assertEqual([(c['label'],c['cache_mode'],c['signal'])for c in fixture['cases']if c['signal']],[('square/64/contacts','cold',11)])

    def test_all_prepared_and_numbered_bytes_from_predicted_allocations(self):
        results=[compare(case)for case in self.fixture['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        self.assertEqual(sum(r['objects_checked']for r in results),9744)
        # Exact byte/unknown counts also prevent silently weakening field masks.
        self.assertEqual(sum(r['bytes_checked']for r in results),558096)
        self.assertEqual(sum(r['unknown_bytes']for r in results),306528)

    def test_unwritten_group_bytes_and_unknown_incoming_index_are_preserved(self):
        probe=Memory(AddressSpace([dict(start=0x1000,end=0x1004)]));probe.write(0x1000,b'old!')
        with self.assertRaises(MemoryFault):probe.write_unknown(0x1000,8)
        self.assertEqual(probe.read(0x1000,4),b'old!')
        probe.write_unknown(0x1000,4)
        with self.assertRaises(UnknownMemory):probe.read(0x1000,4)
        case=next(c for c in self.fixture['cases']if c['label']=='square/2/contacts'and c['cache_mode']=='cold')
        report,heap,addresses=prelude(case,return_state=True);self.assertEqual(report['differences'],[])
        groups=ported_records(case);memory=Memory(heap.address_space)
        for i,group in enumerate(groups):
            memory.write(addresses[f'contact_group.{i}'],b'\xa5'*136)
            for j,contact in enumerate(group.contacts):memory.write(addresses[f'contact.{i}.{j}'],b'\x5a'*60)
        write_prepared(memory,groups,addresses)
        for i,group in enumerate(groups):
            address=addresses[f'contact_group.{i}']
            self.assertEqual(memory.read(address+len(group.name),80-len(group.name)),b'\xa5'*(80-len(group.name)))
            self.assertEqual(memory.read(address+124,4),b'\xa5'*4)
            for j,contact in enumerate(group.contacts):
                with self.assertRaises(UnknownMemory):memory.read(addresses[f'contact.{i}.{j}']+52,4)
        # Explicit caller history is copied as a word, then replaced by native
        # numbering. No captured temporary index initializes the guest records.
        write_prepared(memory,groups,addresses,history_index=0xdeadbeef)
        for i,group in enumerate(groups):
            for j,contact in enumerate(group.contacts):self.assertEqual(memory.u32(addresses[f'contact.{i}.{j}']+52),0xdeadbeef)
        number_contacts(memory,groups,addresses);number_groups(memory,groups,addresses)
        for i,group in enumerate(case['contact_storage'][1]['groups']):
            self.assertEqual(memory.u32(addresses[f'contact_group.{i}']+124),i)
            for j,contact in enumerate(group['contacts']):self.assertEqual(memory.read(addresses[f'contact.{i}.{j}'],60).hex(),contact['data'])

    def test_changed_original_bound_fails_without_changing_generated_records(self):
        case=copy.deepcopy(self.fixture['cases'][0]);generated=ported_records(case)
        observed=case['contact_storage'][0]['groups'][0]['contacts'][0]
        raw=bytearray.fromhex(observed['data']);raw[0]^=1;observed['data']=raw.hex()
        self.assertEqual(ported_records(case),generated)
        self.assertEqual([d['kind']for d in compare(case)['differences']],['bytes'])

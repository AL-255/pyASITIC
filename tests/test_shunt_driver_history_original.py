"""Earlier caller state, all native branch heaps and independent later words."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_driver_history_original as capture
from capture_driver_history_original import expand_case
from capture_cache_storage_original import expand_files
from audit_shunt_driver_history_original import compare
from audit_shared_heap_original import ported_impedance
from reasitic.contact_stack import contact_frames
from reasitic.green_diagnostics import messages


class ShuntDriverHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_driver_history_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label,mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label,mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_all_native_requests_files_heap_pages_and_observers_retained(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(jobs),14);self.assertEqual(len(f['cases']),28)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_filament_storage_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        for raw,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            c=expand_case(f,raw)
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key])
            self.assertEqual((c['plain']['returncode'],c['signal'],c['pending'],c['setup_pending'],c['prefix_pending']),(0,0,0,0,0))
            self.assertFalse(c['console_inputs']['timing']);self.assertFalse(c['console_inputs']['matrix_dump'])
            self.assertEqual({name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())for name,data in expand_files(f,c)},c['initial_cache'])
            for state in c['allocator_states']:
                self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
                self.assertIsInstance(state['esp'],int);self.assertIsInstance(state['ebp'],int)
            for w in c['workspace_storage']:
                self.assertLessEqual(w['size'],16384);self.assertEqual(len(w['data']),2*w['size']);self.assertEqual(c['events'][w['event_index']]['kind'],'free')
        self.assertEqual(sum(len(c['allocator_states'])for c in f['cases']),122)
        self.assertEqual(sum(len(c['workspace_storage'])for c in f['cases']),476)
        self.assertEqual(sum(len(c['prelude_storage'])for c in f['cases']),308)
        self.assertEqual(sum(len(c['console_calls'])for c in f['cases']),754)

    def test_contact_history_words_come_from_earlier_driver_esp(self):
        count=0
        for c in self.fixture['cases']:
            initial=next(s for s in c['allocator_states']if s['label']=='driver_entry');frames=contact_frames(c['setup_context']['driver'],initial['esp']);entry=next(s for s in c['allocator_states']if s['label']=='contacts_entry')
            self.assertEqual(frames['contacts_entry'],entry['esp'])
            for source in c['contact_stack_entries']:
                for name,key in(('builder_entry','esp'),('contacts_frame','ebp'),('index_address','index_address'),('index','index')):self.assertEqual(frames[name],source[key])
                count+=1
            for g in c['contact_storage'][0]['groups']:
                for contact in g['contacts']:self.assertEqual(struct.unpack_from('<I',bytes.fromhex(contact['data']),52)[0],frames['index'])
        self.assertEqual(count,338)

    def test_complete_small_cold_warm_heaps_and_cache_stores(self):
        for mode in('cold','warm'):
            report,*_=self.source('wire/coarse',mode);self.assertEqual(report['differences'],[])
            self.assertEqual((report['early_heap_boundaries_checked'],report['heap_boundaries_checked']),(2,1))
            self.assertEqual((report['early_unknown_heap_bytes'],report['unknown_heap_bytes'],report['driver']['unknown_bytes']),(0,0,0))

    def test_both_eddy_paths_emit_original_direct_printf_and_preserve_complete_heaps(self):
        for label in('wire/eddy','square/eddy'):
            entry=self.entry(label);report,*_=self.source(label);self.assertEqual(report['differences'],[])
            prepared=ported_impedance(entry);diagnostics=[b''.join(messages(result,f,sep,height))for f,sep,height,width,result in prepared.integrals if result.status]
            self.assertEqual(len(diagnostics),1);self.assertIn(diagnostics[0].decode(),entry['plain']['stdout'])
            self.assertFalse(any(bytes.fromhex(c['text']).startswith(b'\nError:  Quadpack')for c in entry['console_calls']))

    def test_later_heap_and_builder_word_mutations_do_not_repair_source_memory(self):
        baseline,heap,addresses,memory=self.source('wire/coarse');self.assertEqual(baseline['differences'],[])
        entry=copy.deepcopy(self.entry('wire/coarse'));state=next(s for s in entry['allocator_states']if s['label']=='scope')
        address=entry['contact_storage'][0]['groups'][0]['contacts'][0]['address']+52
        region=next(r for r in state['memory_regions']if r['address']<=address<r['address']+r['size']);page,offset=divmod(address-region['address'],4096)
        fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']));data=bytearray.fromhex(fixture['driver_heap_pages'][region['pages'][page]]);data[offset]^=1;key=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][key]=data.hex();region['pages'][page]=key
        region['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in region['pages'])).hexdigest()
        report,other_heap,other_addresses,other_memory=compare(fixture,entry,return_state=True)
        self.assertEqual([(d['kind'],d.get('address'))for d in report['differences']],[('early-heap-word',address)])
        self.assertEqual(other_memory._pages,memory._pages);self.assertEqual(other_addresses,addresses);self.assertEqual(other_heap.tcache,heap.tcache)
        entry=copy.deepcopy(self.entry('wire/coarse'));entry['contact_stack_entries'][0]['index']^=1
        report,other_heap,other_addresses,other_memory=compare(self.fixture,entry,return_state=True)
        self.assertEqual([d['kind']for d in report['differences']],['contact-builder-stack']);self.assertEqual(other_memory._pages,memory._pages)

    def test_changed_earlier_esp_changes_contact_words_before_numbering(self):
        entry=copy.deepcopy(self.entry('wire/coarse'));initial=next(s for s in entry['allocator_states']if s['label']=='driver_entry');initial['esp']+=16
        frames=contact_frames(entry['setup_context']['driver'],initial['esp']);report=compare(self.fixture,entry)
        changed=[d for d in report['differences']if d['kind']=='early-heap-word'];self.assertEqual(len(changed),2)
        self.assertTrue(all(d['boundary']=='scope'and d['actual']==struct.pack('<I',frames['index']).hex()for d in changed))
        self.assertNotIn('node-word',[d['kind']for d in report['differences']])
        del initial['esp']
        with self.assertRaisesRegex(ValueError,'earlier driver ESP'):compare(self.fixture,entry)

    def test_missing_green_printf_is_a_real_full_heap_failure(self):
        with patch('reasitic.green_diagnostics.messages',return_value=()):report=compare(self.fixture,self.entry('wire/eddy'))
        self.assertGreater(len(report['differences']),0);self.assertEqual({d['kind']for d in report['differences']},{'heap-word'})


if __name__=='__main__':unittest.main()

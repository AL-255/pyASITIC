"""Earlier ABI provenance, real stdin seeks and unwaived shutdown targets."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_repl_original as capture
import audit_shunt_repl_original as audit
import audit_seek_storage_original as seek
from audit_loader_lookup_original import data


class ShuntReplTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_repl_original.json.gz').read_bytes()));cls.cached=None

    def entry(self):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==('wire/coarse','warm'))

    def source(self):
        if self.__class__.cached is None:self.__class__.cached=audit.compare(self.fixture,self.entry(),return_state=True)
        return self.__class__.cached

    def test_all_native_scripts_earlier_abi_inputs_and_complete_later_targets(self):
        f=self.fixture;jobs=list(capture.parent.parent.second.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28))
        self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_shutdown_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs','loader_regions'):
            for digest,raw in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(raw)).hexdigest(),digest)
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            inputs=entry['transition_inputs'];ctx=inputs['loader_context'];stdio=inputs['stdio_context'];s=entry['shutdown']
            self.assertEqual((entry['plain']['returncode'],entry['signal'],entry['second']['signal'],entry['port_tail']['signal'],s['exit_code'],s['signal'],s['pending']),(0,0,0,0,0,0,0))
            self.assertEqual(ctx['tls_base'],inputs['port_tail_abi']['tls_base']);self.assertEqual(stdio['stdin_position'],inputs['stdin_stream']['file_position'])
            self.assertEqual(stdio['sar31_af'],f['integer_cpu']['sar31_af']);self.assertEqual(stdio['input_abi']['shr1_af'],f['byte_cpu']['shr1_af'])
            for region in ctx['regions']:data(f,region)
            initial=next(s for s in entry['allocator_states']if s['label']=='driver_entry')
            for mapping in inputs['cache_mapping_inputs']:
                self.assertIn(mapping,initial['mapped_chunks'])
                start=mapping['address']-mapping['prev_size'];size=mapping['prev_size']+(mapping['size_word']&~7)
                region=next(r for r in inputs['initial_regions']if r['address']==start and len(r['data'])//2==size)
                self.assertEqual(struct.unpack_from('<II',bytes.fromhex(region['data']),mapping['prev_size']),(mapping['prev_size'],mapping['size_word']))
            self.assertEqual(len(s['printf']),3)
            for call in s['printf']:self.assertEqual(set(call),{'kind','before','after'});self.assertEqual(set(call['before']),set(call['after']))
            for state in s['states']:
                self.assertEqual(len(state['component_regions']),4+len(stdio['regions']))
                for region in state['component_regions']:data(f,region)
            for call in s['io']:
                self.assertEqual(set(call),{'kind','before','after'})
                for phase in('before','after'):
                    self.assertEqual(len(call[phase]['regions']),2)
                    for region in call[phase]['regions']:data(f,region)

    def test_every_isolated_native_seek_sync_stack_register_and_position(self):
        report=seek.run(self.fixture);self.assertEqual(report['differences'],0)
        self.assertEqual((report['cases'],report['calls_checked'],report['words_checked'],report['registers_checked'],report['positions_checked']),(28,120,4059600,2040,120))

    def test_source_continues_buffered_quit_with_actual_events_and_registers(self):
        r,h,a,m,s=self.source();self.assertEqual(r['before']['differences'],[])
        native=self.entry()['shutdown'];self.assertEqual(s.events[:50],native['events'][:50]);self.assertGreaterEqual(r['heap_boundaries_checked'],7)
        self.assertEqual(r['printf_calls_checked'],3);self.assertEqual(r['printf_registers_checked'],102)
        self.assertEqual(r['registers_checked'],10);self.assertEqual((r['unknown_bytes'],r['io_unknown_bytes']),(0,0))
        self.assertFalse({'shutdown-heap-word','shutdown-component-word','shutdown-register','repl-printf-register','repl-io-register','repl-io-position'}&{d['kind']for d in r['differences']})
        self.assertEqual(s.history.stdin_position,len(bytes.fromhex(self.entry()['transition_inputs']['stdin_stream']['file_data'])))

    def test_changed_later_io_words_and_registers_never_seed_the_continuation(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(self.entry());f=dict(self.fixture,loader_regions=dict(self.fixture['loader_regions']))
        call=entry['shutdown']['io'][0];call['before']['registers']['eax']^=1
        region=call['before']['regions'][0];raw=bytearray(data(f,region));raw[0]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region['sha256']=key
        changed,other_h,other_a,other_m,other_s=audit.compare(f,entry,return_state=True)
        self.assertGreater(len(changed['differences']),len(baseline['differences']));self.assertIn('repl-io-register',{d['kind']for d in changed['differences']})
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events)

    def test_earlier_descriptor_position_drives_the_virtual_seek(self):
        entry=self.entry();call=next(c for c in entry['shutdown']['io']if c['kind']=='llseek')
        m,storage=seek.engine(self.fixture,entry,call);storage.positions[0]+=7
        result=storage.llseek(call['before']['registers']);self.assertEqual(storage.positions[0],call['after']['stdin_position']+7)
        self.assertEqual(result['eax'],call['after']['registers']['eax']+7)


if __name__=='__main__':unittest.main()

"""Native complete closes, transient locks and later-target independence."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_cleanup_original as capture
import audit_shunt_cleanup_original as audit
from audit_loader_lookup_original import data,memory_for
from audit_malloc_storage_original import engine
from reasitic.process_cleanup import ProcessCleanup
from reasitic.memory import UnknownMemory
from reasitic.libio_storage import FileStorage


class ShuntCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_cleanup_original.json.gz').read_bytes()));cls.cached=None

    def entry(self):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==('square/coarse','warm'))

    def source(self):
        if self.__class__.cached is None:self.__class__.cached=audit.compare(self.fixture,self.entry(),return_state=True)
        return self.__class__.cached

    def test_all_unchanged_histories_and_complete_native_cleanup_targets(self):
        f=self.fixture;jobs=list(capture.parent.parent.parent.parent.second.command.shunt.shunt.jobs());self.assertEqual((len(jobs),len(f['cases'])),(14,28))
        self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['shunt_cleanup_reference'],capture.REFERENCE)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_malloc_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        regions=total=phases=0
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            s=entry['shutdown'];self.assertEqual((entry['plain']['returncode'],entry['signal'],s['exit_code'],s['signal'],s['pending']),(0,0,0,0,0))
            self.assertEqual([c['kind']for c in s['cleanup']],['log.input','log.output','XFreeThreads']);self.assertEqual(len(s['states']),8)
            for call in s['cleanup']:
                self.assertEqual(set(call),{'kind','before','after'}if call['kind']=='XFreeThreads'else{'kind','file','before','after','free'})
                if 'free'in call:self.assertEqual(len(call['free']),2)
                for point in [call['before'],call['after']]+[v['state']for v in call.get('free',[])]:
                    phases+=1;self.assertEqual(len(point['registers']),17);self.assertEqual(len(point['xstate'])//2,2440)
                    head=entry['libio_inputs']['libc_symbols']['_IO_list_all']['address'];self.assertIn((head,4),[(r['address'],r['size'])for r in point['regions']])
                    for region in point['regions']:raw=data(f,region);regions+=1;total+=len(raw)
        self.assertEqual((phases,regions,total),(280,15344,399245376));self.assertEqual(f['cleanup_projection'],dict(complete_regions_checked=regions,bytes_checked=total,reference=capture.parent.PROJECTION_REFERENCE))

    def test_every_isolated_close_keeps_all_stack_register_fp_failures(self):
        r=audit.run(self.fixture,isolated=True)
        self.assertEqual((r['cases'],r['native_cleanup_calls'],r['cleanup_calls_checked'],r['cleanup_phases_checked'],r['cleanup_words_checked'],r['cleanup_heap_boundaries_checked'],r['cleanup_unknown_bytes']),(28,84,56,168,59889864,168,0))
        kinds=collections.Counter(d['kind']for c in r['results']for d in c['differences'])
        self.assertEqual(kinds,{'cleanup-word':6618,'cleanup-register-continuation-missing':168,'cleanup-fp-continuation-missing':168,'cleanup-phase-missing':56})
        for result,entry in zip(r['results'],self.fixture['cases']):
            for d in result['differences']:
                if d['kind']=='cleanup-word':
                    stack=entry['shutdown']['cleanup'][d['call']]['before']['regions'][0];self.assertTrue(stack['address']<=d['address']<stack['address']+stack['size'])

    def test_continuing_source_closes_both_logs_and_reaches_exit_entry(self):
        r,h,a,m,s=self.source();entry=self.entry();self.assertEqual(r['before']['differences'],[])
        self.assertEqual(s.events,entry['shutdown']['events'][:-3]);self.assertEqual(r['heap_boundaries_checked'],8)
        self.assertEqual((r['cleanup_calls_checked'],r['cleanup_phases_checked'],r['cleanup_heap_boundaries_checked'],r['cleanup_unknown_bytes']),(2,8,8,0))
        self.assertEqual([c['kind']for c in s.history.cleanup.calls],['log.input','log.output'])
        kinds={d['kind']for d in r['differences']};self.assertFalse({'shutdown-heap-word','shutdown-freed-buffer','shutdown-event','state','physical-chunks','physical-header-errors','cleanup-heap-field','cleanup-event-count','cleanup-region-owners'}&kinds)
        self.assertIn('shutdown-process-exit-missing',kinds);self.assertIn('cleanup-phase-missing',kinds)
        self.assertEqual([d['reason']for d in r['differences']if d['kind']=='shutdown-runtime'],['Libc exit handlers and loader finalizers are not yet bound'])
        stack=entry['shutdown']['cleanup'][0]['before']['regions'][0]
        for d in r['differences']:
            if d['kind']in('cleanup-word','shutdown-component-word'):self.assertTrue(stack['address']<=d['address']<stack['address']+stack['size'])

    def test_changed_later_cleanup_outputs_cannot_seed_execution(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(self.entry());f=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        target=entry['shutdown']['cleanup'][0]['after'];target['heap']['top']^=16;target['registers']['eax']^=1
        region=next(r for r in target['regions']if r['address']==entry['shutdown']['cleanup'][0]['file']and r['size']==304)
        raw=bytearray(data(f,region));raw[100]^=1;key=hashlib.sha256(raw).hexdigest();f['driver_heap_pages'][key]=raw.hex();region['pages']=[key];region['sha256']=key
        changed,other_h,other_a,other_m,other_s=audit.compare(f,entry,return_state=True)
        kinds=collections.Counter(d['kind']for d in changed['differences']);prior=collections.Counter(d['kind']for d in baseline['differences'])
        self.assertEqual(kinds['cleanup-word']-prior['cleanup-word'],1);self.assertEqual(kinds['state']-prior['state'],1)
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events)

    def test_transient_file_reset_is_detected_even_with_equal_final_memory(self):
        baseline,h,a,m,s=self.source();point=ProcessCleanup.point
        def early(cleanup,phase,address=None):
            if phase=='free'and len(cleanup.calls[-1]['free'])==1:FileStorage(cleanup.memory,cleanup.abi).closed_byte_stream(cleanup.calls[-1]['file'])
            point(cleanup,phase,address)
        with patch.object(ProcessCleanup,'point',early):r,other_h,other_a,other_m,other_s=audit.compare(self.fixture,self.entry(),return_state=True)
        self.assertGreater(len(r['differences']),len(baseline['differences']));self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_s.events,s.events)

    def component(self):
        entry=self.entry();call=entry['shutdown']['cleanup'][0];ctx=entry['transition_inputs']['loader_context'];before=call['before']
        h,m,_=engine(self.fixture,dict(before,regions=ctx['regions']+before['regions']),ctx);history=SimpleNamespace(heap=h,memory=m,libio=entry['libio_inputs'],inputs=entry['transition_inputs']);frees=[]
        def release(address,caller,*,before_free):frees.append(address);before_free();h.free(address)
        return call,m,ProcessCleanup(history,release=release),frees

    def test_missing_earlier_log_binding_remains_unknown(self):
        call,m,cleanup,frees=self.component();m.forget(0x80d7e24,4)
        with self.assertRaises(UnknownMemory):cleanup.close_logs()
        self.assertEqual(frees,[])

    def test_pending_log_output_cannot_be_silently_dropped(self):
        call,m,cleanup,frees=self.component();file=call['file'];base=m.u32(file+16);m.put_u32(file+20,base+1);contents=m.read(base,1)
        with self.assertRaisesRegex(NotImplementedError,'pending output'):cleanup.close(call['kind'],file)
        self.assertEqual(frees,[]);self.assertEqual(m.read(base,1),contents)

    def test_x11_finalizer_inputs_are_genuine_earlier_controls(self):
        for entry in self.fixture['cases']:
            ctx=entry['transition_inputs']['loader_context'];m=memory_for(self.fixture,dict(regions=ctx['regions']));control=entry['transition_inputs']['cleanup_context'];x=next(v for v in ctx['maps']if v['address']==control['x11_map'])
            self.assertEqual(control['x11_sha256'],capture.X11_SHA256);self.assertEqual(x['plt']['elf_sha256'],capture.X11_SHA256);base=m.u32(x['address'])
            self.assertEqual([m.u32(base+offset)for offset in(0x150e4c,0x150e48,0x150e44)],[e['address']for e in entry['shutdown']['events'][-3:]])
            self.assertEqual([m.u32(base+0x14e838+offset)for offset in(0,4)],[base+0x120d0,base+0x11ff0])
            final=entry['shutdown']['cleanup'][-1]['after'];region=next(r for r in final['regions']if r['address']==base+0x150e44 and r['size']==12);self.assertEqual(data(self.fixture,region),bytes(12))


if __name__=='__main__':unittest.main()

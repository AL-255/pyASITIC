"""Full native stdin allocations, continuing source and input causality."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_malloc_original as capture
import audit_shunt_malloc_original as audit
from audit_malloc_storage_original import engine
from audit_loader_lookup_original import data
from reasitic.memory import UnknownMemory


class ShuntMallocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_malloc_original.json.gz').read_bytes()));cls.cached=None

    def entry(self):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==('square/coarse','warm'))

    def source(self):
        if self.__class__.cached is None:self.__class__.cached=audit.compare(self.fixture,self.entry(),return_state=True)
        return self.__class__.cached

    def test_all_original_histories_provenance_and_complete_malloc_regions(self):
        f=self.fixture;jobs=list(capture.parent.parent.parent.second.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_repl_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        regions=total=calls=0
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            s=entry['shutdown'];self.assertEqual((entry['plain']['returncode'],entry['signal'],s['exit_code'],s['signal'],s['pending']),(0,0,0,0,0))
            self.assertEqual(len(s['states']),8);self.assertEqual(len(s['printf']),3)
            for call in s['malloc']:
                calls+=1;self.assertEqual(set(call),{'before','after'})
                for point in call.values():
                    self.assertEqual(len(point['regions']),3);self.assertEqual(len(point['registers']),17);self.assertEqual(len(point['xstate'])//2,2440)
                    for region in point['regions']:
                        self.assertEqual(region['page_bank'],'driver_heap_pages');raw=data(f,region);regions+=1;total+=len(raw)
        self.assertEqual((calls,regions,total),(10,60,25827120))
        self.assertEqual(f['malloc_projection'],dict(complete_regions_checked=regions,bytes_checked=total,reference=capture.PROJECTION_REFERENCE))

    def test_all_isolated_malloc_memory_register_fp_and_heap_targets(self):
        report=audit.run(self.fixture,isolated=True);self.assertEqual(report['differences'],0)
        self.assertEqual((report['cases'],report['calls_checked'],report['words_checked'],report['registers_checked'],report['fp_bytes_checked'],report['heap_boundaries_checked']),(28,10,3228390,170,24400,10))

    def test_unbuffered_source_reaches_quit_and_cache_release(self):
        r,h,a,m,s=self.source();self.assertEqual(r['before']['differences'],[])
        self.assertEqual((r['malloc_calls_checked'],r['malloc_phases_checked'],r['malloc_words_checked'],r['malloc_registers_checked'],r['malloc_heap_boundaries_checked'],r['malloc_unknown_bytes']),(1,2,645678,34,2,0))
        self.assertEqual(s.events,self.entry()['shutdown']['events'][:-3])
        self.assertEqual(r['heap_boundaries_checked'],8);self.assertEqual((r['printf_calls_checked'],r['registers_checked']),(3,10))
        self.assertEqual([d['reason']for d in r['differences']if d['kind']=='shutdown-runtime'],['Libc exit handlers and loader finalizers are not yet bound'])
        self.assertFalse({'shutdown-heap-word','malloc-register','malloc-heap-field','physical-chunks','physical-header-errors','state'}&{d['kind']for d in r['differences']})
        # The newly executed exit-entry boundary exposes inherited stack
        # effects. Every word remains a failure in the complete audit.
        words=[d for d in r['differences']if d['kind']=='shutdown-component-word'];self.assertEqual(len(words),24)
        workspace=self.entry()['transition_inputs']['workspace_address'];stack=next(v for v in self.entry()['transition_inputs']['initial_regions']if v['address']<=workspace<v['address']+len(v['data'])//2)
        self.assertTrue(all(stack['address']<=d['address']<stack['address']+len(stack['data'])//2 for d in words))
        self.assertEqual(sum(d['kind']=='malloc-fp-continuation-missing'for d in r['differences']),2)

    def test_later_malloc_targets_do_not_initialize_the_full_source(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(self.entry());f=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        call=entry['shutdown']['malloc'][0]
        for point in call.values():
            point['registers']['eax']^=1;point['heap']['top']^=16
            region=point['regions'][0];key=region['pages'][0];raw=bytearray.fromhex(f['driver_heap_pages'][key]);raw[0]^=1;digest=hashlib.sha256(raw).hexdigest();f['driver_heap_pages'][digest]=raw.hex();region['pages'][0]=digest
            original=b''.join(bytes.fromhex(f['driver_heap_pages'][key])for key in region['pages']);region['sha256']=hashlib.sha256(original).hexdigest()
        changed,other_h,other_a,other_m,other_s=audit.compare(f,entry,return_state=True)
        kinds=collections.Counter(d['kind']for d in changed['differences']);prior=collections.Counter(d['kind']for d in baseline['differences'])
        self.assertEqual(kinds['malloc-register']-prior['malloc-register'],2);self.assertEqual(kinds['malloc-word']-prior['malloc-word'],2);self.assertEqual(kinds['state']-prior['state'],2)
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events);self.assertEqual(other_s.malloc_calls,s.malloc_calls)

    def test_missing_earlier_allocator_controls_stay_unknown(self):
        entry=self.entry();before=entry['shutdown']['malloc'][0]['before'];ctx=entry['transition_inputs']['loader_context'];inputs=dict(before,regions=ctx['regions']+before['regions'])
        h,m,storage=engine(self.fixture,inputs,ctx);m.forget(storage.got+0x78,4)
        with self.assertRaises(UnknownMemory):storage.enter(before['registers'])
        h,m,storage=engine(self.fixture,inputs,ctx);m.put_u32(h.arena_address+56,h.top+16)
        with self.assertRaisesRegex(ValueError,'physical top'):storage.enter(before['registers'])

    def test_changed_later_fp_remains_an_independent_failure(self):
        entry=copy.deepcopy(self.entry());before=entry['shutdown']['malloc'][0]['before'];entry['shutdown']['malloc'][0]['after']['xstate']='%02x'%(int(before['xstate'][:2],16)^1)+before['xstate'][2:]
        self.assertEqual([d['kind']for d in audit.compare_isolated(self.fixture,entry)['differences']],['malloc-fp-byte'])
        entry['shutdown']['malloc'][0]['after']['xstate']+='00'
        self.assertIn('malloc-fp-size',[d['kind']for d in audit.compare_isolated(self.fixture,entry)['differences']])

    def test_every_additional_later_heap_field_remains_required(self):
        entry=copy.deepcopy(self.entry());after=entry['shutdown']['malloc'][0]['after']['heap']
        after['flags']^=1;after['max_fast']^=16;after['tcache_counts'][0]+=1;after['tcache_key']^=1;after['mapping_policy']['mmap_min_addr']^=4096
        after['maps'][0]['permissions']='---p';after['event_count']+=1;after['errors'].append(dict(section='tcache.0',reason='injected'))
        kinds=collections.Counter(d['kind']for d in audit.compare_isolated(self.fixture,entry)['differences'])
        self.assertEqual(kinds,{'malloc-heap-field':5,'malloc-mappings':1,'malloc-observer-event-count':1,'malloc-additional-native-heap-error':1})

    def test_inconsistent_earlier_arena_cannot_silently_disable_stores(self):
        from reasitic.heap import Heap
        from reasitic.memory import Memory
        before=self.entry()['shutdown']['malloc'][0]['before'];h=Heap(before['heap']);m=Memory(h.address_space)
        m.write(h.arena_address,bytes.fromhex(before['heap']['arena_bytes']));m.put_u32(h.arena_address+56,h.top+16)
        with self.assertRaisesRegex(ValueError,'Earlier arena image'):h.observe_header_stores(m)


if __name__=='__main__':unittest.main()

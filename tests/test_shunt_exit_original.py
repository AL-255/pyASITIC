"""Earlier exit inputs, source dependency traversal and complete later assertions."""
import collections,copy,hashlib,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_exit_original as capture
import audit_shunt_exit_original as audit
from audit_loader_lookup_original import data,memory_for
from exit_fixture import read_fixture,expand_case,heap,factor,content_key,INLINE,REFERENCE
from reasitic.exit_storage import ExitStorage
from reasitic.memory import UnknownMemory


class ShuntExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/shunt_exit_original.json.gz');cls.cached=None

    def entry(self):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==('square/coarse','warm'))

    def source(self):
        if self.__class__.cached is None:self.__class__.cached=audit.compare(self.fixture,self.entry(),return_state=True)
        return self.__class__.cached

    def component(self,entry=None):
        entry=expand_case(self.fixture,self.entry()if entry is None else entry);inputs=entry['transition_inputs']
        m=memory_for(self.fixture,dict(regions=inputs['loader_context']['regions']+entry['shutdown']['exit_calls'][0]['before']['regions']))
        return ExitStorage(SimpleNamespace(memory=m,heap=None,inputs=inputs,libio=entry['libio_inputs']))

    def first_destructor(self,engine):
        with self.assertRaisesRegex(NotImplementedError,'ELF finalizer body 0x80b4784'):engine.run(0)

    def test_unchanged_native_histories_and_every_complete_exit_target(self):
        f=self.fixture;jobs=list(capture.parent.parent.parent.parent.parent.second.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['shunt_exit_reference'],capture.REFERENCE)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_cleanup_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        phases=regions=total=calls=0
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            s=entry['shutdown'];self.assertEqual((entry['plain']['returncode'],entry['signal'],s['exit_code'],s['signal'],s['pending']),(0,0,0,0,0))
            self.assertEqual(collections.Counter(c['kind']for c in s['exit_calls']),{'exit':1,'registered':1,'loader':1,'object':19,'fini':31})
            for call in s['exit_calls']:
                calls+=1;self.assertEqual(len(call['arguments']),3)
                self.assertEqual('after'in call,call['kind']!='exit')
                for which in('before','after'):
                    if which not in call:continue
                    point=call[which];phases+=1
                    self.assertEqual(len(point['registers']),17);self.assertEqual(len(point['xstate'])//2,2440)
                    self.assertEqual([(r['address'],r['size'])for r in point['regions'][-len(entry['transition_inputs']['exit_inputs']['regions']):]],[(r['address'],r['size'])for r in entry['transition_inputs']['exit_inputs']['regions']])
                    for region in point['regions']:raw=data(f,region);regions+=1;total+=len(raw)
        self.assertEqual((calls,phases,regions,total),(1484,2940,467460,4243637580))
        self.assertEqual(f['exit_projection'],dict(complete_regions_checked=regions,bytes_checked=total,reference=capture.parent.parent.PROJECTION_REFERENCE))

    def test_lossless_heap_transport_and_independent_assertion_containers(self):
        f=self.fixture;self.assertEqual(f['exit_heap_projection'],dict(states_checked=2940,unique_states=56,reference=REFERENCE))
        for key,body in f['exit_heap_states'].items():self.assertEqual(content_key(body),key)
        expanded=expand_case(f,self.entry());refactored=copy.deepcopy(expanded);single=dict(cases=[refactored]);factor(single)
        for original,packed in zip(expanded['shutdown']['exit_calls'],refactored['shutdown']['exit_calls']):
            for which in('before','after'):
                if which not in original:continue
                self.assertEqual(heap(single,packed[which]),original[which]['heap'])
                self.assertEqual(set(packed[which]['heap'])-{'content'},set(original[which]['heap'])&set(INLINE))
        before=heap(f,self.entry()['shutdown']['exit_calls'][0]['before']);later=heap(f,self.entry()['shutdown']['exit_calls'][1]['before'])
        unchanged=copy.deepcopy(before);later['maps'][0]['start']^=4096
        self.assertEqual(before,unchanged);self.assertEqual(heap(f,self.entry()['shutdown']['exit_calls'][0]['before']),unchanged)
        for info in f['external_banks'].values():
            raw=(ROOT/'tests/fixtures'/info['file']).read_bytes();self.assertLess(len(raw),100*1024**2);self.assertEqual(hashlib.sha256(raw).hexdigest(),info['sha256'])

    def test_all_isolated_states_keep_stack_abi_and_unexecuted_finalizer_failures(self):
        r=audit.run(self.fixture,isolated=True)
        self.assertEqual((r['cases'],r['native_exit_calls'],r['exit_calls_checked'],r['exit_phases_checked'],r['exit_words_checked'],r['exit_heap_boundaries_checked'],r['exit_argument_words_checked'],r['exit_object_order_checked'],r['exit_unknown_bytes']),(28,1484,140,112,40416016,112,84,532,0))
        self.assertEqual(collections.Counter(d['kind']for c in r['results']for d in c['differences']),{'exit-word':7000,'exit-phase-missing':2800,'exit-register-continuation-missing':112,'exit-fp-continuation-missing':112,'exit-runtime':28})
        for result,entry in zip(r['results'],self.fixture['cases']):
            stack=entry['shutdown']['exit_calls'][0]['before']['regions'][0]
            for d in result['differences']:
                if d['kind']=='exit-word':self.assertTrue(stack['address']<=d['address']<stack['address']+stack['size'])

    def test_full_history_uses_same_memory_and_actual_exit_stores(self):
        r,h,a,m,s=self.source();e=expand_case(self.fixture,self.entry());engine=s.history.exiting
        self.assertIs(engine.m,m);self.assertIs(engine.heap,h)
        self.assertEqual([c['kind']for c in engine.calls],['exit','registered','loader','object','fini'])
        self.assertFalse(any(c.get('returned')for c in engine.calls))
        self.assertEqual(engine.object_order,[c['arguments'][0]for c in e['shutdown']['exit_calls']if c['kind']=='object'])
        self.assertEqual((r['exit_calls_checked'],r['exit_phases_checked'],r['exit_heap_boundaries_checked'],r['exit_unknown_bytes']),(5,5,5,0))
        control=engine.controls;node=m.u32(control['__exit_funcs']['address'])
        self.assertEqual((m.u32(node+4),m.u32(node+8),m.u32(control['__exit_funcs_lock']['address'])),(0,0,0))
        self.assertEqual(engine.field(engine.object_order[0],'l_init_called'),0)
        self.assertTrue(all(engine.field(p,'l_init_called')for p in engine.object_order[1:]))
        self.assertEqual(s.events,e['shutdown']['events'][:-3])
        kinds={d['kind']for d in r['differences']};self.assertIn('exit-phase-missing',kinds);self.assertIn('shutdown-process-exit-missing',kinds)
        self.assertFalse({'exit-call','exit-argument','exit-object-order','exit-region-owners','exit-heap-field','exit-event-count'}&kinds)
        stack=e['shutdown']['exit_calls'][0]['before']['regions'][0]
        # Complete _rtld_global newly exposes skipped earlier lazy bindings.
        # These remain ordinary failing words in the strict full audit.
        nonstack=[d for d in r['differences']if d['kind']=='exit-word'and not stack['address']<=d['address']<stack['address']+stack['size']]
        counter=engine.control('_rtld_global')+0x5dc
        self.assertEqual([(d['call'],d['phase'],d['address'])for d in nonstack],[(i,'before',counter)for i in range(5)])
        self.assertTrue(all(int.from_bytes(bytes.fromhex(d['original']),'little')-int.from_bytes(bytes.fromhex(d['actual']),'little')==7 for d in nonstack))
        self.assertEqual([d['reason']for d in r['differences']if d['kind']=='shutdown-runtime'],['ELF finalizer body 0x80b4784 requires its source implementation'])

    def test_changed_later_targets_never_initialize_full_replay(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(expand_case(self.fixture,self.entry()));f=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        target=entry['shutdown']['exit_calls'][4]['before'];target['heap']['top']^=16;target['registers']['eax']^=1
        address=entry['transition_inputs']['exit_inputs']['controls']['__exit_funcs_done']['address'];region=next(r for r in target['regions']if(r['address'],r['size'])==(address,1))
        raw=bytes([data(f,region)[0]^1]);key=hashlib.sha256(raw).hexdigest();f['driver_heap_pages'][key]=raw.hex();region['pages']=[key];region['sha256']=key
        changed,other_h,other_a,other_m,other_s=audit.compare(f,entry,return_state=True)
        prior=collections.Counter(d['kind']for d in baseline['differences']);after=collections.Counter(d['kind']for d in changed['differences'])
        self.assertEqual(after['exit-word']-prior['exit-word'],1);self.assertEqual(after['state']-prior['state'],1)
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events)
        self.assertEqual(other_s.history.exiting.object_order,s.history.exiting.object_order)

    def test_metadata_orders_do_not_supply_source_results(self):
        expected=self.component();self.first_destructor(expected)
        entry=copy.deepcopy(self.entry());x=entry['transition_inputs']['exit_inputs']
        x['functions']=[];x['fini']=list(reversed(x['fini']));x['sort_algorithm']=0
        for item in x['fini']:item['callbacks']=[]
        changed=self.component(entry);self.first_destructor(changed)
        self.assertEqual(changed.object_order,expected.object_order);self.assertEqual(changed.m._pages,expected.m._pages)

    def test_changed_earlier_dependency_changes_computed_order(self):
        baseline=self.component();self.first_destructor(baseline);engine=self.component()
        maps={v['name'].split('/')[-1]:v['address']for v in engine.inputs['maps']};gl=maps['libMesaGL.so.3'];glu=maps['libMesaGLU.so.3']
        engine.m.put_u32(engine.field(glu,'l_initfini')+4,gl);self.first_destructor(engine)
        self.assertNotEqual(engine.object_order,baseline.object_order)
        self.assertLess(engine.object_order.index(glu),engine.object_order.index(gl))

    def test_changed_live_callback_dispatches_and_missing_earlier_bytes_stay_unknown(self):
        engine=self.component();node=engine.m.u32(engine.control('__exit_funcs'));encoded=engine.m.u32(node+12);pc=engine.demangle(encoded)+4
        value=pc^engine.m.u32(engine.tls+24);engine.m.put_u32(node+12,((value<<9)|(value>>23))&0xffffffff)
        with self.assertRaisesRegex(NotImplementedError,'Registered exit callback'):engine.run(0)
        self.assertEqual(engine.calls[-1]['pc'],pc);self.assertEqual(engine.object_order,[])
        for which in('guard','head'):
            engine=self.component();address=engine.tls+24 if which=='guard'else engine.control('__exit_funcs');engine.m.forget(address,4)
            with self.assertRaises(UnknownMemory):engine.run(0)
            self.assertEqual([c['kind']for c in engine.calls],['exit'])

    def test_real_namespace_includes_vdso_and_enum_reads_live_ro_bytes(self):
        engine=self.component();maps=engine.inputs['maps'];self.assertEqual(len(maps),20)
        vdso=next(v['address']for v in maps if v['name']=='linux-gate.so.1');self.assertEqual(engine.field(vdso,'l_init_called'),0)
        self.first_destructor(engine);self.assertEqual(engine.field(vdso,'l_visited'),1);self.assertNotIn(vdso,engine.object_order)
        engine=self.component();address=engine.control('_rtld_global_ro')+engine.inputs['rtld_ro_fields']['_dl_dso_sort_algo']['offset']
        self.assertEqual(engine.m.u32(address),1);engine.m.put_u32(address,123)
        with self.assertRaisesRegex(NotImplementedError,'sorting algorithm'):engine.run(0)


if __name__=='__main__':unittest.main()

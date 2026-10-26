"""Actual CRT member/pool/registry stores with every later target retained."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_crt_original as capture
import audit_shunt_crt_original as audit
from audit_loader_lookup_original import data,memory_for
from exit_fixture import read_fixture,expand_case,heap,content_key
from reasitic.crt_storage import CRTStorage,CRTStrings
from reasitic.exit_storage import ExitStorage
from reasitic.legacy_strings import LegacyStrings
from reasitic.loader_lookup_value import LoaderLookupValue
from reasitic.plt_fixup_storage import PltFixup
from reasitic.memory import UnknownMemory


class ShuntCRTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/shunt_crt_original.json.gz');cls.cached=None

    def entry(self):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==('square/coarse','warm'))

    def source(self):
        if self.__class__.cached is None:self.__class__.cached=audit.compare(self.fixture,self.entry(),return_state=True)
        return self.__class__.cached

    def component(self,entry=None):
        entry=expand_case(self.fixture,self.entry()if entry is None else entry);inputs=entry['transition_inputs']
        m=memory_for(self.fixture,dict(regions=inputs['loader_context']['regions']+entry['shutdown']['crt_calls'][0]['before']['regions']))
        history=SimpleNamespace(memory=m,heap=None,inputs=inputs,libio=entry['libio_inputs'])
        return CRTStorage(ExitStorage(history))

    def test_all_native_histories_and_every_complete_phase(self):
        f=self.fixture;jobs=list(capture.parent.parent.parent.parent.parent.parent.second.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['shunt_crt_reference'],capture.REFERENCE)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_exit_original.json.gz').read_bytes()).hexdigest())
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(f['exit_heap_projection']['states_checked'],3780);self.assertEqual(f['exit_heap_projection']['unique_states'],56)
        for key,body in f['exit_heap_states'].items():self.assertEqual(content_key(body),key)
        totals={name:[0,0,0]for name in('exit','crt')}
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            s=entry['shutdown'];self.assertEqual((entry['plain']['returncode'],entry['signal'],s['exit_code'],s['signal'],s['pending']),(0,0,0,0,0))
            self.assertEqual(collections.Counter(c['kind']for c in s['crt_calls']),{'main.fini':1,'main.dtors':1,'logs.dtors':1,'logs.members':1,'port.dtors':1,'port.member':1,'frame.deregister':1,'mutex.lock':4,'mutex.unlock':4})
            self.assertEqual(len(s['exit_calls']),53)
            for name in totals:
                for call in s[name+'_calls']:
                    for which in('before','after'):
                        if which not in call:continue
                        point=call[which];totals[name][0]+=1;self.assertEqual(len(point['registers']),17);self.assertEqual(len(point['xstate'])//2,2440)
                        self.assertEqual([(r['address'],r['size'])for r in point['regions'][-len(entry['transition_inputs']['exit_inputs']['regions']):]],[(r['address'],r['size'])for r in entry['transition_inputs']['exit_inputs']['regions']])
                        for region in point['regions']:raw=data(f,region);totals[name][1]+=1;totals[name][2]+=len(raw)
                        self.assertNotIn('content',heap(f,point))
        self.assertEqual(totals,dict(exit=[2940,514500,4245131100],crt=[840,147000,1212894600]))
        for name,(_,regions,bytes_)in totals.items():self.assertEqual(f[name+'_projection'],dict(complete_regions_checked=regions,bytes_checked=bytes_,reference=capture.parent.parent.parent.PROJECTION_REFERENCE))

    def test_all_independent_crt_outputs_and_defined_return_values(self):
        r=audit.run(self.fixture,isolated=True)
        self.assertEqual((r['cases'],r['native_crt_calls'],r['crt_calls_checked'],r['crt_phases_checked'],r['crt_words_checked'],r['crt_heap_boundaries_checked'],r['crt_argument_words_checked'],r['crt_values_checked'],r['crt_unknown_bytes']),(28,420,420,812,293119240,812,364,252,0))
        self.assertEqual(collections.Counter(d['kind']for c in r['results']for d in c['differences']),{'crt-word':31632,'crt-register-continuation-missing':812,'crt-fp-continuation-missing':812})
        for result,entry in zip(r['results'],self.fixture['cases']):
            stack=entry['shutdown']['crt_calls'][0]['before']['regions'][0]
            for d in result['differences']:
                if d['kind']=='crt-word':self.assertTrue(stack['address']<=d['address']<stack['address']+stack['size'])

    def test_continuing_source_finishes_main_and_preserves_all_required_gaps(self):
        r,h,a,m,s=self.source();e=self.entry();exiting=s.history.exiting;crt=exiting.crt
        self.assertIs(crt.m,m);self.assertIs(crt.heap,h);self.assertTrue(all(c['returned']for c in crt.calls))
        self.assertEqual((r['crt_calls_checked'],r['crt_phases_checked'],r['crt_heap_boundaries_checked'],r['crt_values_checked'],r['crt_unknown_bytes']),(15,30,30,9,0))
        self.assertEqual((r['exit_calls_checked'],r['exit_phases_checked']),(7,9))
        self.assertEqual(m.u32(0x80cb988),1);self.assertEqual(m.u32(m.u32(0x80cb984)),0)
        removed=next(c['value']for c in crt.calls if c['kind']=='frame.deregister');self.assertEqual(m.u32(removed+8),0x80d0560)
        self.assertEqual(m.u32(crt.legacy_base+0x4142c),m.u32(removed+20))
        self.assertEqual(s.events,e['shutdown']['events'][:-3])
        kinds={d['kind']for d in r['differences']};self.assertFalse({'crt-call','crt-argument','crt-value','crt-event-count','crt-phase-missing','crt-heap-field','crt-region-owners','exit-call','exit-object-order'}&kinds)
        self.assertIn('shutdown-process-exit-missing',kinds);self.assertIn('exit-phase-missing',kinds)
        self.assertEqual([d['reason']for d in r['differences']if d['kind']=='shutdown-runtime'],['ELF finalizer body 0xf7e22a80 requires its source implementation'])
        # Counter deficits from earlier unexecuted imports remain ordinary
        # full-audit failures at every reached phase, with no owner exemption.
        stack=e['shutdown']['crt_calls'][0]['before']['regions'][0];counter=exiting.control('_rtld_global')+0x5dc
        nonstack=[d for d in r['differences']if d['kind']in('crt-word','exit-word')and not stack['address']<=d['address']<stack['address']+stack['size']]
        self.assertEqual(len(nonstack),39);self.assertEqual({d['address']for d in nonstack},{counter})

    def test_changed_later_results_never_seed_full_execution(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(expand_case(self.fixture,self.entry()));f=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        frame=next(c for c in entry['shutdown']['crt_calls']if c['kind']=='frame.deregister');frame['after']['registers']['eax']^=1;frame['after']['heap']['top']^=16
        target=entry['shutdown']['crt_calls'][0]['after'];region=next(r for r in target['regions']if(r['address'],r['size'])==(0x80cb984,8));raw=bytearray(data(f,region));raw[4]^=1
        key=hashlib.sha256(raw).hexdigest();f['driver_heap_pages'][key]=raw.hex();region.update(sha256=key,pages=[key])
        changed,other_h,other_a,other_m,other_s=audit.compare(f,entry,return_state=True)
        old=collections.Counter(d['kind']for d in baseline['differences']);new=collections.Counter(d['kind']for d in changed['differences'])
        for kind in('crt-word','crt-value','state'):self.assertEqual(new[kind]-old[kind],1)
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events)

    def test_actual_cursor_and_registry_links_drive_execution(self):
        engine=self.component();cursor=engine.m.u32(0x80cb984);nil_refs=engine.m.u32(0x80cf1a8+8)
        engine.m.put_u32(0x80cb984,cursor+4);engine.main_fini()
        self.assertNotIn('logs.dtors',[c['kind']for c in engine.calls]);self.assertIn('port.dtors',[c['kind']for c in engine.calls]);self.assertEqual(engine.m.u32(0x80cf1a8+8),nil_refs)
        engine=self.component();head=engine.legacy_base+0x4142c;engine.m.put_u32(head,engine.m.u32(engine.m.u32(head)+20))
        with self.assertRaisesRegex(NotImplementedError,'absent object'):engine.main_fini()
        self.assertEqual(engine.m.u32(0x80cb988),0)

    def test_descriptive_frame_inventory_cannot_repair_missing_earlier_bytes(self):
        baseline=self.component();baseline.main_fini();entry=copy.deepcopy(self.entry());entry['transition_inputs']['crt_inputs']['frame_nodes']=[]
        changed=self.component(entry);changed.main_fini();self.assertEqual(changed.m._pages,baseline.m._pages)
        for address in(0x80cb984,changed.legacy_base+0x4142c):
            engine=self.component();engine.m.forget(address,4)
            with self.assertRaises(UnknownMemory):engine.main_fini()
            self.assertEqual(engine.m.u32(0x80cb988),0)

    def test_transient_pool_lock_order_is_required_even_if_final_memory_matches(self):
        baseline,h,a,m,s=self.source()
        def early_unlock(strings,address,size):
            if size>128:return LegacyStrings.put(strings,address,size)
            strings.crt.mutex(0x80cf20c,True,strings.crt.main);strings.crt.mutex(0x80cf20c,False,strings.crt.main)
            return LegacyStrings.put(strings,address,size)
        with patch.object(CRTStrings,'put',early_unlock):changed,other_h,other_a,other_m,other_s=audit.compare(self.fixture,self.entry(),return_state=True)
        self.assertGreater(len(changed['differences']),len(baseline['differences']));self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_s.events,s.events)

    def test_live_lookup_values_and_bindings_match_original_records(self):
        f=json.loads(gzip.decompress((ROOT/'tests/fixtures/loader_lookup_original.json.gz').read_bytes()));count=0
        for entry in f['cases']:
            for call in entry['lookup_calls']:
                a,b=call['before'],call['after'];m=memory_for(f,a);expected=memory_for(f,b);s=a['registers']['esp'];args=[m.u32(s+4+4*i)for i in range(8)]
                engine=LoaderLookupValue(m,a['loader_base']);value=engine.value(args[0],args[1],m.u32(args[2]),args[3],args[4],type_class=args[5],flags=args[6],skip_map=args[7])
                self.assertEqual(value,dict(provider=b['registers']['eax'],symbol=expected.u32(args[2])));self.assertEqual(m.u32(engine.got+0x5f4),expected.u32(engine.got+0x5f4));count+=1
        self.assertEqual(count,8)
        f=json.loads(gzip.decompress((ROOT/'tests/fixtures/plt_fixup_original.json.gz').read_bytes()));count=0;sample=None
        for entry in f['cases']:
            for call in entry['plt_calls']:
                a,b=call['before'],call['after'];m=memory_for(f,a);t=a['registers']['esp'];map_=m.u32(t);offset=m.u32(t+4);engine=PltFixup(m,a['loader_base'],tls_base=a['tls_base'])
                reloc=engine._dynamic(map_,23)+offset;symbol=engine._dynamic(map_,6)+16*(m.u32(reloc+4)>>8);name=engine._string(engine._dynamic(map_,5)+m.u32(symbol));slot=m.u32(map_)+m.u32(reloc)
                plt=dict(address=m.u32(slot)-16*(offset//8+1)-6,size=16*(m.u32(m.u32(map_+40)+4)//8+1));value=engine.bind_value(map_,name,plt)
                self.assertTrue(value['lazy']);self.assertEqual(value['target'],b['registers']['eip']);self.assertEqual(m.u32(slot),value['target'])
                if sample is None and m.read(value['symbol']+12,1)[0]&15!=10:sample=(a,map_,name,plt,value)
                before=m.u32(engine.got+0x5f4);again=engine.bind_value(map_,name,plt);self.assertFalse(again['lazy']);self.assertEqual(m.u32(engine.got+0x5f4),before);count+=1
        self.assertEqual(count,8)
        # An earlier provider-symbol value changes the computed binding;
        # the later native target cannot overwrite that source input.
        a,map_,name,plt,value=sample;m=memory_for(f,a);engine=PltFixup(m,a['loader_base'],tls_base=a['tls_base']);m.put_u32(value['symbol']+4,m.u32(value['symbol']+4)+4)
        changed=engine.bind_value(map_,name,plt);self.assertEqual(changed['target'],value['target']+4)

    def test_completed_crt_is_not_run_twice_and_held_mutex_is_not_ignored(self):
        engine=self.component();engine.main_fini();before=copy.deepcopy(engine.m._pages);engine.main_fini();self.assertEqual(engine.m._pages,before)
        engine=self.component();engine.m.put_u32(0x80cf20c,1)
        with self.assertRaisesRegex(NotImplementedError,'Contended CRT mutex'):engine.main_fini()
        self.assertEqual(engine.m.u32(0x80cb988),0)


if __name__=='__main__':unittest.main()

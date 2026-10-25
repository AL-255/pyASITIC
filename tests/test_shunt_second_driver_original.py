"""Two native solves, shared source state, cache reuse and strict later targets."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_second_driver_original as capture
import audit_shunt_second_driver_original as audit
from reasitic.memory import Memory
from reasitic.heap import AddressSpace
from reasitic.port_header_storage import NativePortStack
from reasitic.node_storage import NodeStorage
from reasitic.cache_storage import CacheStorage
from reasitic import Technology


class ShuntSecondDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_second_driver_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label='wire/coarse',mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label='wire/coarse',mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=audit.compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_all_jobs_original_outcomes_complete_capture_and_provenance(self):
        f=self.fixture;parent=ROOT/'tests/fixtures/shunt_command_transition_original.json.gz';jobs=list(capture.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(),f['driver_history_parent_sha256'])
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        maximum=0;prefixes=0
        for raw,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(raw[key],job[key])
            c=audit.expand_second(f,raw)
            self.assertEqual((raw['plain']['returncode'],raw['signal'],raw['post_driver']['status'],c['signal'],c['post_output']['status'],c['post_driver']['status']),(0,0,1,0,1,1))
            self.assertEqual((c['pending'],c['setup_pending'],c['setup_interfaces'],c['prefix_pending'],c['prefix_interfaces'],c['post_pending'],c['post_interfaces']),(0,0,0,0,0,0,0))
            self.assertEqual([s['label']for s in c['post_states']],['node_release','node_return','driver_return']);self.assertEqual((len(c['post_events']),len(c['post_buffers'])),(14,8))
            for state in c['allocator_states']+c['post_states']:self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
            for record in c['post_buffers']:
                event=c['post_events'][record['event_index']];self.assertEqual((event['kind'],event['address']),('free',record['address']));self.assertEqual(len(record['data']),2*record['size']);maximum=max(maximum,record['size'])
            self.assertTrue(all(e['allocator']=='scalar'for e in c['prefix_events']));prefixes+=len(c['prefix_events'])
        self.assertEqual(maximum,18496);self.assertGreater(prefixes,0)

    def test_cold_warm_ground_and_coupled_second_solves_match(self):
        for label,mode in(('wire/coarse','cold'),('wire/coarse','warm'),('wire/ground','warm'),('wire/coupled','warm')):
            with self.subTest(label=label,mode=mode):
                r,h,a,m=self.source(label,mode);self.assertEqual(r['differences'],[])
                self.assertEqual((r['events_checked'],r['allocations_checked'],r['buffers_checked'],r['heap_boundaries_checked']),(14,6,8,3))
                self.assertEqual((r['second_early_heap_boundaries_checked'],r['second_early_unknown_bytes'],r['unknown_heap_bytes'],r['unknown_port_bytes']),(3,0,0,0))
                self.assertEqual(r['cache_files_checked'],1);self.assertEqual(r['cache_tables_checked'],2*len(self.entry(label,mode)['second']['cache_outputs']))

    def test_both_node_solves_and_preludes_keep_identical_memory(self):
        first=audit.first;prelude=audit.prelude;solve=NodeStorage.solve;seen={};memories=[]
        def prefix(*args,**kwargs):
            result=first(*args,**kwargs);seen['heap']=result[1];seen['memory']=result[3];return result
        def following(*args,**kwargs):
            context=kwargs['source_context'];self.assertIs(context['geometry'].memory,seen['memory']);self.assertIs(context['geometry'].heap,seen['heap']);self.assertNotIn('initial_regions',kwargs)
            result=prelude(*args,**kwargs);self.assertIs(result[3],seen['memory']);return result
        def nodes(history):memories.append(history.memory);return solve(history)
        with patch.object(audit,'first',side_effect=prefix),patch.object(audit,'prelude',side_effect=following),patch.object(NodeStorage,'solve',nodes):r=audit.compare(self.fixture,self.entry())
        self.assertEqual(r['differences'],[]);self.assertEqual(len(memories),2);self.assertTrue(all(m is seen['memory']for m in memories))

    def test_later_entry_cache_file_heap_ports_and_console_never_seed_source(self):
        baseline,h,a,m=self.source();self.assertEqual(baseline['differences'],[])
        entry=copy.deepcopy(self.entry());second=entry['second'];fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        for record,key in((second['setup_context']['entry'],'arguments_data'),(second['post_output']['ports'][0],'data'),(second['console_calls'][-1],'text')):
            data=bytearray.fromhex(record[key]);data[0]^=1;record[key]=data.hex()
        second['setup_context']['entry']['esp']+=4
        for record in(second['cache_inputs']['initial_regions'][0],second['cache_outputs'][0],second['cache_inputs']['files'][0]):record['sha256']='0'*64
        region=second['allocator_states'][0]['memory_regions'][0];data=bytearray.fromhex(fixture['driver_heap_pages'][region['pages'][0]]);data[0]^=1;digest=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][digest]=data.hex();region['pages'][0]=digest
        region['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in region['pages'])).hexdigest()
        r,other_h,other_a,other_m=audit.compare(fixture,entry,return_state=True)
        self.assertEqual({d['kind']for d in r['differences']},{'second-entry','second-argument-bytes','second-cache-table','second-cache-file','second-heap-word','node-port','node-port-memory','console-call'})
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_a,a);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(r['first']['differences'],[])

    def test_reused_source_table_changes_the_second_capacitance(self):
        first=audit.first
        def changed(fixture,entry,**kwargs):
            value=first(fixture,entry,**kwargs);m=value[3];inputs=entry['cache_inputs'];technology=Technology.from_text(entry['request']['technology'])
            shape=entry['setup_context']['arguments'][0];segment=m.u32(shape+0xa8);metal=m.u32(segment+0xdc)
            cache=CacheStorage(m,inputs,technology,1.);index=cache.index(metal,metal);group=inputs['arrays']['xy'];address=m.u32(group['pointer_address']+4*index)
            values=struct.unpack('<'+'d'*(group['size']//8),m.read(address,group['size']));m.write(address,struct.pack('<'+'d'*len(values),*(v*2 for v in values)))
            return value
        with patch.object(audit,'first',side_effect=changed):r=audit.compare(self.fixture,self.entry())
        kinds={d['kind']for d in r['differences']};self.assertIn('second-cache-table',kinds);self.assertIn('node-word',kinds);self.assertEqual(r['first']['differences'],[])

    def test_fflush_call_writer_and_partial_push_follow_native_provenance(self):
        from capture_port_driver_writers_original import OBSERVER,commands
        f=json.loads((ROOT/'tests/fixtures/port_driver_writers_original.json').read_text());self.assertEqual(f['observer'],OBSERVER)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],commands(directory));self.assertEqual(len(f['cases']),3)
        for c in f['cases']:
            frame=c['registers']['ebp'];m=Memory(AddressSpace([dict(start=(frame-8192)&~4095,end=(frame+4096)&~4095)]));m.write((frame-8192)&~4095,bytes([0xa5])*12288)
            call=NativePortStack(m,frame).driver_entry('pi2',[1,2],3.,libc_base=c['libc_base']);sync=next(w for w in reversed(c['watch'])if '_IO_new_file_sync'in w['trace']);last=c['watch'][-1]
            self.assertEqual((sync['pc']-c['libc_base'],sync['value']-c['libc_base']),(0x833f0,0x75bd2));self.assertEqual((last['pc'],last['address'],last['value']),(0x8052c1a,call['esp']+20,m.u32(call['esp']+20)))
        for base in(0,0x12345000,0xf794d000,0xfff90000):
            m=Memory(AddressSpace([dict(start=0x3000,end=0x6000)]));m.write(0x3000,bytes([0xa5])*0x3000);call=NativePortStack(m,0x5000).driver_entry('pi2',[1,2],3.,libc_base=base)
            self.assertEqual(m.u32(call['esp']+20),((base+0x75bd2)&0xffffffff)&0xffff0000)

    def test_wrong_earlier_libc_binding_cannot_be_repaired_by_later_flag_bytes(self):
        original=NativePortStack.driver_entry
        def changed(history,*args,**kwargs):kwargs['libc_base']+=0x10000;return original(history,*args,**kwargs)
        with patch.object(NativePortStack,'driver_entry',changed):r=audit.compare(self.fixture,self.entry())
        self.assertEqual([d['kind']for d in r['differences']],['second-argument-bytes']);self.assertEqual(r['first']['differences'],[])


if __name__=='__main__':unittest.main()

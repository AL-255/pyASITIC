"""Complete native S files, continuing stream identity, locking and strict targets."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_port_tail_original as capture
import audit_shunt_port_tail_original as audit
from reasitic.port_output_storage import PortOutputStorage
from reasitic.node_storage import PORT_ADDRESSES
from reasitic.memory import Memory
from reasitic.heap import AddressSpace
from reasitic.libio_storage import FileStorage
from reasitic.stdio_storage import OutputStream


class ShuntPortTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_port_tail_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label='wire/coarse',mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label='wire/coarse',mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=audit.compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_every_job_outcome_earlier_tls_and_complete_native_boundaries(self):
        f=self.fixture;parent=ROOT/'tests/fixtures/shunt_second_driver_original.json.gz';jobs=list(capture.second.command.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(),f['driver_history_parent_sha256'])
        self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER);directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        for raw,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(raw[key],job[key])
            t=audit.expand_tail(f,raw);self.assertEqual((raw['plain']['returncode'],raw['signal'],raw['second']['signal'],t['signal'],t['pending']),(0,0,0,0,0))
            self.assertEqual([s['label']for s in t['states']],['record_entry','record_return','close_entry','free.buffer','free.file','export_return']);self.assertEqual([s['tail_event_count']for s in t['states']],[0,0,0,0,1,2])
            self.assertEqual((len(t['events']),len(t['buffers']),len(t['printf']),len(t['end']['files'])),(2,2,1,1));self.assertEqual([r['size']for r in t['buffers']],[4108,316])
            tls=raw['transition_inputs']['port_tail_abi']['tls_base'];region=next(r for r in raw['transition_inputs']['initial_regions']if r['address']==tls)
            self.assertEqual(len(region['data']),32);self.assertEqual(struct.unpack_from('<II',bytes.fromhex(region['data']),8),(tls,0))
            for s in t['states']:
                self.assertEqual([(r['address'],len(r['data']))for r in s['memory_regions']],[(m['start'],m['end']-m['start'])for m in s['maps']if m['path']=='[heap]'])
                self.assertEqual([len(r['data'])//2 for r in s['component_regions']],[304,4096,4,16,16,16,16])
            for r in t['buffers']:self.assertEqual((t['events'][r['event_index']]['kind'],t['events'][r['event_index']]['address'],len(r['data'])),('free',r['address'],r['size']))

    def test_all_cold_warm_ground_and_coupled_files_match(self):
        for label,mode in(('wire/coarse','cold'),('wire/coarse','warm'),('wire/ground','warm'),('wire/coupled','warm')):
            with self.subTest(label=label,mode=mode):
                r,h,a,m=self.source(label,mode);self.assertEqual(r['differences'],[])
                self.assertEqual((r['events_checked'],r['buffers_checked'],r['heap_boundaries_checked'],r['printf_calls_checked'],r['printf_argument_bytes_checked'],r['files_checked'],r['unknown_bytes']),(2,2,6,1,72,1,0))
                self.assertEqual(r['buffer_bytes_checked'],4424)

    def test_record_retains_the_actual_source_stream_memory_and_heap(self):
        producer=audit.second;construct=PortOutputStorage.__init__;seen={}
        def prefix(*args,**kwargs):
            callback=kwargs['observe_continuation']
            def observe(history):seen['history']=history;callback(history)
            kwargs['observe_continuation']=observe;return producer(*args,**kwargs)
        def following(storage,history,**kwargs):
            self.assertIs(history,seen['history']);construct(storage,history,**kwargs)
            self.assertIs(storage.stream,history.port_stream);self.assertIs(storage.memory,history.memory);self.assertIs(storage.heap,history.heap);self.assertIs(storage.console,history.console)
        with patch.object(audit,'second',side_effect=prefix),patch.object(PortOutputStorage,'__init__',following):r=audit.compare(self.fixture,self.entry())
        self.assertEqual(r['differences'],[])

    def test_changed_later_file_printf_s_fields_heap_and_free_bytes_never_repair_source(self):
        baseline,h,a,m=self.source();self.assertEqual(baseline['differences'],[]);entry=copy.deepcopy(self.entry());tail=entry['port_tail'];fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        for record,key in((tail['end']['files'][0],'data'),(tail['printf'][0],'arguments'),(tail['states'][1]['component_regions'][3],'data')):
            data=bytearray.fromhex(record[key]);data[0]^=1;record[key]=data.hex()
        def alter(record):
            data=bytearray.fromhex(fixture['driver_heap_pages'][record['pages'][0]]);data[0]^=1;digest=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][digest]=data.hex();record['pages'][0]=digest
            record['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in record['pages'])).hexdigest()
        alter(tail['states'][0]['memory_regions'][0]);alter(tail['buffers'][0])
        r,other_h,other_a,other_m=audit.compare(fixture,entry,return_state=True)
        self.assertEqual({d['kind']for d in r['differences']},{'tail-file','tail-printf','tail-component-word','tail-heap-word','tail-freed-buffer'})
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_a,a);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(r['before']['differences'],[])

    def test_changed_live_guest_y_changes_s_arguments_globals_and_output(self):
        producer=audit.second
        def changed(*args,**kwargs):
            result=producer(*args,**kwargs);m=result[3];address=PORT_ADDRESSES['y11'];real,imag=struct.unpack('<2d',m.read(address,16));m.write(address,struct.pack('<2d',real+.0001,imag));return result
        with patch.object(audit,'second',side_effect=changed):r=audit.compare(self.fixture,self.entry())
        self.assertTrue({'tail-printf','tail-component-word','tail-file','tail-freed-buffer'}<={d['kind']for d in r['differences']});self.assertEqual(r['before']['differences'],[])

    def close_state(self,owner=0,depth=0,locked=0,nonhead=False):
        m=Memory(AddressSpace([dict(start=0x1000,end=0x6000)]));m.zero(0x1000,0x5000);file,buffer,head,tls,thread=0x1200,0x3000,0x1800,0x2000,0x2200
        abi=copy.deepcopy(self.entry()['libio_inputs']);abi['libc_symbols']['_IO_list_all']['address']=head
        FileStorage(m,abi).initialize(file,list_head=0);stream=OutputStream(m,file,buffer,4096,abi,3);stream.write(b'row')
        m.put_u32(file-4,321);m.put_u32(buffer-4,4113);m.put_u32(tls+8,thread);m.put_u32(head,file)
        if nonhead:m.put_u32(head,0x1900);m.put_u32(0x1900+abi['file']['fields']['_chain']['offset'],file)
        lock=m.u32(file+abi['file']['fields']['_lock']['offset']);m.write(lock,struct.pack('<3I',locked,depth,owner));points={};freed=[]
        history=SimpleNamespace(heap=SimpleNamespace(free=freed.append),memory=m,console=object(),port_stream=stream,port_name=b's.out',libio=abi,inputs={'port_tail_abi':{'tls_base':tls}})
        storage=PortOutputStorage(history,observe=lambda label,s:points.update({label:(struct.unpack('<3I',m.read(lock,12)),m.u32(head),m.u32(file+20))}))
        return storage,m,points,freed,(file,buffer,head,tls,thread)

    def test_close_locks_while_freeing_buffer_then_unlocks_and_unlinks(self):
        storage,m,p,freed,(file,buffer,head,tls,thread)=self.close_state();storage.close()
        self.assertEqual(p['free.buffer'],((1,0,thread),0,buffer));self.assertEqual(p['free.file'],((0,0,0),0,0));self.assertEqual(freed,[buffer,file])
        storage,m,p,freed,values=self.close_state(owner=0x2200,depth=2,locked=1,nonhead=True);storage.close()
        self.assertEqual(p['free.buffer'][0],(1,3,0x2200));self.assertEqual(p['free.file'][0],(1,2,0x2200));self.assertEqual(m.u32(values[2]),0x1900);self.assertEqual(m.u32(0x1900+storage.abi['file']['fields']['_chain']['offset']),0)
        for owner in(0,0x2300):
            storage,m,p,freed,values=self.close_state(owner=owner,locked=1)
            with self.assertRaisesRegex(NotImplementedError,'Contended'):storage.close()
            self.assertEqual(freed,[])

    def test_missing_list_unlink_is_not_waived_when_file_text_matches(self):
        close=PortOutputStorage.close
        def missing(storage):
            m=storage.memory;put=m.put_u32;head=storage.abi['libc_symbols']['_IO_list_all']['address']
            with patch.object(m,'put_u32',side_effect=lambda address,value:None if address==head else put(address,value)):close(storage)
        with patch.object(PortOutputStorage,'close',missing):r=audit.compare(self.fixture,self.entry())
        self.assertEqual({d['kind']for d in r['differences']},{'tail-component-word'});self.assertEqual(r['files_checked'],1);self.assertEqual(r['before']['differences'],[])


if __name__=='__main__':unittest.main()

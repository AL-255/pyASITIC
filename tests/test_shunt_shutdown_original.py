"""Native exit evidence, continuing stream ownership and unwaived gaps."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_shutdown_original as capture
import audit_shunt_shutdown_original as audit
from reasitic.script_eof_storage import ScriptEOFStorage
from reasitic.stdio_storage import InputStream
from reasitic.libio_storage import FileStorage


class ShuntShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_shutdown_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label='wire/coarse',mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label='wire/coarse',mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=audit.compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_all_unchanged_jobs_continue_to_the_actual_original_exit(self):
        f=self.fixture;jobs=list(capture.parent.second.command.shunt.shunt.jobs());parent=ROOT/'tests/fixtures/shunt_port_tail_original.json.gz'
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(),f['driver_history_parent_sha256'])
        self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory))
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        for entry,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
            t=audit.expand_shutdown(f,entry)
            self.assertEqual((entry['plain']['returncode'],entry['signal'],entry['second']['signal'],entry['port_tail']['signal'],t['exit_code'],t['signal'],t['pending'],t['interfaces']),(0,0,0,0,0,0,0,0))
            self.assertEqual([s['label']for s in t['states']],['script.read','script.eof','script.close','script.free.buffer','script.free.file','script.return','interactive.parse','exit'])
            self.assertEqual([s['shutdown_event_count']for s in t['states'][:6]],[0,0,0,0,1,2])
            stdin=entry['transition_inputs']['stdin_stream'];base=struct.unpack_from('<I',bytes.fromhex(stdin['data']),28)[0]
            self.assertEqual(stdin['file_position'],len(bytes.fromhex(stdin['file_data']))if base else 0)
            self.assertEqual(t['states'][6]['shutdown_event_count'],2 if base else 3)
            if not base:self.assertEqual({k:t['events'][2][k]for k in('kind','allocator','request','returned')},dict(kind='allocate',allocator='malloc',request=4096,returned=True))
            for s in t['states']:
                self.assertEqual([(r['address'],len(r['data']))for r in s['memory_regions']],[(m['start'],m['end']-m['start'])for m in s['maps']if m['path']=='[heap]'])
                self.assertEqual([len(r['data'])//2 for r in s['component_regions']],[304,4096,4,4460]);self.assertEqual(len(s['registers']),10)
            for b in t['buffers']:
                e=t['events'][b['event_index']];self.assertEqual((e['kind'],e['address'],len(b['data'])),('free',b['address'],b['size']))

    def test_script_closes_with_native_heap_file_buffer_and_lock_bytes(self):
        for mode in('cold','warm'):
            with self.subTest(mode=mode):
                r,h,a,m,s=self.source(mode=mode)
                self.assertEqual(r['before']['differences'],[]);self.assertTrue(s.complete)
                self.assertEqual((r['events_checked'],r['buffers_checked'],r['buffer_bytes_checked'],r['heap_boundaries_checked'],r['files_checked'],r['unknown_bytes']),(2,2,4424,6,1,0))
                # The full audit remains failing, including all later targets.
                self.assertTrue(r['differences']);self.assertGreater(r['native_events'],r['events_checked']);self.assertGreater(r['native_buffers'],r['buffers_checked']);self.assertGreater(r['native_boundaries'],r['heap_boundaries_checked'])
                self.assertNotIn('shutdown-heap-word',{d['kind']for d in r['differences']})
                self.assertNotIn('shutdown-component-word',{d['kind']for d in r['differences']})
                native=audit.expand_shutdown(self.fixture,self.entry(mode=mode))
                for actual,expected in zip(s.freed,native['buffers']):self.assertEqual(actual['data'],expected['data'])

    def test_eof_uses_the_same_inputstream_memory_heap_and_thread_state(self):
        producer=audit.port_tail;construct=ScriptEOFStorage.__init__;seen={};script_creations=[];input_init=InputStream.__init__
        def created(stream,memory,address,data,position,allocate):
            script_creations.append(stream);input_init(stream,memory,address,data,position,allocate)
        def prefix(*args,**kwargs):
            callback=kwargs['observe_continuation']
            def observe(history):seen['history']=history;callback(history)
            kwargs['observe_continuation']=observe;return producer(*args,**kwargs)
        def following(storage,history,**kwargs):
            self.assertIs(history,seen['history']);construct(storage,history,**kwargs)
            self.assertIs(storage.stream,history.script_stream);self.assertIn(storage.stream,script_creations)
            self.assertIs(storage.memory,history.memory);self.assertIs(storage.heap,history.heap);self.assertIs(storage.console,history.console)
        with patch.object(audit,'port_tail',side_effect=prefix),patch.object(ScriptEOFStorage,'__init__',following),patch.object(InputStream,'__init__',created):
            r,h,a,m,s=audit.compare(self.fixture,self.entry(),return_state=True)
        self.assertEqual(len(script_creations),1);self.assertTrue(s.complete);self.assertEqual(r['before']['differences'],[])

    def test_later_targets_never_repair_the_running_script(self):
        baseline,h,a,m,s=self.source();entry=copy.deepcopy(self.entry());native=entry['shutdown'];fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        first=native['states'][0];raw=bytearray.fromhex(first['component_regions'][0]['data']);raw[0]^=1;first['component_regions'][0]['data']=raw.hex()
        record=first['memory_regions'][0];data=bytearray.fromhex(fixture['driver_heap_pages'][record['pages'][0]]);data[0]^=1;key=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][key]=data.hex();record['pages'][0]=key;record['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in record['pages'])).hexdigest()
        native['states'][-1]['registers']['eax']^=1;native['exit_code']=37
        r,other_h,other_a,other_m,other_s=audit.compare(fixture,entry,return_state=True)
        self.assertIn('shutdown-heap-word',{d['kind']for d in r['differences']});self.assertGreater(len(r['differences']),len(baseline['differences']))
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_a,a);self.assertEqual(other_s.events,s.events)
        self.assertEqual(next(d for d in r['differences']if d['kind']=='shutdown-process-exit-missing')['original'],37)

    def test_early_file_reset_fails_even_when_the_final_heap_matches(self):
        baseline,h,a,m,s=self.source();point=ScriptEOFStorage.point
        def early_reset(storage,label):
            if label=='script.free.buffer':FileStorage(storage.memory,storage.abi).closed_byte_stream(storage.stream.address)
            point(storage,label)
        with patch.object(ScriptEOFStorage,'point',early_reset):r,other_h,other_a,other_m,other_s=audit.compare(self.fixture,self.entry(),return_state=True)
        self.assertTrue({'shutdown-heap-word','shutdown-component-word'}<={d['kind']for d in r['differences']})
        self.assertGreater(len(r['differences']),len(baseline['differences']))
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_h.tcache,h.tcache);self.assertEqual(other_s.events,s.events)


if __name__=='__main__':unittest.main()

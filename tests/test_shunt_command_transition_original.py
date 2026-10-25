"""Branch command continuation, native provenance and later-target independence."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_command_transition_original as capture
import audit_shunt_command_transition_original as audit
from capture_command_transition_original import expand_case
from reasitic.command_transition import CommandTransition
from reasitic.command_storage import Characters,CommandStorage,ScanHistory
from reasitic.geometry_storage import GeometryStorage
from reasitic.memory import Memory
from reasitic.heap import AddressSpace


class ShuntCommandTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_command_transition_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label,mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label,mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=audit.compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_all_original_jobs_outcomes_complete_heaps_and_parent_provenance(self):
        f=self.fixture;path=ROOT/'tests/fixtures/shunt_node_history_original.json.gz';parent=json.loads(gzip.decompress(path.read_bytes()));jobs=list(capture.shunt.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        drivers=[]
        for raw,old,job in zip(f['cases'],parent['cases'],(j for j in jobs for _ in range(2))):
            c=expand_case(f,raw)
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key]);self.assertEqual(c[key],old[key])
            self.assertEqual((c['plain']['returncode'],c['signal'],c['post_driver']['status']),(0,0,1))
            self.assertEqual((len(c['transition_events']),len(c['transition_buffers']),len(c['transition_states']),c['transition_pending'],c['transition_interfaces']),(5,1,1,0,0))
            self.assertEqual([p['kind']for p in c['transition_points']],['parse','header']);self.assertEqual(len(c['transition_calendar']),1);drivers.append(c['transition_end']['driver'])
            for s in c['transition_states']:self.assertEqual([(r['address'],len(r['data'])//2)for r in s['memory_regions']],[(m['start'],m['end']-m['start'])for m in s['maps']if m['path']=='[heap]'])
            for b in c['transition_buffers']:
                event=c['transition_events'][b['event_index']];self.assertEqual((event['kind'],event['address']),('free',b['address']));self.assertEqual(len(b['data']),2*b['size'])
        self.assertEqual((drivers.count('pi2'),drivers.count('calctrans')),(22,6))

    def test_grounded_default_and_coupled_next_entries_match(self):
        for label,mode in(('wire/ground','cold'),('wire/ground','warm'),('wire/coarse','warm'),('wire/coupled','warm')):
            with self.subTest(label=label,mode=mode):
                r,h,a,m=self.source(label,mode);self.assertEqual(r['differences'],[])
                self.assertEqual((r['events_checked'],r['buffers_checked'],r['points_checked'],r['files_checked'],r['calendar_calls_checked'],r['unknown_bytes']),(5,1,2,1,1,0))
                self.assertEqual(r['before']['differences'],[])

    def test_outer_parser_continues_on_identical_driver_memory(self):
        producer=audit.node;run=CommandTransition.run;seen={}
        def prefix(*args,**kwargs):
            value=producer(*args,**kwargs);seen['memory']=value[3];seen['heap']=value[1];return value
        def continuation(history):
            self.assertIs(history.memory,seen['memory']);self.assertIs(history.heap,seen['heap']);run(history);seen['result']=history.result
        with patch.object(audit,'node',side_effect=prefix),patch.object(CommandTransition,'run',continuation):r=audit.compare(self.fixture,self.entry('wire/ground'))
        self.assertEqual(r['differences'],[]);self.assertEqual(seen['result']['arguments'],self.entry('wire/ground')['transition_end']['arguments'])
        self.assertNotEqual(*seen['result']['arguments'])

    def test_type_eight_resets_only_primary_counts_and_empty_shape(self):
        m=Memory(AddressSpace([dict(start=0x1000,end=0x3000)]));m.write(0x1000,bytes([0x5a])*0x2000)
        shape,other,first,last,child,argument=0x1000,0x1100,0x1200,0x1300,0x1400,0x1800
        m.put_u32(shape+0xa8,first);m.put_u32(other+0xa8,0);m.put_u32(first+0xec,last);m.put_u32(last+0xec,0);m.put_u32(first+0xe8,child);m.put_u32(child+0xe8,0)
        m.write(argument,b'G\0');before=m.read(0x1000,0x2000);expected=bytearray(before)
        geometry=GeometryStorage(None,m,shape);parser=CommandStorage(m,Characters(self.entry('wire/ground')['transition_inputs']['character_tables']),lambda name:shape if name==b'G'else other,lambda text:self.fail(text),reset_mesh=geometry.reset_mesh_counts)
        self.assertTrue(parser.parse_argument(argument,8,ScanHistory(None,None,None)))
        struct.pack_into('<I',expected,argument+256-0x1000,shape)
        for address in(first,last):struct.pack_into('<II',expected,address+0xe0-0x1000,0xffffffff,0xffffffff)
        self.assertEqual(m.read(0x1000,0x2000),bytes(expected))
        geometry.reset_mesh_counts(other);self.assertEqual(m.read(0x1000,0x2000),bytes(expected))
        # Ordinary shape arguments must leave every mesh count alone.
        m.write(0x1000,before);self.assertTrue(parser.parse_argument(argument,0,ScanHistory(None,None,None)))
        struct.pack_into('<I',expected:=bytearray(before),argument+256-0x1000,shape);self.assertEqual(m.read(0x1000,0x2000),bytes(expected))

    def test_later_files_calendar_arguments_and_heap_cannot_repair_source(self):
        baseline,h,a,m=self.source('wire/coarse');self.assertEqual(baseline['differences'],[])
        entry=copy.deepcopy(self.entry('wire/coarse'));fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']))
        for record,key in((entry['transition_end']['files'][0],'data'),(entry['transition_calendar'][0],'text'),(entry['transition_points'][0]['regions'][0],'data')):
            data=bytearray.fromhex(record[key]);data[0]^=1;record[key]=data.hex()
        entry['transition_end']['arguments'][1]+=4
        region=entry['transition_states'][0]['memory_regions'][0];data=bytearray.fromhex(fixture['driver_heap_pages'][region['pages'][0]]);data[0]^=1;digest=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][digest]=data.hex();region['pages'][0]=digest
        region['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in region['pages'])).hexdigest()
        r,other_h,other_a,other_m=audit.compare(fixture,entry,return_state=True)
        self.assertEqual({d['kind']for d in r['differences']},{'transition-file','transition-calendar','transition-point-word','transition-next-driver','transition-heap-word'})
        self.assertEqual(other_m._pages,m._pages);self.assertEqual(other_a,a);self.assertEqual(other_h.tcache,h.tcache)

    def test_suppressed_ground_reset_fails_complete_native_heap(self):
        # This native script already reset G in its first PI2 command, so the
        # following reset is idempotent. Give the outer parser different
        # incoming counts to prove it performs the operation, not just that
        # its unchanged memory happens to match this capture.
        producer=audit.node;entry=self.entry('wire/ground');ground=entry['setup_context']['arguments'][1]
        def changed(*args,**kwargs):
            value=producer(*args,**kwargs);m=value[3]
            for address in GeometryStorage(value[1],m,ground).segments(ground):m.write(address+0xe0,struct.pack('<II',9,10))
            return value
        with patch.object(audit,'node',side_effect=changed):self.assertEqual(audit.compare(self.fixture,entry)['differences'],[])
        with patch.object(audit,'node',side_effect=changed),patch.object(GeometryStorage,'reset_mesh_counts',return_value=None):r=audit.compare(self.fixture,entry)
        self.assertTrue(any(d['kind']=='transition-heap-word'for d in r['differences']));self.assertEqual(r['before']['differences'],[])
        self.assertFalse(any(d['kind']=='transition-next-driver'for d in r['differences']))

    def test_changed_ground_lookup_changes_source_handoff(self):
        find=CommandTransition.find_shape
        def changed(history,name):return find(history,b'A'if name==b'G'else name)
        with patch.object(CommandTransition,'find_shape',changed):r=audit.compare(self.fixture,self.entry('wire/ground'))
        next_entry=[d for d in r['differences']if d['kind']=='transition-next-driver'];self.assertEqual(len(next_entry),1)
        self.assertEqual(next_entry[0]['actual']['arguments'][0],next_entry[0]['actual']['arguments'][1]);self.assertEqual(r['before']['differences'],[])


if __name__=='__main__':unittest.main()

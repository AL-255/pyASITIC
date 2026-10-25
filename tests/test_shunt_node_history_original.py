"""Native branch node/cleanup state, shared memory, and strict later targets."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_node_history_original as capture
import audit_shunt_node_history_original as audit
from capture_node_history_original import expand_case
from reasitic.node_storage import NodeStorage,PORT_ADDRESSES
from reasitic.console_storage import ConsoleStorage
from reasitic import node_storage


class ShuntNodeHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_node_history_original.json.gz').read_bytes()));cls.results={}

    def entry(self,label,mode='warm'):return next(c for c in self.fixture['cases']if(c['label'],c['cache_mode'])==(label,mode))

    def source(self,label,mode='warm'):
        key=(label,mode)
        if key not in self.results:self.results[key]=audit.compare(self.fixture,self.entry(*key),return_state=True)
        return self.results[key]

    def test_every_native_request_outcome_full_buffer_and_heap_is_retained(self):
        f=self.fixture;parent_path=ROOT/'tests/fixtures/shunt_driver_history_original.json.gz';parent=json.loads(gzip.decompress(parent_path.read_bytes()));jobs=list(capture.shunt.jobs())
        self.assertEqual((len(jobs),len(f['cases'])),(14,28));self.assertEqual(f['driver_history_parent_sha256'],hashlib.sha256(parent_path.read_bytes()).hexdigest())
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for bank in('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
            for digest,data in f[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        maximum=0
        for raw,old,job in zip(f['cases'],parent['cases'],(j for j in jobs for _ in range(2))):
            case=expand_case(f,raw)
            for key in('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key]);self.assertEqual(case[key],old[key])
            self.assertEqual((case['plain']['returncode'],case['signal'],case['post_output']['status'],case['post_driver']['status']),(0,0,1,1))
            self.assertEqual((len(case['events']),len(case['workspace_storage'])),(len(old['events']),len(old['workspace_storage'])))
            self.assertEqual((len(case['post_events']),len(case['post_buffers']),case['post_pending'],case['post_interfaces']),(14,8,0,0))
            self.assertTrue(all(e['returned']for e in case['post_events']));self.assertEqual([s['label']for s in case['post_states']],['node_release','node_return','driver_return'])
            for state in case['post_states']:self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
            for record in case['post_buffers']:
                event=case['post_events'][record['event_index']];self.assertEqual((event['kind'],event['address']),('free',record['address']));self.assertEqual(len(record['data']),2*record['size']);maximum=max(maximum,record['size'])
        self.assertEqual(maximum,18496);self.assertEqual(sum(len(c['console_calls'])for c in f['cases']),838)

    def test_complete_cold_warm_and_eddy_coupled_unequal_histories_match(self):
        for label,mode in(('wire/coarse','cold'),('wire/coarse','warm'),('wire/eddy','warm'),('square/eddy','warm'),('wire/repeated-coupled','warm'),('unequal-branch/asymmetric','warm')):
            with self.subTest(label=label,mode=mode):
                r,h,a,m=self.source(label,mode);self.assertEqual(r['differences'],[])
                self.assertEqual((r['events_checked'],r['allocations_checked'],r['buffers_checked'],r['heap_boundaries_checked']),(14,6,8,3))
                self.assertEqual((r['port_words_checked'],r['port_memory_words_checked'],r['unknown_port_bytes'],r['unknown_heap_bytes']),(16,16,0,0))
                for name,record in zip(('y11','y12','y21','y22'),self.entry(label,mode)['post_driver']['ports']):self.assertEqual(m.read(PORT_ADDRESSES[name],16).hex(),record['data'])

    def test_node_uses_the_same_driver_memory_and_publishes_in_native_order(self):
        producer=audit.driver;publish=NodeStorage.publish_ports;seen={};writes=[]
        def prefix(*args,**kwargs):
            result=producer(*args,**kwargs);seen['memory']=result[3];return result
        def store(history):
            self.assertIs(history.memory,seen['memory']);write=history.memory.write
            def trace(address,data):writes.append(address);write(address,data)
            with patch.object(history.memory,'write',side_effect=trace):publish(history)
        with patch.object(audit,'driver',side_effect=prefix),patch.object(NodeStorage,'publish_ports',store):result=audit.compare(self.fixture,self.entry('wire/coarse'))
        self.assertEqual(result['differences'],[]);self.assertEqual(writes,[PORT_ADDRESSES[k]for k in('y22','y11','y21','y12')])

    def test_later_ports_cap_buffers_and_extents_do_not_initialize_source(self):
        baseline,heap,addresses,memory=self.source('wire/coarse');self.assertEqual(baseline['differences'],[])
        for field in('ports','capacitance','buffer','extent','port_owner'):
            entry=copy.deepcopy(self.entry('wire/coarse'))
            if field=='ports':record=entry['post_output']['ports'][0];key='data'
            elif field=='capacitance':record=entry['post_output'];key='capacitance'
            elif field=='buffer':record=entry['post_buffers'][0];key='pages'
            elif field=='extent':entry['post_node']['size']=99
            else:entry['post_output']['ports'][0]['address']+=16
            fixture=self.fixture
            if field in('ports','capacitance'):
                data=bytearray.fromhex(record[key]);data[0]^=1;record[key]=data.hex()
            elif field=='buffer':
                fixture=dict(self.fixture,driver_heap_pages=dict(self.fixture['driver_heap_pages']));data=bytearray.fromhex(fixture['driver_heap_pages'][record['pages'][0]]);data[0]^=1;digest=hashlib.sha256(data).hexdigest();fixture['driver_heap_pages'][digest]=data.hex();record['pages'][0]=digest
                record['sha256']=hashlib.sha256(b''.join(bytes.fromhex(fixture['driver_heap_pages'][p])for p in record['pages'])).hexdigest()
            result,other_heap,other_addresses,other_memory=audit.compare(fixture,entry,return_state=True)
            expected={'ports':{'node-port','node-port-memory'},'capacitance':{'node-cap-word'},'buffer':{'node-buffer-word'},'extent':{'node-owner'},'port_owner':{'node-port-owner'}}[field]
            self.assertEqual({d['kind']for d in result['differences']},expected);self.assertEqual(other_memory._pages,memory._pages);self.assertEqual(other_addresses,addresses);self.assertEqual(other_heap.tcache,heap.tcache)

    def test_deferred_prefix_and_model_console_assertions_remain_strict(self):
        baseline,heap,addresses,memory=self.source('wire/coarse')
        for index in(0,-1):
            entry=copy.deepcopy(self.entry('wire/coarse'));record=entry['console_calls'][index];raw=bytearray.fromhex(record['text']);raw[0]^=1;record['text']=raw.hex()
            result,h,a,m=audit.compare(self.fixture,entry,return_state=True)
            self.assertEqual([d['kind']for d in result['differences']],['console-call']);self.assertEqual(result['before']['differences'],[]);self.assertEqual(m._pages,memory._pages)

    def test_missing_guest_global_stores_fail_even_when_computed_ports_match(self):
        with patch.object(NodeStorage,'publish_ports',return_value=None):result=audit.compare(self.fixture,self.entry('wire/coarse'))
        self.assertEqual({d['kind']for d in result['differences']},{'unknown-node-port-memory'});self.assertEqual(result['unknown_port_bytes'],128);self.assertEqual(result['port_words_checked'],16)

    def test_wrong_rhs_and_missing_model_reports_are_not_waived(self):
        original=node_storage.folded
        def wrong(*args,**kwargs):
            result=original(*args,**kwargs);kwargs['storage']['rhs']=[0j]*len(args[0]);return result
        with patch.object(node_storage,'folded',side_effect=wrong):result=audit.compare(self.fixture,self.entry('wire/coarse'))
        kinds={d['kind']for d in result['differences']};self.assertTrue({'node-buffer-word','post-heap-word'}<=kinds);self.assertNotIn('node-port',kinds)
        with patch.object(ConsoleStorage,'report_nodes',return_value=None):result=audit.compare(self.fixture,self.entry('wire/coarse'))
        kinds={d['kind']for d in result['differences']};self.assertTrue({'post-heap-word','console-call-count'}<=kinds);self.assertNotIn('node-port',kinds)


if __name__=='__main__':unittest.main()

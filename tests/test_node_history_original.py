"""Complete node lifetimes, independent later outputs, and continuous memory."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_node_history_original as capture
from capture_prelude_storage_extended_original import jobs as extra_jobs
from audit_node_history_original import compare
from reasitic import node_storage


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class NodeHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('node_history_original.json.gz');cls.extended=load('node_history_extended_original.json.gz')

    def test_every_native_job_full_freed_buffer_and_boundary_heap_retained(self):
        large=0;cases=0
        for fixture,jobs,parent in ((self.fixture,list(capture.console.driver.cache.libio.prelude.geometry.arena.lifetime.jobs()),'console_storage_original.json.gz'),(self.extended,list(extra_jobs()),'console_storage_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            previous=load(parent)
            for entry,old,job in zip(fixture['cases'],previous['cases'],(j for j in jobs for _ in range(2))):
                cases+=1
                for key in ('label','request','script','stdin','variant'):self.assertEqual(entry[key],job[key])
                self.assertEqual(entry['cache_mode'],old['cache_mode']);self.assertEqual(entry['node']is None,old['node']is None)
                self.assertEqual(len(entry['events']),len(old['events']))
                case=capture.expand_case(fixture,entry)
                for state in case['post_states']:
                    self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
                for record in case['post_buffers']:
                    event=case['post_events'][record['event_index']];self.assertEqual(event['kind'],'free');self.assertEqual(event['address'],record['address'])
                    self.assertEqual(len(record['data']),record['size']*2);large=max(large,record['size'])
                if case['node']is not None:
                    self.assertEqual(case['post_driver']['status'],1);self.assertEqual(case['post_output']['status'],1)
                    self.assertEqual([s['label']for s in case['post_states']],['node_release','node_return','driver_return'])
                    self.assertEqual(len(case['post_events']),14);self.assertEqual(len(case['post_buffers']),8)
                    self.assertTrue(all(e['returned']for e in case['post_events']));self.assertEqual(case['post_pending'],0);self.assertEqual(case['post_interfaces'],0)
                else:self.assertEqual(case['signal'],11);self.assertEqual(case['post_events'],[])
            for bank in ('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
                for digest,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
        self.assertEqual(cases,134);self.assertEqual(large,65536)

    def test_all_small_complete_node_and_driver_histories_exact(self):
        reports=[compare(self.extended,entry)for entry in self.extended['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*4)
        self.assertEqual(sum(r['events_checked']for r in reports),56);self.assertEqual(sum(r['buffers_checked']for r in reports),32)
        self.assertEqual(sum(r['heap_words_checked']for r in reports),417792)
        self.assertEqual(sum(r['port_words_checked']for r in reports),64)

    def test_plain_faults_remain_explicit_beyond_first_driver_return(self):
        from collections import Counter
        self.assertEqual(Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:125,-6:4,-11:1})
        self.assertEqual(Counter(c['plain']['returncode']for c in self.extended['cases']),{0:3,-6:1})
        old=load('console_storage_original.json.gz')
        changed=[(a['label'],a['cache_mode'],a['plain']['returncode'],b['plain']['returncode'])for a,b in zip(old['cases'],self.fixture['cases'])if a['plain']['returncode']!=b['plain']['returncode']]
        self.assertEqual(changed,[('square/1/coarse','cold',0,-6),('pilot-width3/1/coarse','cold',-6,0),('pilot-width3/1/coarse','warm',0,-6),('pilot-width3/1/contacts','warm',-6,0)])
        for fixture in (self.fixture,self.extended):
            for case in fixture['cases']:
                if case['plain']['returncode']==-6:
                    self.assertEqual(case['post_driver']['status'],1)
                    self.assertEqual(case['plain']['stderr'],'malloc(): unaligned tcache chunk detected\n'if fixture is self.fixture else'double free or corruption (!prev)\n')

    def test_later_port_and_cap_bytes_do_not_seed_runtime(self):
        for field in ('ports','capacitance'):
            entry=copy.deepcopy(self.extended['cases'][1]);output=entry['post_output']
            if field=='ports':output['ports'][0]['data']='00'+output['ports'][0]['data'][2:]
            else:output['capacitance']='00'+output['capacitance'][2:]
            result=compare(self.extended,entry)
            # Both the computed result and its actual guest-global stores
            # remain independent of the changed later port observation.
            self.assertEqual({d['kind']for d in result['differences']},{'node-port','node-port-memory'}if field=='ports'else{'node-cap-word'})

    def test_later_node_extent_does_not_control_source_allocations(self):
        entry=copy.deepcopy(self.extended['cases'][1]);entry['post_node']['size']=99
        result=compare(self.extended,entry)
        self.assertEqual([d['kind']for d in result['differences']],['node-owner'])
        self.assertEqual(result['allocations_checked'],6)

    def test_wrong_final_rhs_is_detected_despite_exact_ports(self):
        original=node_storage.folded
        def wrong(*args,**kwargs):
            result=original(*args,**kwargs);kwargs['storage']['rhs']=[0j]*len(args[0]);return result
        with patch.object(node_storage,'folded',side_effect=wrong):result=compare(self.extended,self.extended['cases'][1])
        kinds={d['kind']for d in result['differences']}
        self.assertIn('node-buffer-word',kinds);self.assertIn('post-heap-word',kinds)
        self.assertNotIn('node-port',kinds);self.assertNotIn('console-call',kinds)


if __name__=='__main__':unittest.main()

"""Continuous source memory, independent later outputs and strict missing stores."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_driver_history_original as capture
import capture_driver_history_extended_original as extended
from capture_cache_storage_original import expand_files
from audit_driver_history_original import compare
from audit_cache_storage_original import compare as cache
from audit_shared_heap_original import ported_impedance,ported_inductance_geometry,via_records,seed
from audit_cap_prelude_original import dimensions
from reasitic.allocation_plan import combined_network_storage
from reasitic.bridge import _mesh
from reasitic.solver import filament_counts
from reasitic.storage_history import StorageHistory
from reasitic.memory import Memory
from reasitic.cache_storage import CacheStorage
from reasitic.heap import Heap
from reasitic.prelude_storage import table_storage


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class DriverHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('driver_history_original.json.gz');cls.extended=load('driver_history_extended_original.json.gz')

    def test_all_original_inputs_full_boundary_heaps_and_workspaces_retained(self):
        for fixture,jobs,parent in ((self.fixture,list(capture.cache.libio.prelude.geometry.arena.lifetime.jobs()),'cache_storage_original.json.gz'),(self.extended,list(extended.jobs()),'cache_storage_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['driver_history_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            for bank in ('driver_heap_pages','cache_file_pages','storage_pages','storage_blobs'):
                for digest,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
            for i,job in enumerate(jobs):
                cold,warm=fixture['cases'][2*i:2*i+2];self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain'])
                for entry,mode in ((cold,'cold'),(warm,'warm')):
                    with self.subTest(label=job['label'],mode=mode):
                        case=capture.expand_case(fixture,entry)
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode)
                        self.assertEqual({name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())for name,data in expand_files(fixture,case)},case['initial_cache'])
                        for state in case['allocator_states']:
                            self.assertEqual([(r['address'],len(r['data'])//2)for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])
                        regions=case['allocator_states'][0]['memory_regions'];address=case['cache_inputs']['coefficient_address']
                        self.assertTrue(any(r['address']<=address<r['address']+len(r['data'])//2 for r in regions))
                        for record in case['workspace_storage']:
                            event=case['events'][record['event_index']];self.assertEqual(event['kind'],'free');self.assertEqual(event['address'],record['address'])
                            self.assertEqual(len(record['data']),2*record['size']);self.assertLessEqual(record['size'],16384)
                        script=fixture['gdb_commands'].encode();self.assertEqual(case['initial_files']['capture.gdb'],dict(size=len(script),sha256=hashlib.sha256(script).hexdigest()))
        self.assertEqual(sum(len(c['workspace_storage'])for c in self.fixture['cases']),2735)
        self.assertTrue(all(c['via']is None for c in self.extended['cases']))
        self.assertEqual(self.extended['cases'][2]['plain']['returncode'],-6)

    def test_small_live_cache_outputs_and_workspaces_with_missing_heap_stores_visible(self):
        reports=[compare(self.extended,c)for c in self.extended['cases']]
        for report in reports:
            # This component produces all numerical values, while the strict
            # executable still fails on every missing logging/heap word.
            self.assertTrue(all(d['kind']=='heap-word'for d in report['differences']),report['differences'])
            self.assertGreater(report['heap_words_checked'],0);self.assertEqual(report['unknown_heap_bytes'],0)
            self.assertEqual(report['driver']['differences'],[])
        self.assertEqual(sum(r['workspace_arrays_checked']for r in reports),56)
        self.assertEqual(sum(r['workspace_bytes_checked']for r in reports),672)
        self.assertEqual(sum(r['cap_words_checked']for r in reports),8)
        self.assertEqual(sum(r['ind_words_checked']for r in reports),8)
        self.assertEqual(sum(r['heap_words_checked']for r in reports),139264)

    def test_constructor_continues_existing_bytes_without_any_seed_store(self):
        entry=self.extended['cases'][1];report,heap,addresses,memory=cache(self.extended,entry,return_state=True)
        prepared=ported_impedance(entry)
        args=dict(initial_regions=(),key=heap._cache_key,contacts=(),capacitance={},impedance=prepared,technology=None,mesh={},geometry_addresses=(),via_records=(),memory=memory)
        with patch.object(memory,'write',side_effect=AssertionError('Continuation tried to reseed memory')):
            history=StorageHistory(heap,addresses,**args)
        self.assertIs(history.memory,memory)
        for override in (dict(initial_regions=[(0,b'bad')]),dict(memory=Memory(heap.address_space)),dict(key=heap._cache_key^1)):
            with self.assertRaises(ValueError):StorageHistory(heap,addresses,**dict(args,**override))

    def test_native_dense_freed_matrix_retains_zero_lower_triangle(self):
        entry=next(c for c in self.fixture['cases']if c['label']=='square/4/filaments'and c['cache_mode']=='warm')
        report=compare(self.fixture,entry)
        self.assertTrue(all(d['kind']=='heap-word'for d in report['differences']),report['differences'])
        self.assertGreater(report['workspace_arrays_checked'],0)

    def test_native_large_remainder_clears_survive_as_later_header_words(self):
        entry=next(c for c in self.fixture['cases']if c['label']=='square/3/contacts'and c['cache_mode']=='warm')
        report=compare(self.fixture,entry)
        self.assertTrue(all(d['kind']=='heap-word'for d in report['differences']),report['differences'])
        with patch.object(Heap,'_clear_nextsize',return_value=None):without=compare(self.fixture,entry)
        self.assertIn('physical-chunks',{d['kind']for d in without['differences']})

    def test_native_fastbin_words_use_header_pointers_and_address_encoding(self):
        entry=next(c for c in self.fixture['cases']if c['label']=='square/4/contacts'and c['cache_mode']=='warm')
        report,heap,addresses,memory=compare(self.fixture,entry,return_state=True)
        state=next(s for s in entry['allocator_states']if s['label']=='node')
        self.assertEqual(heap.fastbins,state['fastbins']);checked=0
        for chain in state['fastbins']:
            for i,p in enumerate(chain):
                following=chain[i+1]if i+1<len(chain)else 0
                self.assertEqual(memory.u32(p+8),following^((p+8)>>12));checked+=1
        self.assertGreater(checked,0)
        with patch.object(Heap,'_fastbin_store',return_value=None):
            report,heap,addresses,memory=compare(self.fixture,entry,return_state=True)
        self.assertTrue(any(memory.u32(p+8)!=(chain[i+1]if i+1<len(chain)else 0)^((p+8)>>12)for chain in state['fastbins']for i,p in enumerate(chain)))

    def test_native_bin_links_size_rings_and_arena_heads_after_source_lifetimes(self):
        # Exercise the allocator's bytes independently of matrix arithmetic.
        # Every request and free identity still comes from the source plan.
        entry=next(c for c in self.fixture['cases']if c['label']=='square/48/coarse'and c['cache_mode']=='warm')
        report,heap,addresses,memory=cache(self.fixture,entry,return_state=True)
        self.assertEqual(report['differences'],[])
        shape,technology=ported_inductance_geometry(entry);mesh=_mesh(entry['request'],technology)
        conductors=[s for s in shape.segments if s.metal<len(technology.metals)]
        filaments=sum(y*z for s in conductors for y,z in [filament_counts(s,mesh['width_cell'],mesh['thickness_cell'],mesh.get('max_width_cells',500))])
        plan=combined_network_storage(dimensions(entry)[0],len(conductors),filaments,len(via_records(entry)),clone_segments=len(shape.segments))
        native=[e for e in entry['events']if e['kind']in ('allocate','free')]
        self.assertEqual(len(plan),len(native))
        for event,observed in zip(plan,native):
            self.assertEqual((event.action,event.allocator),(observed['kind'],observed['allocator']))
            if event.action=='allocate':
                self.assertEqual(event.size,observed['request']);address=heap.malloc(event.size);addresses[event.name]=address
            else:address=addresses[event.name];heap.free(address)
            self.assertEqual(address,observed['address'])
        case=capture.expand_case(self.fixture,entry);state=next(s for s in case['allocator_states']if s['label']=='node')
        self.assertEqual(heap.bins[1:],state['bins']);expected=Memory(heap.address_space);seed(expected,state);large=0
        for index,chain in enumerate(heap.bins[1:],1):
            head=heap._bin_head(index);self.assertEqual(memory.read(head+8,8),expected.read(head+8,8))
            for p in chain:
                size=16 if heap.chunks[p].size>=1008 else 8
                self.assertEqual(memory.read(p+8,size),expected.read(p+8,size))
                large+=int(index!=1 and size==16)
        self.assertGreater(large,0)

    def test_isolated_rectangular_table_padding_fails_native_capacitance(self):
        def isolated(cache,source,target):return table_storage(cache.technology,cache.frequency,source,target)[:3]
        with patch.object(CacheStorage,'__call__',isolated):report=compare(self.extended,self.extended['cases'][3])
        self.assertTrue(any(d['kind']=='node-word'and d['name']=='cap.output'for d in report['differences']))

    def test_later_via_owners_and_words_do_not_repair_source_memory(self):
        case=copy.deepcopy(self.fixture['cases'][1]);case['via']['shape_address']+=16;case['via']['segment_addresses'][0]+=16
        next(s for s in case['allocator_states']if s['label']=='via_entry')['tcache_key']^=1
        event=next(e for e in case['events']if e['kind']=='via_write');raw=bytearray.fromhex(event['before']);raw[0]^=1;event['before']=raw.hex()
        report=compare(self.fixture,case)
        kinds={d['kind']for d in report['differences']}
        self.assertTrue({'via-shape-owner','via-segment-owners','before-store','cache-key'}<=kinds)
        self.assertNotIn('after-store',kinds);self.assertNotIn('node-word',kinds)
        self.assertEqual(report['stores_checked'],1)


if __name__=='__main__':unittest.main()

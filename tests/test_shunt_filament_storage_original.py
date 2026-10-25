"""Native branch tables, cleanup, reused contacts and actual shared stores."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_shunt_filament_storage_original as capture
from audit_shunt_filament_storage_original import compare,run
from audit_shared_heap_original import ported_inductance_geometry
from reasitic.filament_storage import FilamentLayout


class ShuntFilamentStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_filament_storage_original.json.gz').read_bytes()))

    def test_every_original_job_observer_plain_outcome_and_array_extent(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(jobs),14);self.assertEqual(len(f['cases']),28)
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(directory));self.assertEqual(f['allocator_provenance']['observer'],capture.OBSERVER)
        self.assertEqual(f['shunt_filament_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/shunt_geometry_storage_original.json.gz').read_bytes()).hexdigest())
        self.assertEqual(f['allocator_provenance']['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key])
            self.assertEqual((c['plain']['returncode'],c['signal'],c['pending']),(0,0,0));self.assertEqual(c['filament_context']['control'],0x37f)
            n=c['filament_context'];self.assertGreater(n['segment_count'],n['groups']);self.assertEqual(n['arrays']['extra_segments']['size'],4*n['groups'])
            for key in('segments','width_counts','thickness_counts'):self.assertEqual(n['arrays'][key]['size'],4*n['segment_count'])
            for item in n['arrays'].values():self.assertEqual(len(bytes.fromhex(item['data'])),item['size'])
            for w in c['workspace_storage']:
                self.assertLessEqual(w['size'],16384);self.assertEqual(len(bytes.fromhex(w['data'])),w['size']);self.assertEqual(c['events'][w['event_index']]['kind'],'free')
            self.assertEqual([s['label']for s in c['contact_storage']],['prepared','numbered'])

    def test_all_native_tables_cleanup_and_allocator_lifetimes(self):
        reports=[compare(c)for c in self.fixture['cases']]
        for r in reports:
            with self.subTest(label=r['label'],mode=r['cache_mode']):self.assertEqual(r['differences'],[])
        for key,value in(('events_checked',1950),('allocations_checked',542),('tables_checked',122),('table_bytes_checked',4736),('released_tables_checked',122),('released_table_bytes_checked',4736),('geometry_bytes_checked',92144),('cleanup_records_checked',362),('allocator_boundaries_checked',28)):self.assertEqual(sum(r[key]for r in reports),value)

    def test_public_mesh_preflight_counts_all_native_secondary_conductors(self):
        from reasitic.bridge import handle
        for case in self.fixture['cases'][::2]:
            with self.subTest(label=case['label']):
                plan=handle(dict(case['request'],action='mesh',model=case['request']['action']))
                self.assertEqual(plan['filaments'],case['filament_context']['filaments'])
                self.assertEqual(plan['segments'],case['filament_context']['groups'])
                self.assertEqual(plan['within_limit'],plan['filaments']<=256)

    def test_reused_group_headers_and_contacts_match_every_defined_native_field(self):
        from audit_contact_storage_original import compare as contacts
        reports=[contacts(c)for c in self.fixture['cases']]
        for r in reports:
            with self.subTest(label=r['label'],mode=r['cache_mode']):self.assertEqual(r['differences'],[])
        self.assertEqual(sum(r['objects_checked']for r in reports),1064);self.assertEqual(sum(r['bytes_checked']for r in reports),61584);self.assertEqual(sum(r['unknown_bytes']for r in reports),28096)

    def test_actual_storage_history_hooks_include_the_branch_through_native_node(self):
        from audit_shunt_filament_storage_original import compare_branch_history
        reports=[compare_branch_history(c)for c in self.fixture['cases']];self.assertEqual(len(reports),28)
        for report in reports:
            with self.subTest(label=report['label'],mode=report['cache_mode']):self.assertEqual(report['differences'],[])
        for key,value in(('events_checked',1950),('workspace_arrays_checked',476),('workspace_bytes_checked',193592),('node_words_checked',12576),('via_stores_checked',14),('via_words_checked',56)):self.assertEqual(sum(r[key]for r in reports),value)

    def test_later_numerical_workspace_and_via_words_cannot_change_source_execution(self):
        from audit_shunt_filament_storage_original import compare_branch_history
        for label,field,kind in(('wire/eddy','workspace_storage','branch-history-workspace'),('square/coarse','events','branch-history-via-after')):
            case=next(c for c in self.fixture['cases']if c['label']==label and c['cache_mode']=='cold')
            baseline,heap,addresses,memory,produced=compare_branch_history(case,return_state=True);self.assertEqual(baseline['differences'],[])
            changed=copy.deepcopy(case)
            if field=='workspace_storage':
                target=max((w for w in changed[field]if w['address']==addresses['ind.final_inverse.inverse_work']),key=lambda w:w['event_index']);key='data'
            else:target=next(e for e in changed[field]if e['kind']=='via_write');key='after'
            raw=bytearray.fromhex(target[key]);raw[0]^=1;target[key]=raw.hex()
            report,other_heap,other_addresses,other_memory,other=compare_branch_history(changed,return_state=True)
            self.assertEqual([d['kind']for d in report['differences']],[kind]);self.assertEqual(other,produced);self.assertEqual(other_addresses,addresses);self.assertEqual(other_heap.tcache,heap.tcache)

    def test_omitting_source_eddy_fold_fails_native_first_node(self):
        from audit_shunt_filament_storage_original import compare_branch_history
        from reasitic.storage_history import StorageHistory
        case=next(c for c in self.fixture['cases']if c['label']=='wire/eddy'and c['cache_mode']=='cold')
        with patch.object(StorageHistory,'released',return_value=None):report=compare_branch_history(case)
        self.assertIn('branch-history-node',[d['kind']for d in report['differences']])

    def test_memory_attachment_defers_geometry_reads_until_the_filament_plan(self):
        from audit_geometry_setup_original import compare as setup
        from audit_shared_heap_original import ported_impedance
        from reasitic.storage_history import StorageHistory
        case=self.fixture['cases'][0];prefix,heap,addresses,memory=setup(case,return_state=True);self.assertEqual(prefix['differences'],[])
        prepared=ported_impedance(case);shape,technology=ported_inductance_geometry(case)
        parents=[addresses[f'geometry.segment.{i}']for i in range(len(shape.segments))]
        with patch.object(memory,'read',side_effect=AssertionError('Attachment read numerical geometry')),patch.object(memory,'write',side_effect=AssertionError('Attachment rewrote continuing memory')):
            history=StorageHistory(heap,addresses,initial_regions=(),key=heap._cache_key,contacts=(),capacitance={},impedance=prepared,technology=None,mesh={},geometry_addresses=parents,via_records=(),memory=memory)
        self.assertIs(history.memory,memory);self.assertIsNone(history._filament_layout)
        history.technology=technology
        self.assertEqual(history.filament_layout.group_segments,(2,))
        self.assertEqual(history.filament_pointers,[parents[0],memory.u32(parents[0]+0xe8)])

    def test_expected_table_and_free_pointer_mutations_cannot_change_source_execution(self):
        original=next(c for c in self.fixture['cases']if c['label']=='wire/repeated'and c['cache_mode']=='cold');baseline,heap,addresses,memory,layout,produced=compare(original,return_state=True)
        c=copy.deepcopy(original);table=c['filament_context']['arrays']['width_counts'];changed=bytearray.fromhex(table['data']);changed[0]^=1;table['data']=changed.hex()
        report,other_heap,other_addresses,other_memory,other_layout,other=compare(c,return_state=True)
        self.assertEqual([d['kind']for d in report['differences']],['filament-table']);self.assertEqual(other,produced);self.assertEqual(other_addresses,addresses)
        c=copy.deepcopy(original);child=c['filament_context']['geometry']['segments'][0]['children'][0]['address'];event=next(e for e in c['events']if e['kind']=='free'and e['allocator']=='scalar'and e['address']==child);event['address']^=1
        report,other_heap,other_addresses,other_memory,other_layout,other=compare(c,return_state=True)
        self.assertEqual([d['kind']for d in report['differences']],['filament-allocation-owner']);self.assertEqual(other,produced);self.assertEqual(other_heap.tcache,heap.tcache)

    def test_secondary_pointers_require_actual_earlier_geometry_memory(self):
        c=self.fixture['cases'][0];shape,tech=ported_inductance_geometry(c);layout=FilamentLayout(shape,len(tech.metals))
        with self.assertRaisesRegex(ValueError,'earlier source geometry memory'):layout.pointers(None,[0]*len(shape.segments))


if __name__=='__main__':unittest.main()

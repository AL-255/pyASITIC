"""Native pre-free workspace provenance and independent portable vectors."""
import collections,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_workspace_storage_original as capture
import capture_trailing_via_heap_original as lifetime
from audit_workspace_storage_original import compare
from reasitic.allocation_plan import combined_network_storage


class WorkspaceStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/workspace_storage_original.json.gz').read_bytes()))

    def test_all_selected_inputs_array_frees_and_workspace_coverage(self):
        fixture=self.fixture;self.assertEqual(len(fixture['cases']),130)
        self.assertEqual(fixture['original_sha256'],lifetime.ORIGINAL_SHA256);self.assertEqual(fixture['legacy_sha256'],lifetime.LEGACY_SHA256)
        self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
        self.assertEqual(fixture['workspace_storage_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/cap_prelude_original.json.gz').read_bytes()).hexdigest())
        for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        arrays=total=workspaces=0
        for i,job in enumerate(lifetime.jobs()):
            cold,warm=fixture['cases'][2*i:2*i+2]
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['cache_after_plain'],warm['initial_cache'])
            for case,mode in ((cold,'cold'),(warm,'warm')):
                with self.subTest(label=job['label'],mode=mode):
                    for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                    self.assertEqual(case['cache_mode'],mode);self.assertEqual((case['pending'],case['prefix_pending'],case['prefix_interfaces']),(0,0,0))
                    for name,value in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                        self.assertEqual(case['initial_files'][name],dict(size=len(value.encode()),sha256=hashlib.sha256(value.encode()).hexdigest()))
                    captured={r['event_index']:r for r in case['workspace_storage']}
                    for index,r in captured.items():
                        event=case['events'][index];self.assertEqual((event['kind'],event['address']),('free',r['address']))
                        self.assertLessEqual(r['size'],16384);self.assertEqual(len(bytes.fromhex(r['data'])),r['size']);arrays+=1;total+=r['size']
                    plan=iter(combined_network_storage([len(g['contacts'])for g in case['contact_groups']],case['via']['matrix']['size'],case['matrices']['ind_full']['size'],len(case['via']['indices']),clone_segments=len(case['via']['segments'])))
                    for index,event in enumerate(case['events']):
                        if event['kind']not in ('allocate','free'):continue
                        expected=next(plan)
                        if event['kind']=='free'and expected.name.endswith(('.work','.inverse_work','.pivots')):
                            self.assertIn(index,captured);workspaces+=1
        self.assertEqual((arrays,total,workspaces),(2735,1815488,1427))
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in fixture['cases']),{0:126,-6:3,-11:1})

    def test_portable_first_native_workspace_arrays(self):
        for case in self.fixture['cases'][:2]:
            with self.subTest(mode=case['cache_mode']):
                result=compare(case);self.assertEqual(result['differences'],[])
                self.assertEqual((result['arrays_checked'],result['bytes_checked']),(11,176))

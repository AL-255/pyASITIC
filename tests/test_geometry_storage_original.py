"""Complete native clone/COPY/JOIN records and continuous arena placement."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_geometry_setup_original as capture
import capture_geometry_setup_extended_original as extended
from audit_geometry_setup_original import compare


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class GeometryStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=load('geometry_setup_original.json.gz');cls.extended=load('geometry_setup_extended_original.json.gz')

    def test_all_inputs_observers_and_whole_initial_heap_provenance(self):
        for fixture,jobs,parent in ((self.original,list(capture.arena.lifetime.jobs()),'cap_prelude_original.json.gz'),(self.extended,list(extended.jobs()),'geometry_setup_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs))
            self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            self.assertEqual(fixture['geometry_setup_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            for i,job in enumerate(jobs):
                cold,warm=fixture['cases'][2*i:2*i+2]
                self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain'])
                for case,mode in ((cold,'cold'),(warm,'warm')):
                    with self.subTest(label=job['label'],mode=mode):
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode)
                        self.assertEqual((case['setup_pending'],case['setup_interfaces'],case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0,0,0))
                        context=case['setup_context'];state=case['allocator_states'][0]
                        self.assertEqual((context['control'],case['setup_output']['control']),(0x37f,0x37f))
                        self.assertEqual((state['label'],state['setup_event_count']),('driver_entry',0));self.assertEqual(state['errors'],[])
                        maps=[m for m in state['maps']if m['path']=='[heap]'];regions=context['memory_regions']
                        self.assertEqual([(r['address'],len(r['data'])//2)for r in regions],[(m['start'],m['end']-m['start'])for m in maps])
                        def initial_bytes(address,size):
                            region=next(r for r in regions if r['address']<=address and address+size<=r['address']+len(r['data'])//2)
                            start=2*(address-region['address']);return region['data'][start:start+2*size]
                        self.assertEqual(context['head'],context['scene'][0]['address'])
                        for shape in context['scene']:
                            self.assertEqual(shape['data'],initial_bytes(shape['address'],188))
                            for segment in shape['segments']:
                                self.assertEqual(segment['data'],initial_bytes(segment['address'],240));self.assertEqual(segment['children'],[])
                        for name,value in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                            self.assertEqual(case['initial_files'][name],dict(size=len(value.encode()),sha256=hashlib.sha256(value.encode()).hexdigest()))

    def test_all_original_bytes_requests_frees_and_continuous_cap_entry(self):
        results=[compare(case)for case in self.original['cases']]
        for result in results:
            with self.subTest(label=result['label'],mode=result['cache_mode']):self.assertEqual(result['differences'],[])
        self.assertEqual(sum(r['events_checked']for r in results),2308)
        self.assertEqual(sum(r['allocations_checked']for r in results),2206)
        self.assertEqual(sum(r['geometry_bytes_checked']for r in results),983544)
        self.assertEqual(sum(r['string_bytes_checked']for r in results),83720)
        self.assertEqual(sum(r['prefix']['events']for r in results),7732)
        self.assertEqual(sum(r['prefix']['allocations_checked']for r in results),6302)
        # Plain command-exit faults are preserved separately from the earlier
        # observer boundary. Neither a native crash nor a nonfinite case is dropped.
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.original['cases']),{0:122,-6:7,-11:1})

    def test_longitudinal_typed_copies_coupled_join_and_large_string_storage(self):
        self.assertEqual(len(self.extended['cases']),10)
        for case in self.extended['cases']:
            with self.subTest(label=case['label'],mode=case['cache_mode']):self.assertEqual(compare(case)['differences'],[])
        subdivided=self.extended['cases'][0]
        source=next(s for s in subdivided['setup_context']['scene']if s['address']==subdivided['setup_context']['arguments'][0])
        self.assertGreater(len(subdivided['setup_output']['first']['segments']),len(source['segments']))
        for case in self.extended['cases'][-2:]:
            self.assertTrue(any(e['kind']=='allocate'and e['request']==144 and e['allocator']=='malloc'for e in case['setup_events']))
            name=bytes.fromhex(case['setup_output']['first']['data']).split(b'\0',1)[0]
            self.assertEqual(name,b'L'*63+b'_')

    def test_predicted_geometry_owners_do_not_read_later_via_observations(self):
        case=copy.deepcopy(self.original['cases'][0])
        case['via']['shape_address']=0;case['via']['segment_addresses']=[];case['via']['segments']=[]
        self.assertEqual(compare(case)['differences'],[])

    def test_changed_expected_word_fails_without_repairing_generated_bytes(self):
        case=copy.deepcopy(self.original['cases'][0]);shape=case['setup_output']['first']
        native=bytes.fromhex(shape['data']);changed=bytearray(native);changed[0x54]^=1;shape['data']=changed.hex()
        result,heap,addresses,memory=compare(case,return_state=True)
        self.assertTrue(any(d['kind']=='memory'and d['offset']==0x54 for d in result['differences']))
        self.assertEqual(memory.read(addresses['geometry.descriptor'],188),native)


if __name__=='__main__':unittest.main()

"""Full native secondary records, continuous allocation and pointer phases."""
import copy,gzip,hashlib,json,math,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_geometry_setup_original as setup
import capture_shunt_geometry_storage_original as capture_setup
import capture_shunt_dispatch_original as capture_dispatch
from audit_geometry_setup_original import compare as geometry_compare
from audit_shunt_dispatch_original import compare as dispatch_compare,run as dispatch_run


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class ShuntGeometryStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=load('shunt_geometry_storage_original.json.gz');cls.dispatch=load('shunt_dispatch_original.json.gz')

    def test_native_setup_inputs_all_outcomes_and_complete_initial_group_records(self):
        f=self.fixture;jobs=list(capture_setup.jobs());self.assertEqual(len(jobs),14);self.assertEqual(len(f['cases']),28)
        self.assertEqual(f['allocator_provenance']['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        directory=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],setup.commands(directory));self.assertEqual(f['allocator_provenance']['observer'],setup.OBSERVER)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        parent=ROOT/'tests/fixtures/shunt_sessions_original.json.gz';self.assertEqual(f['geometry_setup_parent_sha256'],hashlib.sha256(parent.read_bytes()).hexdigest())
        children=0
        for case,job in zip(f['cases'],(job for job in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
            self.assertEqual(case['plain']['returncode'],0);self.assertEqual(case['signal'],0)
            self.assertEqual((case['setup_pending'],case['setup_interfaces'],case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0,0,0))
            context=case['setup_context'];self.assertEqual((context['control'],case['setup_output']['control']),(0x37f,0x37f))
            def initial_bytes(address,size):
                r=next(r for r in context['memory_regions']if r['address']<=address and address+size<=r['address']+len(r['data'])//2);offset=2*(address-r['address']);return r['data'][offset:offset+2*size]
            for shape in context['scene']:
                self.assertEqual(shape['data'],initial_bytes(shape['address'],188))
                for segment in shape['segments']:
                    self.assertEqual(segment['data'],initial_bytes(segment['address'],240))
                    for child in segment['children']:self.assertEqual(child['data'],initial_bytes(child['address'],240));children+=1
        self.assertGreater(children,0)

    def test_all_setup_addresses_raw_records_pool_and_continuous_cap_preparation(self):
        results=[geometry_compare(c)for c in self.fixture['cases']]
        for r in results:
            with self.subTest(label=r['label'],mode=r['cache_mode']):self.assertEqual(r['differences'],[])
        # Retain the entire original twelve-session/cold-warm cohort as well
        # as the additional child-governed and typed-one-part clone cases.
        for key,value in(('events_checked',890),('allocations_checked',626),('geometry_bytes_checked',123096),('string_bytes_checked',15456)):self.assertEqual(sum(r[key]for r in results[:24]),value)
        for key,value in(('events_checked',918),('allocations_checked',654),('geometry_bytes_checked',133240),('string_bytes_checked',18032)):self.assertEqual(sum(r[key]for r in results),value)
        self.assertEqual(sum(r['prefix']['events']for r in results),1148);self.assertEqual(sum(r['prefix']['allocations_checked']for r in results),840)
        refined=next(c for c in self.fixture['cases']if c['label']=='unequal-branch/refined'and c['cache_mode']=='cold')
        source=next(s for s in refined['setup_context']['scene']if s['address']==refined['setup_context']['arguments'][0])
        parent=next(s for s in source['segments']if s['children'])
        def length(record):
            values=struct.unpack_from('<6d',bytes.fromhex(record['data']));return math.dist(values[:3],values[3:])
        self.assertEqual(math.ceil(length(parent)/35),2);self.assertEqual(math.ceil(length(parent['children'][0])/35),3)
        self.assertEqual(len(refined['setup_output']['first']['segments']),6)

    def test_changed_later_secondary_bytes_fail_without_repairing_source_memory(self):
        c=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='wire/repeated'and c['cache_mode']=='cold'));child=c['setup_output']['first']['segments'][0]['children'][0];native=bytes.fromhex(child['data']);changed=bytearray(native);changed[0]^=1;child['data']=changed.hex()
        result,heap,addresses,memory=geometry_compare(c,return_state=True)
        self.assertTrue(any(d['kind']=='memory'and d['address']==child['address']and d['offset']==0 for d in result['differences']))
        self.assertEqual(memory.read(child['address'],240),native)

    def test_dispatch_scripts_initial_context_and_all_plain_outcomes(self):
        f=self.dispatch;jobs=list(capture_dispatch.jobs());self.assertEqual(len(f['cases']),19);self.assertEqual(len(jobs),19);self.assertEqual(f['observer'],capture_dispatch.OBSERVER)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['legacy_sha256'],'bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34')
        self.assertEqual(f['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,job in zip(f['cases'],jobs):
            for key in('label','commands','prefix','stdin','technology'):self.assertEqual(c[key],job[key])
            self.assertEqual(c['script'],c['prefix']+''.join('JOINSHUNT '+' '.join(names)+'\n'for names in c['commands']))
            directory=Path(c['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(c['gdb_commands'],capture_dispatch.commands(directory,len(c['commands'])))
            self.assertEqual((c['plain']['returncode'],c['signal'],c['pending'],c['interfaces']),(0,0,0,0));self.assertEqual(len(c['outputs']),len(c['commands']))
            self.assertEqual(c['allocator_states'][0]['label'],'command_entry');self.assertEqual(len(c['allocator_states']),len(c['commands'])+1)
            for output in[c['context'],*c['outputs']]:
                self.assertEqual(output['control'],0x37f);self.assertLessEqual(set(output['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(output['environment'][key],value)
        selected=next(c for c in f['cases']if c['label']=='selected-later');self.assertNotEqual(selected['context']['selected'],0)
        self.assertEqual(selected['outputs'][0]['selected'],selected['context']['selected']);self.assertNotEqual(selected['outputs'][1]['selected'],selected['context']['selected'])

    def test_consecutive_dispatch_words_addresses_phases_and_physical_allocator_states(self):
        report=dispatch_run(self.dispatch);self.assertEqual(report['differences'],0,json.dumps(report,indent=2))
        for key,value in(('commands_checked',33),('events_checked',494),('allocations_checked',229),('geometry_bytes_checked',187084),('phase_words_checked',53),('allocator_boundaries_checked',33)):self.assertEqual(report[key],value)

    def test_later_argument_and_phase_observations_never_seed_the_continuing_heap(self):
        c=copy.deepcopy(next(c for c in self.dispatch['cases']if c['label']=='selected-later'));c['command_inputs'][1]['arguments'][1]^=1
        result,geometry,heap,memory=dispatch_compare(c,return_state=True);self.assertEqual([d['kind']for d in result['differences']],['shunt-dispatch-arguments'])
        self.assertEqual(geometry.selected,c['outputs'][-1]['selected'])
        c=copy.deepcopy(next(c for c in self.dispatch['cases']if c['label']=='negative-batch'));shape=c['outputs'][0]['shapes'][0];native=bytes.fromhex(shape['data']);changed=bytearray(native);changed[0xac]^=1;shape['data']=changed.hex()
        result,geometry,heap,memory=dispatch_compare(c,return_state=True)
        self.assertEqual({d['kind']for d in result['differences']},{'shunt-dispatch-word','shunt-dispatch-phase'})
        self.assertEqual(memory.read(shape['address'],188),native)
        initial_source=next(s['address']for s in c['context']['shapes']if bytes.fromhex(s['data']).split(b'\0',1)[0]==b'XS1')
        self.assertEqual(memory.u32(shape['address']+0xac),initial_source)


if __name__=='__main__':unittest.main()

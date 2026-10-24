"""All native CAP buffer provenance and small portable buffer/store checks."""
import collections,copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_cap_storage_original as capture
import capture_trailing_via_heap_original as lifetime
from audit_cap_storage_original import compare,ported_buffers
from reasitic.heap import AddressSpace
from reasitic.memory import Memory,ComplexView


class CapStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/cap_storage_original.json.gz').read_bytes()))

    def test_all_selected_native_buffers_inputs_and_observer_provenance(self):
        fixture=self.fixture;self.assertEqual(len(fixture['cases']),130)
        self.assertEqual(fixture['original_sha256'],lifetime.ORIGINAL_SHA256);self.assertEqual(fixture['legacy_sha256'],lifetime.LEGACY_SHA256)
        self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
        directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
        self.assertEqual(fixture['cap_storage_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/cap_prelude_original.json.gz').read_bytes()).hexdigest())
        for parent,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest(),digest)
        words=matrices=0
        for i,job in enumerate(lifetime.jobs()):
            cold,warm=fixture['cases'][2*i:2*i+2]
            self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['initial_cache'],warm['cache_after_plain'])
            for case,mode in ((cold,'cold'),(warm,'warm')):
                with self.subTest(label=job['label'],mode=mode):
                    for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                    self.assertEqual(case['cache_mode'],mode);self.assertEqual((case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0));self.assertEqual(case['events'][0]['control'],0x37f)
                    for filename,value in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                        self.assertEqual(case['initial_files'][filename],dict(size=len(value.encode()),sha256=hashlib.sha256(value.encode()).hexdigest()))
                    self.assertEqual(tuple(case['cap_storage']),('cap_full','cap_reduced','cap_folded','cap_output'))
                    for name,matrix in case['cap_storage'].items():
                        matrices+=1;n=matrix['size'];self.assertEqual(matrix['stride'],n)
                        raw=bytes.fromhex(matrix['data_bytes']);self.assertEqual(len(raw),16*n*n);words+=len(raw)//8
                        for key in ('data','size','stride','descriptor'):self.assertEqual(matrix[key],case['matrices'][name][key])
        self.assertEqual((matrices,words),(520,841328))
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in fixture['cases']),{0:125,-6:4,-11:1})
        self.assertEqual([(c['label'],c['cache_mode'],c['signal'])for c in fixture['cases']if c['signal']],[('square/64/contacts','cold',11)])

    def test_portable_first_native_history_and_immutable_buffer_observations(self):
        # The mandatory packaged audit checks all 130 cases, including complete
        # 192-contact inverse buffers. This keeps an independent portable case.
        for case in self.fixture['cases'][:2]:
            with self.subTest(mode=case['cache_mode']):
                buffers=ported_buffers(case);self.assertEqual(tuple(buffers),('cap.full','cap.reduced','cap.folded','cap.output'))
                for matrix in buffers.values():
                    self.assertIsInstance(matrix,tuple);self.assertTrue(all(isinstance(row,tuple)for row in matrix))
                    with self.assertRaises(TypeError):matrix[0][0]=0j
                result=compare(case);self.assertEqual(result['differences'],[])
                self.assertEqual((result['matrices_checked'],result['words_checked'],result['allocations_checked'],result['events_checked']),(4,8,6,8))

    def test_changed_original_word_fails_without_changing_source_matrices(self):
        case=copy.deepcopy(self.fixture['cases'][0]);buffers=ported_buffers(case)
        matrix=case['cap_storage']['cap_full'];raw=bytearray.fromhex(matrix['data_bytes']);raw[0]^=1;matrix['data_bytes']=raw.hex()
        self.assertEqual(ported_buffers(case),buffers)
        self.assertEqual([d['kind']for d in compare(case)['differences']],['word'])

    def test_complete_matrix_stores_preserve_stride_padding_and_aliases(self):
        memory=Memory(AddressSpace([dict(start=0x1000,end=0x1060)]));memory.write(0x1000,b'\xa5'*96)
        matrix=((1+2j,complex(-0.,-0.)),(3+4j,5+6j));view=ComplexView(memory,0x1000,2,3);view.write(matrix)
        for i in range(2):
            for j in range(2):self.assertEqual(memory.read(view.cell_address(i,j),16),struct.pack('<2d',matrix[i][j].real,matrix[i][j].imag))
        self.assertEqual(memory.read(0x1020,16),b'\xa5'*16);self.assertEqual(memory.read(0x1050,16),b'\xa5'*16)
        alias=ComplexView(memory,0x1030,1);self.assertEqual(struct.pack('<2d',alias.get(0,0).real,alias.get(0,0).imag),struct.pack('<2d',-0.,-0.))
        before=memory.read(0x1000,96)
        with self.assertRaisesRegex(ValueError,'dimensions'):view.write(((1j,),))
        self.assertEqual(memory.read(0x1000,96),before)

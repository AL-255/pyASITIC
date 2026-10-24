"""Native complete pre-CAP freed storage, input provenance and strict failures."""
import copy,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_libio_storage_original as capture
import capture_prelude_storage_extended_original as extended
from project_prelude_storage_original import expand_case
from audit_libio_storage_original import compare
from reasitic.memory import Memory


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class LibioStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('libio_storage_original.json.gz');cls.extended=load('libio_storage_extended_original.json.gz')

    def test_all_inputs_linker_binding_layout_and_external_header_provenance(self):
        for fixture,jobs,parent in ((self.fixture,list(capture.prelude.geometry.arena.lifetime.jobs()),'prelude_storage_original.json.gz'),(self.extended,list(extended.jobs()),'prelude_storage_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['libio_storage_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            for i,job in enumerate(jobs):
                cold,warm=fixture['cases'][2*i:2*i+2]
                self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain'])
                for case,mode in ((cold,'cold'),(warm,'warm')):
                    with self.subTest(label=job['label'],mode=mode):
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode);inputs=case['libio_inputs']
                        self.assertNotEqual(inputs['list_head'],inputs['unqualified_list_head'])
                        for name,item in inputs['libc_symbols'].items():self.assertEqual(item['address'],inputs['libc_base']+item['offset'])
                        self.assertEqual(inputs['file_jumps'],inputs['libc_symbols']['_IO_file_jumps']['address'])
                        self.assertEqual(inputs['wide_jumps'],inputs['libc_symbols']['_IO_wfile_jumps']['address'])
                        self.assertEqual((inputs['file']['size'],inputs['plus']['size'],inputs['wide']['size'],inputs['lock_size']),(148,152,140,12))
                        self.assertEqual(inputs['file']['fields']['_mode'],dict(offset=104,size=4))
                        self.assertEqual(inputs['file']['fields']['_offset'],dict(offset=76,size=8))
                        self.assertEqual(len(inputs['cache_files']),int(mode=='warm'))
                        for record in inputs['cache_files']:
                            self.assertEqual({k:record[k]for k in('size','sha256')},case['initial_cache'][record['name']])
                            header=bytes.fromhex(record['header']);self.assertEqual(len(header),16+40*inputs['substrate_count']+236*inputs['metal_count'])
                            self.assertEqual(struct.unpack_from('<2i',header),(int(job['request']['technology'].split('fftx = ')[1].split()[0]),int(job['request']['technology'].split('ffty = ')[1].split()[0])))
                        for filename,text in (('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',fixture['gdb_commands'])):
                            self.assertEqual(case['initial_files'][filename],dict(size=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest()))

    def test_both_earlier_symbol_resolution_experiments_are_retained(self):
        for name,count in (('libio_binding_ambiguous_original.json.gz',130),('libio_binding_pilot_original.json.gz',2)):
            fixture=load(name);self.assertEqual(len(fixture['cases']),count)
            for case in fixture['cases']:
                script=fixture['gdb_commands'].encode();self.assertEqual(case['initial_files']['capture.gdb'],dict(size=len(script),sha256=hashlib.sha256(script).hexdigest()))
                self.assertNotIn('libc_symbols',case['libio_inputs'])
                expanded=expand_case(fixture,case);chain=struct.unpack_from('<I',bytes.fromhex(next(r for r in expanded['prelude_storage']if r['size']==304)['data']),52)[0]
                self.assertNotEqual(case['libio_inputs']['list_head'],chain)

    def test_portable_full_small_freed_bytes_and_retained_rectangular_metadata_failure(self):
        reports=[compare(expand_case(self.extended,c))for c in self.extended['cases']]
        for report in reports:
            self.assertEqual(report['unknown_bytes'],0)
            self.assertFalse(any(d['kind']=='bytes'for d in report['differences']),report['differences'])
        self.assertEqual(sum(r['bytes_checked']for r in reports),32248)
        self.assertEqual(sum(r['file_records_checked']for r in reports),6)
        self.assertEqual(sum(r['header_arrays_checked']for r in reports),4)
        # The strict command still fails on this known original cache-table
        # heap corruption. Do not drop or repair the observed damaged walk.
        self.assertEqual([len(r['differences'])for r in reports],[0,0,1,0])
        self.assertEqual(reports[2]['differences'][0]['kind'],'chunk-addresses')
        state=next(s for s in self.extended['cases'][2]['allocator_states']if s['label']=='scope')
        self.assertTrue(any(e['section']=='chunks'for e in state['errors']))

    def test_wrong_symbol_input_is_not_repaired_from_expected_file_chain(self):
        case=expand_case(self.extended,self.extended['cases'][0]);inputs=dict(case['libio_inputs'])
        inputs['list_head']=inputs['unqualified_list_head'];case['libio_inputs']=inputs
        report=compare(case)
        self.assertEqual([(d['kind'],d.get('offset'))for d in report['differences']],[('bytes',52),('bytes',52)])

    def test_cache_header_padding_comes_from_input_file_not_current_technology(self):
        case=expand_case(self.extended,self.extended['cases'][1]);case=copy.deepcopy(case)
        header=bytearray.fromhex(case['libio_inputs']['cache_files'][0]['header'])
        offset=16+40*case['libio_inputs']['substrate_count']+12;header[offset]^=1
        case['libio_inputs']['cache_files'][0]['header']=header.hex();case['prelude_final_heap']=None
        report=compare(case);differences=report['differences'];self.assertEqual(len(differences),1)
        self.assertEqual((differences[0]['name'],differences[0]['offset']),('cache.header.metals',12))

    def test_header_trace_keeps_actual_stale_footer_and_requires_one_memory(self):
        case=expand_case(self.fixture,self.fixture['cases'][-2])
        # Use the prior geometry input and genuine free/coalesce sequence;
        # the surviving word later becomes FILE's unused wide short buffer.
        from audit_geometry_setup_original import compare as geometry
        initial,heap,addresses,memory=geometry(case,return_state=True,include_prelude=False,observe_headers=True)
        self.assertEqual(initial['differences'],[])
        with self.assertRaises(ValueError):heap.attach_cache_memory(Memory(heap.address_space),0)
        with self.assertRaises(ValueError):heap.observe_header_stores(memory)
        from reasitic.allocation_plan import capacitance_prelude_storage
        from audit_cap_prelude_original import dimensions
        counts,metals,substrates,nx=dimensions(case)
        for event in capacitance_prelude_storage(counts,metals,substrates,nx,cache_mode='cold'):
            self.assertEqual(event.action,'allocate');address=heap.malloc(event.size)
            if event.name=='cache.reader.file':break
        original=next(r for r in case['prelude_storage']if r['size']==304)
        self.assertEqual(address,original['address'])
        self.assertEqual(memory.read(address+296,4),bytes.fromhex(original['data'])[296:300])


if __name__=='__main__':unittest.main()

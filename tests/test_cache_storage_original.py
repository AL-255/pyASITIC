"""Complete native cache histories, shared overflow stores and negative controls."""
import copy,collections,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_cache_storage_original as capture
import capture_cache_storage_extended_original as extended
import audit_cache_storage_original as audit
from project_prelude_storage_original import expand_case
from audit_allocator_original import header_walk,state_differences
from reasitic import Technology
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.cache_storage import CacheStorage,initial_regions


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


def input_memory(case):
    state=case['allocator_states'][0];memory=Memory(AddressSpace(state['maps']))
    for region in case['setup_context']['memory_regions']:memory.write(region['address'],bytes.fromhex(region['data']))
    for address,data in initial_regions(case['cache_inputs']):memory.write(address,data)
    return memory


class CacheStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('cache_storage_original.json.gz');cls.extended=load('cache_storage_extended_original.json.gz')

    def test_all_histories_earlier_inputs_and_complete_independent_outputs(self):
        for fixture,jobs,parent in ((self.fixture,list(capture.libio.prelude.geometry.arena.lifetime.jobs()),'libio_storage_original.json.gz'),(self.extended,list(extended.jobs()),'libio_storage_extended_original.json.gz')):
            self.assertEqual(len(fixture['cases']),2*len(jobs));self.assertEqual(fixture['allocator_provenance']['observer'],capture.OBSERVER)
            self.assertEqual(fixture['cache_storage_parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures'/parent).read_bytes()).hexdigest())
            directory=fixture['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
            self.assertEqual(fixture['gdb_commands'],capture.commands(Path(directory)))
            for name,digest in fixture['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
            for bank in ('cache_file_pages','storage_pages','storage_blobs'):
                for digest,data in fixture[bank].items():self.assertEqual(hashlib.sha256(bytes.fromhex(data)).hexdigest(),digest)
            for i,job in enumerate(jobs):
                cold,warm=fixture['cases'][2*i:2*i+2]
                self.assertEqual(cold['initial_cache'],{});self.assertEqual(warm['initial_cache'],cold['cache_after_plain'])
                for entry,mode in ((cold,'cold'),(warm,'warm')):
                    with self.subTest(label=job['label'],mode=mode):
                        case=expand_case(fixture,entry)
                        for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
                        self.assertEqual(case['cache_mode'],mode)
                        self.assertEqual((case['setup_pending'],case['setup_interfaces'],case['prefix_pending'],case['prefix_interfaces'],case['pending']),(0,0,0,0,0))
                        files=dict(capture.expand_files(fixture,case))
                        self.assertEqual({name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())for name,data in files.items()},case['initial_cache'])
                        inputs=case['cache_inputs'];memory=input_memory(case);count=inputs['metals']*(inputs['metals']+1)//2
                        self.assertEqual(inputs['nx'],int(Technology.from_text(case['request']['technology']).chip['fftx']))
                        self.assertEqual(inputs['ny'],int(Technology.from_text(case['request']['technology']).chip['ffty']))
                        self.assertEqual(len(inputs['initial_regions']),3*count)
                        for name,group in inputs['arrays'].items():
                            self.assertEqual(len(group['pointers']),count)
                            self.assertEqual([memory.u32(group['pointer_address']+4*k)for k in range(count)],group['pointers'])
                        for region in inputs['initial_regions']:
                            self.assertEqual(hashlib.sha256(memory.read(region['address'],region['size'])).hexdigest(),region['sha256'])
                        self.assertEqual({(r['name'],r['index'])for r in case['cache_outputs']},{(name,k)for name in inputs['arrays']for k in range(count)})
                        for r in case['cache_outputs']:self.assertEqual(r['size'],inputs['arrays'][r['name']]['size'])
                        script=fixture['gdb_commands'].encode();self.assertEqual(case['initial_files']['capture.gdb'],dict(size=len(script),sha256=hashlib.sha256(script).hexdigest()))
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:124,-6:4,-11:2})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.extended['cases']),{0:3,-6:1})

    def test_portable_all_small_tables_buffers_and_damaged_physical_walk(self):
        reports=[audit.compare(self.extended,c)for c in self.extended['cases']]
        for report in reports:self.assertEqual(report['differences'],[])
        self.assertEqual(sum(r['tables_checked']for r in reports),180)
        self.assertEqual(sum(r['table_bytes_checked']for r in reports),150720)
        self.assertEqual(sum(r['bytes_checked']for r in reports),32248)
        self.assertEqual(sum(r['unknown_bytes']for r in reports),0)
        case=self.extended['cases'][2];self.assertEqual(case['plain']['returncode'],-6)
        state=next(s for s in case['allocator_states']if s['label']=='scope')
        self.assertTrue(any(e['section']=='chunks'for e in state['errors']))

    def test_clipping_rectangular_writes_is_detected(self):
        begin=CacheStorage.begin
        def clipped(cache,source,target):
            address=cache.address('xy',cache.index(source,target));end=address+cache.inputs['arrays']['xy']['size'];write=cache.memory.write
            def bounded(position,data):
                count=max(0,min(len(data),end-position))
                if count:write(position,data[:count])
            with patch.object(cache.memory,'write',side_effect=bounded):begin(cache,source,target)
        with patch.object(CacheStorage,'begin',clipped):report=audit.compare(self.extended,self.extended['cases'][2])
        kinds={d['kind']for d in report['differences']}
        # Declared tables alone cannot expose this bug: later generations
        # overwrite them. The damaged physical walk must still be checked.
        self.assertEqual(kinds,{'physical-chunks','physical-header-errors'})

    def test_expected_table_metadata_cannot_seed_actual_owner_or_bytes(self):
        case=copy.deepcopy(self.extended['cases'][0]);original=case['cache_outputs'][0].copy()
        case['cache_outputs'][0].update(address=original['address']+16,sha256='0'*64)
        case['prelude_final_heap']=None
        report,heap,addresses,memory=audit.compare(self.extended,case,return_state=True)
        self.assertEqual([d['kind']for d in report['differences']],['cache-table-owner','cache-table'])
        self.assertEqual(hashlib.sha256(memory.read(original['address'],original['size'])).hexdigest(),original['sha256'])

    def test_changed_earlier_external_bytes_propagate_without_repair(self):
        case=self.extended['cases'][1];files=list(capture.expand_files(self.extended,case));path,data=files[0]
        offset=16+40*len(Technology.from_text(case['request']['technology']).substrate)+236*case['cache_inputs']['metals']
        changed=bytearray(data);changed[offset+64]^=1
        with patch.object(audit,'expand_files',return_value=[(path,bytes(changed))]):
            report,heap,addresses,memory=audit.compare(self.extended,case,return_state=True)
        self.assertTrue(any(d['kind']=='cache-table'and d['name']=='xy'and d['index']==0 for d in report['differences']))
        address=memory.u32(case['cache_inputs']['arrays']['xy']['pointer_address'])
        self.assertEqual(memory.read(address+64,1),bytes(changed[offset+64:offset+65]))
        # Header arrays must consume the same full external file as tables,
        # rather than the separate earlier header-only diagnostic copy.
        changed=bytearray(data);padding=16+40*len(Technology.from_text(case['request']['technology']).substrate)+12;changed[padding]^=1
        with patch.object(audit,'expand_files',return_value=[(path,bytes(changed))]):report=audit.compare(self.extended,case)
        self.assertEqual([(d['kind'],d.get('name'),d.get('offset'))for d in report['differences']],[('bytes','cache.header.metals',12)])

    def test_successful_load_uses_opened_path_not_header_frequency(self):
        case=expand_case(self.extended,self.extended['cases'][1]);path,data=next(capture.expand_files(self.extended,case));changed=bytearray(data)
        struct.pack_into('<d',changed,8,0.251e9)
        technology=Technology.from_text(case['request']['technology']);memory=input_memory(case)
        cache=CacheStorage(memory,case['cache_inputs'],technology,0.25e9,[(path,bytes(changed)),('another-tech_0.25.dat',data)])
        cache.load(path);self.assertEqual(cache.loaded,bytes(changed))
        for record in case['cache_outputs']:
            self.assertEqual(hashlib.sha256(memory.read(record['address'],record['size'])).hexdigest(),record['sha256'])
        with self.assertRaisesRegex(ValueError,'Missing or ambiguous'):cache.load('missing.dat')
        with self.assertRaisesRegex(ValueError,'Truncated'):CacheStorage(memory,case['cache_inputs'],technology,0.25e9,[(path,data[:16])]).load(path)

    def test_every_physical_header_word_and_walk_error_is_compared(self):
        case=self.extended['cases'][2]
        report,heap,addresses,memory=audit.compare(self.extended,case,return_state=True)
        self.assertEqual(report['differences'],[]);state=next(s for s in case['allocator_states']if s['label']=='scope')
        chunks,errors=header_walk(memory,heap.parameters['sbrk_base'],heap.top)
        self.assertEqual(chunks,state['chunks']);self.assertEqual(errors,[e for e in state['errors']if e['section']=='chunks'])
        address=chunks[0]['address'];memory.put_u32(address,memory.u32(address)^1)
        self.assertIn('physical-chunks',{d['kind']for d in state_differences(heap,state,memory=memory)})
        error_address=errors[0]['address'];memory.put_u32(error_address+4,memory.u32(error_address+4)^1)
        self.assertIn('physical-header-errors',{d['kind']for d in state_differences(heap,state,memory=memory)})


if __name__=='__main__':unittest.main()

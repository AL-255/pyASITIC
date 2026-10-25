"""Unchanged original ELF lookup calls and input/output independence."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_loader_lookup_original as capture
from audit_loader_lookup_original import compare,data,memory_for
from reasitic.loader_lookup_storage import LoaderLookup,gnu_hash,elf_hash
from reasitic.memory import Memory
from reasitic.heap import AddressSpace


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class LoaderLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('loader_lookup_original.json.gz')
        cls.case=next(c for c in cls.fixture['cases']if c['lookup_calls'])

    def test_all_134_jobs_provenance_regions_and_environment_guard(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(jobs),67);self.assertEqual(len(f['cases']),134)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        provenance=f['loader_lookup_provenance']
        self.assertEqual(provenance['loader_sha256'],'64f2864e740bf9cc15c01466c438d6ba25c7bc9cf9401d8122287ee7ed05e26d')
        self.assertEqual(provenance['observer'],capture.OBSERVER)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for key,value in f['loader_regions'].items():self.assertEqual(hashlib.sha256(bytes.fromhex(value)).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for case,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
            self.assertEqual(case['lookup_pending'],0)
            for call in case['lookup_calls']:
                a=call['before'];m=memory_for(f,a);s=a['registers']['esp']
                self.assertEqual([m.u32(s+4+4*i)for i in range(8)],call['arguments'])
                self.assertEqual(LoaderLookup(m,a['loader_base'])._string(call['arguments'][0]).decode(),call['name'])
                self.assertLessEqual(set(a['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(a['environment'][key],value)
                stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))

    def test_every_native_return_region_register_and_fp_byte_exact(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,total in [('calls_checked',8),('words_checked',1290725),('registers_checked',136),('fp_bytes_checked',19520)]:self.assertEqual(sum(r[key]for r in reports),total)
        self.assertEqual([x['name']for x in self.case['lookup_calls']],['signal','select','_IO_default_uflow','_IO_file_underflow','_IO_file_read','strcat','add_history','kill'])

    def test_absent_calls_and_original_faults_are_not_synthetic_passes(self):
        cases=self.fixture['cases'];self.assertEqual(sum(not c['lookup_calls']for c in cases),133)
        self.assertEqual(collections.Counter(c['signal']for c in cases),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in cases),{0:129,-6:4,-11:1})
        self.assertEqual([(c['label'],c['cache_mode'])for c in cases if c['lookup_calls']],[('prelude/fft/16/8','cold')])
        self.assertEqual([(c['label'],c['cache_mode'])for c in cases if c['signal']==11],[('square/64/contacts','cold')])
        for c in cases:
            if c['signal']:self.assertIsNone(c['next_driver'])
            elif c['lookup_calls']:self.fail('The captured rectangular history must preserve its native abort')

    def test_fresh_original_outcome_changes_are_retained(self):
        parent=load('signal_install_original.json.gz');pairs=list(zip(parent['cases'],self.fixture['cases']))
        plain=[(a['label'],a['cache_mode'],a['plain']['returncode'],b['plain']['returncode'])for a,b in pairs if a['plain']['returncode']!=b['plain']['returncode']]
        stopped=[(a['label'],a['cache_mode'],a['signal'],b['signal'])for a,b in pairs if a['signal']!=b['signal']]
        self.assertEqual(plain,[('pilot-width3/1/coarse','cold',0,-6),('pilot-width3/1/contacts','cold',0,-6),('pilot-width3/1/contacts','warm',-6,0)])
        self.assertEqual(stopped,[('square/1/coarse','cold',11,0),('pilot-width3/1/contacts','cold',11,0),('pilot-boundary/1/coarse','warm',11,0)])

    def test_link_map_abi_offsets_are_verified_by_native_debug_types(self):
        expected=dict(l_addr=0,l_name=4,l_real=20,l_libname=28,l_info=32,l_versions=384,l_nversions=388,l_nbuckets=392,l_gnu_bitmask_idxbits=396,l_gnu_shift=400,l_gnu_bitmask=404,l_gnu_buckets=408,l_gnu_chain_zero=412,l_versyms=452,l_used=536)
        for call in self.case['lookup_calls']:
            layout=call['link_map_layout'];self.assertEqual(layout['size'],632)
            for name,offset in expected.items():self.assertEqual(layout['fields'][name]['offset'],offset)
            for name,offset,bit,bits in [('l_type',420,0,2),('l_removed',422,2,1),('l_ld_readonly',422,5,1)]:
                field=layout['fields'][name];self.assertEqual((field['offset'],field['bit'],field['bits']),(offset,bit,bits))

    def test_later_memory_register_and_fp_outputs_are_assertions_only(self):
        f=copy.deepcopy(self.fixture);case=copy.deepcopy(self.case);case['lookup_calls']=case['lookup_calls'][:1]
        a,b=case['lookup_calls'][0]['before'],case['lookup_calls'][0]['after'];s=a['registers']['esp']
        stack=next(r for r in b['regions']if r['address']<=s<r['address']+r['size']);raw=bytearray(data(f,stack));raw[s-4-stack['address']]^=1
        key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();stack['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,case)['differences']),{'loader-lookup-memory-word':1,'loader-lookup-register':1,'loader-lookup-fp-byte':1})
        b['regions'].pop();self.assertIn('loader-lookup-region-owners',[d['kind']for d in compare(f,case)['differences']])

    def test_lookup_reads_earlier_hash_chain_and_versions(self):
        call=self.case['lookup_calls'][0];a=call['before'];m=memory_for(self.fixture,a);engine=LoaderLookup(m,a['loader_base'])
        result=engine.lookup(a['registers']);provider=result['provider'];symbol=result['symbol']
        # Remove the selected GNU hash hit from earlier metadata. No later
        # expected symbol or function-name dispatch can repair that input.
        m=memory_for(self.fixture,a);index=(symbol-engine._dynamic(provider,6))//16;chain=(m.u32(provider+412)+4*index)&0xffffffff
        m.put_u32(chain,m.u32(chain)^2)
        with self.assertRaisesRegex(NotImplementedError,'Unresolved ELF symbol'):LoaderLookup(m,a['loader_base']).lookup(a['registers'])
        # A requested hidden version cannot bind to an arbitrary same-name
        # symbol. The original version record is an earlier input, too.
        m=memory_for(self.fixture,a);version=call['arguments'][4];m.put_u32(version+4,m.u32(version+4)^1);m.put_u32(version+8,1)
        with self.assertRaisesRegex(NotImplementedError,'Unresolved ELF symbol'):LoaderLookup(m,a['loader_base']).lookup(a['registers'])

    def test_retained_padding_and_caller_registers_come_from_entry(self):
        call=self.case['lookup_calls'][0];a=call['before'];m=memory_for(self.fixture,a);s=a['registers']['esp'];registers=dict(a['registers'])
        # An untouched local word remains unknown to the algorithm rather
        # than being copied from a later native return snapshot.
        m.put_u32(s-108+20,0x12345678);registers.update(ebx=0x11223344,ebp=0xaabbccdd)
        result=LoaderLookup(m,a['loader_base']).lookup(registers)
        self.assertEqual(m.u32(s-108+20),0x12345678)
        self.assertEqual(m.u32(s-4),0xaabbccdd);self.assertEqual(m.u32(s-16),0x11223344)
        self.assertEqual(result['registers']['ebp'],0xaabbccdd);self.assertEqual(result['registers']['ebx'],0x11223344)

    def test_native_hashes_and_debug_output_boundary(self):
        self.assertEqual(gnu_hash(b''),5381);self.assertEqual(gnu_hash(b'printf'),0x156b2bb8)
        self.assertEqual(elf_hash(b''),0);self.assertEqual(elf_hash(b'printf'),0x077905a6)
        a=self.case['lookup_calls'][0]['before'];m=memory_for(self.fixture,a);engine=LoaderLookup(m,a['loader_base']);m.put_u32(engine.got-0x488,8)
        s=a['registers']['esp'];prior=m.read(s-500,500)
        with self.assertRaisesRegex(NotImplementedError,'debug output'):engine.lookup(a['registers'])
        self.assertEqual(m.read(s-500,500),prior)

    def test_byte_strcmp_does_not_read_past_first_difference(self):
        m=Memory(AddressSpace([dict(start=100,end=101),dict(start=200,end=201),dict(start=1000,end=1020)]))
        m.write(100,b'a');m.write(200,b'b');m.zero(1000,20)
        self.assertEqual(LoaderLookup(m,0)._strcmp(1020,100,200,0x9b88),-1)
        self.assertEqual(m.u32(1000),0x9b88)


if __name__=='__main__':unittest.main()

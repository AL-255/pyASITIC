"""Complete native kill/VDSO boundaries and source input independence."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_kill_storage_original as capture
from audit_kill_storage_original import compare,run
from audit_loader_lookup_original import data,memory_for
from reasitic.kill_storage import kill_vdso_entry,vdso_kernel_entry


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class KillStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('kill_storage_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['dispatch_calls']);cls.call=cls.case['dispatch_calls'][0]

    def test_all_jobs_native_outcomes_provenance_and_full_owners(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['kill_storage_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1});self.assertEqual(sum(not c['dispatch_calls']for c in f['cases']),133)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['dispatch_calls']:
                self.assertEqual(set(call),{'entry','history','parse','parsed','kill','kill_vdso','kill_kernel'})
                owners=[(r['address'],r['size'])for r in call['entry']['regions']]
                for point in call.values():
                    self.assertEqual([(r['address'],r['size'])for r in point['regions']],owners)
                    for r in point['regions']:self.assertEqual(len(data(f,r)),r['size'])

    def test_every_native_memory_gp_fp_and_prior_dispatch_target(self):
        r=run(self.fixture);self.assertEqual(r['cases'],134);self.assertEqual(r['cases_without_dispatch'],133)
        for key,value in(('operations_checked',5),('words_checked',833045),('registers_checked',85),('fp_bytes_checked',12200),('differences',0)):self.assertEqual(r[key],value)

    def engine(self,phase='kill'):
        a=self.call[phase];m=memory_for(self.fixture,a);context=self.call['entry'];base=m.u32(next(x['address']for x in context['maps']if x['name'].endswith('/libc.so.6')))
        return m,a['registers'],dict(libc_base=base,tls_base=context['tls_base'])

    def test_whole_kill_prefix_uses_one_memory_without_inner_state_reset(self):
        m,r,kwargs=self.engine();r=kill_vdso_entry(m,r,**kwargs);self.assertEqual(r,self.call['kill_vdso']['registers'])
        r=vdso_kernel_entry(m,r);self.assertEqual(r,self.call['kill_kernel']['registers'])
        for region in self.call['kill_kernel']['regions']:self.assertEqual(m.read(region['address'],region['size']),data(self.fixture,region))

    def test_earlier_arguments_sysinfo_and_registers_supply_all_saves(self):
        m,r,kwargs=self.engine();r=dict(r,ebx=0xaabbccdd,ebp=0x11223344);s=r['esp'];m.put_u32(s+4,0x12345678);m.put_u32(s+8,65)
        a=kill_vdso_entry(m,r,**kwargs);self.assertEqual((a['eax'],a['ebx'],a['ecx'],a['edx']),(37,0x12345678,65,0xaabbccdd));self.assertEqual(a['eip'],m.u32(kwargs['tls_base']+16))
        b=vdso_kernel_entry(m,a);self.assertEqual([m.u32(s-i)for i in(4,8,12,16)],[kwargs['libc_base']+0x3c3a6,65,0xaabbccdd,0x11223344]);self.assertEqual(b['eflags'],r['eflags']);self.assertEqual(b['ebp'],65)
        # The other supported earlier ABI uses MOV EBP,ESP, not MOV EBP,ECX.
        m.write(a['eip'],bytes.fromhex('51525589e50f34cd805d5a59c3'));b=vdso_kernel_entry(m,a)
        self.assertEqual(b['ebp'],a['esp']-12);self.assertEqual(b['eip'],a['eip']+5);self.assertEqual(m.u32(b['esp']),0x11223344)

    def test_later_memory_gp_and_fp_are_assertions_only(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);end=c['dispatch_calls'][0]['kill_kernel'];address=end['registers']['esp'];region=next(r for r in end['regions']if r['address']<=address<r['address']+r['size'])
        raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region['sha256']=key
        end['registers']['eax']^=1;raw=bytearray.fromhex(end['xstate']);raw[0]^=1;end['xstate']=raw.hex()
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'dispatch-memory-word':1,'dispatch-register':1,'dispatch-fp-byte':1})

    def test_missing_earlier_vdso_has_no_later_copy_fallback(self):
        c=copy.deepcopy(self.case);a=c['dispatch_calls'][0]['kill_vdso'];pc=a['registers']['eip'];a['regions']=[r for r in a['regions']if not(r['address']<=pc and pc+12<=r['address']+r['size'])]
        self.assertTrue(any(d['kind']=='dispatch-runtime'and d['phase']=='vdso'for d in compare(self.fixture,c)['differences']))

    def test_unknown_earlier_abi_fails_before_saving_registers(self):
        m,r,_=self.engine('kill_vdso');before=m.read(r['esp']-12,12);m.write(r['eip'],b'?'*12)
        with self.assertRaisesRegex(NotImplementedError,'earlier instruction ABI'):vdso_kernel_entry(m,r)
        self.assertEqual(m.read(r['esp']-12,12),before)

    def test_continuing_calls_use_produced_registers_and_the_same_memory(self):
        import reasitic.command_transition as transition
        from audit_command_transition_original import compare as continuing
        f=load('printf_transition_original.json.gz');c=next(c for c in f['cases']if(c['label'],c['cache_mode'])==(self.case['label'],self.case['cache_mode']));seen=[]
        def wrap(function):
            def call(memory,registers,**kwargs):
                result=function(memory,registers,**kwargs);seen.append((memory,dict(registers),dict(result)));return result
            return call
        with patch.object(transition,'kill_vdso_entry',wrap(kill_vdso_entry)),patch.object(transition,'vdso_kernel_entry',wrap(vdso_kernel_entry)):report,_,_,memory=continuing(f,c,return_state=True)
        self.assertEqual(len(seen),2);self.assertTrue(all(item[0]is memory for item in seen));self.assertEqual(seen[0][2],seen[1][1])
        for actual,phase in((seen[0][1],'kill'),(seen[0][2],'kill_vdso'),(seen[1][2],'kill_kernel')):self.assertEqual(actual,self.call[phase]['registers'])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences'],'Signal FP and handler continuation remain required')


if __name__=='__main__':unittest.main()

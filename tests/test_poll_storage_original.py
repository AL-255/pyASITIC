"""Full original polling boundaries and independence from later assertions."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_poll_storage_original as capture
from audit_poll_storage_original import compare
from audit_loader_lookup_original import data,memory_for
from reasitic.poll_storage import poll_select,select64_entry
from reasitic.plt_fixup_storage import PltFixup


class PollStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/poll_storage_original.json.gz').read_bytes()))
        cls.case=next(c for c in cls.fixture['cases']if c['poll_calls'])

    def test_all_original_jobs_boundaries_metadata_and_safe_environments(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['poll_storage_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(p['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['poll_calls']:
                self.assertEqual(set(call),{'entry','select','select64'});a=call['entry'];self.assertLessEqual(set(a['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(a['environment'][key],value)
                s=a['registers']['esp'];stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
                for point in call.values():
                    for r in point['regions']:data(f,r)

    def test_complete_native_memory_register_and_fp_outputs(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        self.assertEqual(sum(r['operations_checked']for r in reports),2)
        self.assertEqual(sum(r['registers_checked']for r in reports),34)
        self.assertEqual(sum(r['fp_bytes_checked']for r in reports),4880)
        self.assertEqual(sum(r['words_checked']for r in reports),333210)

    def test_later_outputs_and_region_omissions_fail_independently(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);b=c['poll_calls'][0]['select64'];s=b['registers']['esp']
        r=next(r for r in b['regions']if r['address']<=s<r['address']+r['size'])
        raw=bytearray(data(f,r));raw[s-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'poll-memory-word':1,'poll-register':1,'poll-fp-byte':1})
        b['regions'].pop();self.assertIn('poll-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_native_terminal_outcomes_and_absent_polling_are_preserved(self):
        cases=self.fixture['cases'];self.assertEqual(sum(not c['poll_calls']for c in cases),133)
        self.assertEqual(collections.Counter(c['signal']for c in cases),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in cases),{0:129,-11:1,-6:4})
        self.assertEqual([(c['label'],c['cache_mode'])for c in cases if c['poll_calls']],[('prelude/fft/16/8','cold')])

    def test_poll_saved_registers_padding_and_caller_flags_follow_earlier_state(self):
        a=self.case['poll_calls'][0]['entry'];m=memory_for(self.fixture,a);registers=dict(a['registers'],edi=0x11223344,ebx=0xaabbccdd,edx=0x55667788)
        f=registers['esp']-4;m.write(f-140,b'KEEP')
        result=poll_select(m,registers,PltFixup(m,a['loader_base'],tls_base=a['tls_base']),a)
        self.assertEqual(m.u32(f-144),0x11223344);self.assertEqual(m.u32(f-148),0xaabbccdd)
        self.assertEqual(m.read(f-140,4),b'KEEP');self.assertEqual(result['edx'],0x55667788)
        self.assertEqual(m.read(f-128,128),b'\1'+b'\0'*127)

    def test_timeval_and_guard_come_from_earlier_memory(self):
        call=self.case['poll_calls'][0];context=call['entry'];a=call['select'];m=memory_for(self.fixture,a);registers=a['registers'];s=registers['esp'];timeout=m.u32(s+20)
        base=m.u32(next(x['address']for x in context['maps']if x['name'].endswith('/libc.so.6')))
        m.put_u32(context['tls_base']+20,0x12345600);m.put_u32(timeout,0xfffffffe);m.put_u32(timeout+4,0x80000000)
        # The temporary microsecond slot is written; adjacent padding is not.
        m.write(s-76+16,b'KEEP')
        kwargs=dict(libc_base=base,tls_base=context['tls_base'],sar31_af=self.fixture['integer_cpu']['sar31_af'])
        result=select64_entry(m,registers,**kwargs);wide=result['edi']
        self.assertEqual(m.read(wide,16).hex(),'feffffffffffffff00000080ffffffff')
        self.assertEqual(m.u32(s-76+44),0x12345600);self.assertEqual(m.read(s-76+16,4),b'KEEP')
        m.put_u32(s+20,0);before=m.read(s-140,140)
        with self.assertRaisesRegex(NotImplementedError,'Null-timeout'):select64_entry(m,registers,**kwargs)
        self.assertEqual(m.read(s-140,140),before)

    def test_undefined_shift_flag_uses_independent_cpu_profile(self):
        cpu=self.fixture['integer_cpu'];self.assertEqual(cpu['probe'],capture.CPU_PROBE);self.assertEqual(len(cpu['observations']),6)
        self.assertEqual({r['flags_before']&16 for r in cpu['observations']},{0,16})
        self.assertEqual({r['input']for r in cpu['observations']},{100,0x80000000,0x40000000})
        for r in cpu['observations']:
            value=r['input'];shifted=0xffffffff if value&0x80000000 else 0
            self.assertEqual(r['result'],shifted)
            flags=((value>>30)&1)|(4 if (shifted&255).bit_count()%2==0 else 0)|(64 if not shifted else 128)
            self.assertEqual(r['flags_after']&0x8c5,flags)
            self.assertEqual(r['flags_after']&16,cpu['sar31_af'])
        f=copy.deepcopy(self.fixture);f['integer_cpu']['sar31_af']^=16
        differences=compare(f,self.case)['differences']
        self.assertEqual([(d['kind'],d['name'])for d in differences],[('poll-register','eflags')])


if __name__=='__main__':unittest.main()

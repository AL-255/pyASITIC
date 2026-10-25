"""Native signal installation, uninitialized bytes and startup-derived guards."""
import collections,copy,gzip,hashlib,json,re,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_signal_install_original as capture
from audit_signal_install_original import compare
from reasitic.signal_install_storage import startup,bsd_signal,add_flags
from reasitic.heap import AddressSpace
from reasitic.memory import Memory


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


def memory_for(before):
    stack=before['stack'];address=stack['address'];data=bytes.fromhex(stack['data'])
    memory=Memory(AddressSpace([dict(start=address,end=address+len(data))]));memory.write(address,data);return memory


class SignalInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=load('signal_install_original.json.gz')

    def test_all_original_jobs_provenance_and_minimal_environments_retained(self):
        f=self.fixture;provenance=f['signal_install_provenance'];jobs=list(capture.jobs())
        self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(provenance['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        self.assertEqual(provenance['observer'],capture.OBSERVER)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for case,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
            self.assertEqual(case['bsd_pending'],0)
            for call in case['bsd_calls']:
                before=call['before'];self.assertLessEqual(set(before['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(before['environment'][key],value)
                for part in bytes.fromhex(before['stack']['data']).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
                memory=memory_for(before);sig=memory.u32(before['registers']['esp']+4);bit=1<<(sig-1)
                self.assertFalse(before['dispositions']['caught']&bit)
                self.assertEqual(before['old_action'],dict(handler=int(bool(before['dispositions']['ignored']&bit)),flags=0,restorer=0,mask=0))

    def test_every_complete_native_call_stack_register_and_fp_byte_exact(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,total in [('calls_checked',390),('stack_words_checked',13178880),('registers_checked',6630),('fp_bytes_checked',951600)]:self.assertEqual(sum(r[key]for r in reports),total)

    def test_all_native_faults_and_absent_call_histories_remain_explicit(self):
        cases=self.fixture['cases'];self.assertEqual(collections.Counter(c['signal']for c in cases),{0:129,11:4,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in cases),{0:130,-6:3,-11:1})
        self.assertEqual([(c['label'],c['cache_mode'],c['signal'])for c in cases if not c['bsd_calls']],[('square/1/coarse','cold',11),('square/64/contacts','cold',11),('pilot-width3/1/contacts','cold',11),('pilot-boundary/1/coarse','warm',11)])
        for c in cases:self.assertEqual(c['native_exit'],0 if c['signal']==0 else None)
        for c in cases:
            if c['bsd_calls']:
                self.assertEqual([memory_for(x['before']).u32(x['before']['registers']['esp']+4)for x in c['bsd_calls']],[2,6,3])

    def test_startup_guard_uses_auxv_entropy_and_clears_only_low_byte(self):
        before=next(c['bsd_calls'][0]['before']for c in self.fixture['cases']if c['bsd_calls']);m=memory_for(before)
        boot=startup(m,before['main_frame']);pointer=boot['auxv'][25]
        self.assertEqual(boot['guard'],m.u32(pointer)&0xffffff00)
        m.put_u32(pointer,0xa1b2c3d4);self.assertEqual(startup(m,before['main_frame'])['guard'],0xa1b2c300)
        m.put_u32(before['main_frame']+8,4097)
        with self.assertRaisesRegex(ValueError,'argc'):startup(m,before['main_frame'])

    def test_fresh_native_changes_from_parent_are_preserved(self):
        old=load('signal_frames_original.json.gz');new=self.fixture
        plain=[(a['label'],a['cache_mode'],a['plain']['returncode'],b['plain']['returncode'])for a,b in zip(old['cases'],new['cases'])if a['plain']['returncode']!=b['plain']['returncode']]
        stopped=[(a['label'],a['cache_mode'],a['signal'],b['signal'])for a,b in zip(old['cases'],new['cases'])if a['signal']!=b['signal']]
        self.assertEqual(plain,[('pilot-boundary/1/coarse','warm',-6,0)])
        self.assertEqual(stopped,[('square/1/coarse','cold',0,11),('pilot-width3/1/contacts','warm',11,0)])

    def test_later_return_observations_are_assertions_only(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['bsd_calls']));a,b=case['bsd_calls'][0]['before'],case['bsd_calls'][0]['after']
        stack=b['stack'];raw=bytearray.fromhex(stack['data']);offset=a['registers']['esp']-16-stack['address'];raw[offset]^=1;stack['data']=raw.hex()
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(self.fixture,case)['differences']),{'signal-install-stack-word':1,'signal-install-register':1,'signal-install-fp-byte':1})

    def test_uninitialized_high_mask_words_copy_in_both_directions(self):
        for mode in ('new','old'):
            case=copy.deepcopy(next(c for c in self.fixture['cases']if c['bsd_calls']));a,b=case['bsd_calls'][0]['before'],case['bsd_calls'][0]['after'];s=a['registers']['esp'];local=s-300;k=local-352
            source,destination=(local+24,k+48)if mode=='new'else(k+180,local+156)
            for phase,addresses in ((a,(source,)),(b,(source,destination))):
                stack=phase['stack'];raw=bytearray.fromhex(stack['data'])
                for address in addresses:
                    offset=address-stack['address'];raw[offset:offset+4]=b'WXYZ'
                stack['data']=raw.hex()
            self.assertEqual(compare(self.fixture,case)['differences'],[],mode)

    def test_unsupported_call_cannot_partially_overwrite_stack(self):
        a=next(c['bsd_calls'][0]['before']for c in self.fixture['cases']if c['bsd_calls'])
        for mode in ('direction','signal','vdso'):
            m=memory_for(a);registers=dict(a['registers']);boot=startup(m,a['main_frame']);has_vdso=True
            if mode=='direction':registers['eflags']|=0x400
            elif mode=='signal':m.put_u32(registers['esp']+4,32)
            else:has_vdso=False
            address=a['stack']['address'];data=m.read(address,len(a['stack']['data'])//2)
            with self.assertRaises(NotImplementedError):bsd_signal(m,registers,libc_base=a['libc_base'],guard=boot['guard'],intr_mask=a['intr_mask'],old_action=a['old_action'],has_vdso=has_vdso)
            self.assertEqual(m.read(address,len(data)),data)

    def test_integer_flag_stores_preserve_non_arithmetic_bits(self):
        self.assertEqual(add_flags(0xffffffff,1,0x202),0x257)
        self.assertEqual(add_flags(0x7fffffff,1,0x202),0xa96)
        self.assertEqual(add_flags(0x80000000,0x80000000,0x202),0xa47)


if __name__=='__main__':unittest.main()

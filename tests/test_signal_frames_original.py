"""Independent kernel ABI stores; never a late seed for command continuation."""
import collections,copy,gzip,hashlib,json,os,re,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_signal_frames_original as capture
from audit_signal_frames_original import compare
from reasitic.signal_frame import deliver,legacy_x87,elf32_symbols
from reasitic.heap import AddressSpace
from reasitic.memory import Memory


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class SignalFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=load('signal_frames_original.json.gz')

    def test_all_original_jobs_environment_and_provenance_retained(self):
        f=self.fixture;p=f['signal_frame_provenance'];jobs=list(capture.jobs())
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['cpu_probe'],capture.CPU_PROBE)
        self.assertEqual(p['cpu_probe_sha256'],hashlib.sha256(capture.CPU_PROBE.encode()).hexdigest())
        self.assertEqual(f['gdb_commands'],capture.commands());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for case,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(case[key],job[key])
            self.assertIsNone(case['signal_pending'])
            for arrival in case['arrivals']:
                before=arrival['before'];self.assertLessEqual(set(before['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(before['environment'][key],value)
                for part in bytes.fromhex(before['stack']['data']).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
                for key in ('stack','xstate'):
                    self.assertEqual(len(before[key]['data'])if key=='stack'else len(before[key]),len(arrival['after'][key]['data'])if key=='stack'else len(arrival['after'][key]))

    def test_every_native_delivery_whole_stack_and_cpu_state_exact(self):
        results=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in results],[[]]*134)
        for key,total in [('deliveries_checked',130),('stack_words_checked',4392960),('registers_checked',2210),('xstate_bytes_checked',317200),('legacy_bytes_checked',14040)]:self.assertEqual(sum(r[key]for r in results),total)

    def test_pre_delivery_faults_and_plain_outcomes_remain_explicit(self):
        cases=self.fixture['cases']
        self.assertEqual(collections.Counter(c['signal']for c in cases),{0:129,11:4,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in cases),{0:129,-6:4,-11:1})
        self.assertEqual([(c['label'],c['cache_mode'],c['signal'])for c in cases if not c['arrivals']],[('square/64/contacts','cold',11),('pilot-width3/1/contacts','cold',11),('pilot-width3/1/contacts','warm',11),('pilot-boundary/1/coarse','warm',11)])
        rectangular=next(c for c in cases if(c['label'],c['cache_mode'])==('prelude/fft/16/8','cold'))
        self.assertEqual((len(rectangular['arrivals']),rectangular['signal']),(1,6))

    def test_later_stack_register_and_xstate_bytes_do_not_seed_runtime(self):
        case=copy.deepcopy(self.fixture['cases'][0]);after=case['arrivals'][0]['after'];stack=after['stack'];offset=after['registers']['esp']-stack['address']
        raw=bytearray.fromhex(stack['data']);raw[offset]^=1;stack['data']=raw.hex()
        after['registers']['eax']^=1;after['xstate']='00'+after['xstate'][2:]
        result=compare(self.fixture,case)
        self.assertEqual(collections.Counter(d['kind']for d in result['differences']),{'signal-stack-word':1,'signal-register':1,'signal-xstate-byte':1})

    def test_legacy_ptrace_record_is_an_independent_assertion(self):
        case=copy.deepcopy(self.fixture['cases'][0]);before=case['arrivals'][0]['before'];before['fpregs']='00'+before['fpregs'][2:]
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['signal-legacy-byte'])

    def test_reserved_frame_and_pkru_bytes_retain_earlier_memory(self):
        case=copy.deepcopy(self.fixture['cases'][0]);before,after=case['arrivals'][0]['before'],case['arrivals'][0]['after'];frame=after['registers']['esp']
        original=bytes.fromhex(after['stack']['data']);start=after['stack']['address'];fp=struct.unpack_from('<I',original,frame-start+84)[0];fx=fp+112
        pkru=next(c for c in self.fixture['signal_frame_provenance']['cpu']['components']if c['bit']==9)['offset']
        for address in (frame+96,fx+416,fx+pkru+4):
            for phase in (before,after):
                stack=phase['stack'];raw=bytearray.fromhex(stack['data']);offset=address-stack['address'];raw[offset:offset+4]=b'abcd';stack['data']=raw.hex()
        self.assertEqual(compare(self.fixture,case)['differences'],[])

    def test_x87_full_tags_rotate_with_top_and_classify_extended_values(self):
        x=bytearray(2440);struct.pack_into('<HH',x,0,0x37f,3<<11);x[4]=255
        numbers=[(0,0),(1<<63,0x3fff),(1<<63,0x7fff),(1,0),(0,0x8000),(1,0x3fff),((1<<64)-1,0x7fff),(1<<63,0x4000)]
        for i,(significand,exponent)in enumerate(numbers):struct.pack_into('<QH',x,32+16*i,significand,exponent)
        actual=legacy_x87(x,dict(cs=35,ds=43))
        self.assertEqual(struct.unpack_from('<I',actual,8)[0],0xffff684a)
        self.assertEqual(actual[28:],b''.join(struct.pack('<QH',*n)for n in numbers))
        x[4]=0;self.assertEqual(struct.unpack_from('<I',legacy_x87(x,dict(cs=35,ds=43)),8)[0],0xffffffff)

    def test_pending_delivery_and_unsupported_actions_are_failures(self):
        case=copy.deepcopy(self.fixture['cases'][0]);case['signal_pending']=dict(unobserved=True)
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['signal-delivery-not-observed'])
        case=copy.deepcopy(self.fixture['cases'][0]);case['arrivals'][0]['before']['action']['flags']|=4
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['signal-runtime'])

    def test_invalid_or_unsupported_xstate_cannot_change_stack(self):
        original=self.fixture['cases'][0]['arrivals'][0]['before'];cpu=self.fixture['signal_frame_provenance']['cpu']
        for mode in ('truncated','compacted','active','extent'):
            state=bytearray.fromhex(original['xstate']);layout=copy.deepcopy(cpu)
            if mode=='truncated':state=state[:512]
            elif mode=='compacted':struct.pack_into('<Q',state,520,1<<63)
            elif mode=='active':struct.pack_into('<Q',state,512,1<<63)
            else:layout['components'][0]['offset']=len(state)
            stack=original['stack'];address=stack['address'];data=bytes.fromhex(stack['data'])
            memory=Memory(AddressSpace([dict(start=address,end=address+len(data))]));memory.write(address,data)
            with self.subTest(mode=mode),self.assertRaises((ValueError,NotImplementedError)):
                deliver(memory,original['registers'],state,number=3,action=original['action'],mask=original['mask'],thread=original['thread'],cpu=layout,vdso=original['vdso'])
            self.assertEqual(memory.read(address,len(data)),data)


if __name__=='__main__':unittest.main()

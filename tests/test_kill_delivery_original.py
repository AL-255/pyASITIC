"""Native kill -> handler, once-initialized memory and actual earlier FP."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_kill_delivery_original as capture
from audit_kill_delivery_original import compare,run
from audit_loader_lookup_original import data,memory_for
from reasitic.kill_delivery import deliver_from_kill


class KillDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/kill_delivery_original.json.gz').read_bytes()));cls.case=next(c for c in cls.fixture['cases']if c['kill_calls']);cls.call=cls.case['kill_calls'][0]

    def arguments(self,entry=None):
        a=self.call['entry']if entry is None else entry
        return dict({k:a[k]for k in('libc_base','tls_base','number','mask','action','process','thread','vdso')},cpu=self.fixture['kill_delivery_provenance']['cpu'])

    def test_all_jobs_provenance_native_outcomes_and_complete_owners(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['kill_delivery_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(f['gdb_commands'],capture.commands());self.assertEqual(p['cpu_probe'],capture.parent.CPU_PROBE);self.assertEqual(p['cpu_probe_sha256'],hashlib.sha256(p['cpu_probe'].encode()).hexdigest())
        self.assertEqual(p['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0');self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:129,11:4,6:1});self.assertEqual(collections.Counter(c['plain']['returncode']for c in f['cases']),{0:127,-6:6,-11:1})
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            self.assertIsNone(c['signal_pending']);self.assertEqual(len(c['arrivals']),len(c['kill_calls']))
            for call in c['kill_calls']:
                self.assertEqual(set(call),{'entry','vdso','kernel','interrupted','handler'});a=call['entry'];self.assertLessEqual(set(a['environment']),allowed)
                owners=[(r['address'],r['size'])for r in a['regions']]
                for point in call.values():
                    self.assertEqual([(r['address'],r['size'])for r in point['regions']],owners)
                    for r in point['regions']:self.assertEqual(len(data(f,r)),r['size'])

    def test_every_whole_stack_gp_fp_legacy_and_mask_target(self):
        r=run(self.fixture)
        for key,value in(('cases',134),('cases_without_kill',4),('calls_checked',130),('boundaries_checked',520),('words_checked',19173440),('registers_checked',8840),('fp_bytes_checked',1268800),('legacy_bytes_checked',70200),('masks_checked',520),('differences',0)):self.assertEqual(r[key],value)

    def test_later_inner_targets_never_supply_execution_state(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);call=c['kill_calls'][0];b=call['vdso'];address=b['registers']['esp'];r=next(r for r in b['regions']if r['address']<=address<r['address']+r['size'])
        raw=bytearray(data(f,r));raw[address-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r['sha256']=key;b['registers']['eax']^=1
        b=call['kernel'];raw=bytearray.fromhex(b['xstate']);raw[0]^=1;b['xstate']=raw.hex();b['mask']^=1
        b=call['interrupted'];raw=bytearray.fromhex(b['fpregs']);raw[0]^=1;b['fpregs']=raw.hex()
        report=compare(f,c)
        self.assertEqual(collections.Counter(d['kind']for d in report['differences']),{'kill-delivery-memory-word':1,'kill-delivery-register':1,'kill-delivery-fp-byte':1,'kill-delivery-mask':1,'kill-delivery-legacy-byte':1})
        self.assertFalse(any(d.get('phase')=='handler'for d in report['differences']))

    def test_modified_earlier_fp_is_serialized_and_handler_fp_is_initialized(self):
        a=self.call['entry'];m=memory_for(self.fixture,a);fp=bytearray.fromhex(a['xstate']);fp[32]^=1;seen=[]
        result=deliver_from_kill(m,a['registers'],fp,**self.arguments(),observer=lambda phase,r,x,mask:seen.append((phase,r,x,mask)))
        self.assertEqual([p for p,_,_,_ in seen],['vdso','kernel','interrupted','handler'])
        self.assertTrue(all(x==fp for _,_,x,_ in seen[:3]));self.assertEqual(m.read(result['fxstate']+32,16),fp[32:48])
        self.assertEqual(result['xstate'],bytes.fromhex(self.call['handler']['xstate']));self.assertEqual(result['registers'],self.call['handler']['registers'])

    def test_interrupted_ebp_and_saved_context_come_from_earlier_registers(self):
        a=self.call['entry'];m=memory_for(self.fixture,a);r=dict(a['registers'],ebp=0x11223344);seen={}
        result=deliver_from_kill(m,r,bytes.fromhex(a['xstate']),**self.arguments(),observer=lambda phase,r,x,mask:seen.update({phase:r}))
        self.assertEqual(seen['kernel']['ebp'],a['number']);self.assertEqual(seen['interrupted']['ebp'],0x11223344)
        self.assertEqual(seen['interrupted']['orig_eax'],37);self.assertEqual(seen['interrupted']['eax'],0);self.assertEqual(seen['interrupted']['eip'],seen['kernel']['eip']+4)
        self.assertEqual(m.u32(result['frame']+32),0x11223344);self.assertEqual(result['registers']['ebp'],0x11223344)

    def test_earlier_action_and_mask_control_handler_entry(self):
        a=self.call['entry'];m=memory_for(self.fixture,a);args=self.arguments();args['action']=dict(args['action'],handler=0x12345678,mask=1<<12)
        result=deliver_from_kill(m,a['registers'],bytes.fromhex(a['xstate']),**args)
        self.assertEqual(result['registers']['eip'],0x12345678);self.assertEqual(result['mask'],a['mask']|(1<<12)|(1<<(a['number']-1)))

    def test_missing_earlier_code_and_fp_cannot_use_later_snapshots(self):
        c=copy.deepcopy(self.case);a=c['kill_calls'][0]['entry'];a['regions']=[r for r in a['regions']if r['address']!=a['vdso']['address']]
        self.assertTrue(any(d['kind']=='kill-delivery-runtime'for d in compare(self.fixture,c)['differences']))
        a=self.call['entry'];m=memory_for(self.fixture,a);s=a['registers']['esp'];before=m.read(s-16,16)
        with self.assertRaisesRegex(ValueError,'actual earlier XSAVE'):deliver_from_kill(m,a['registers'],None,**self.arguments())
        self.assertEqual(m.read(s-16,16),before)
        with self.assertRaisesRegex(ValueError,'complete earlier standard XSAVE'):deliver_from_kill(m,a['registers'],bytes(64),**self.arguments())
        self.assertEqual(m.read(s-16,16),before)

    def test_pending_or_other_process_targets_fail_explicitly(self):
        a=self.call['entry']
        for mode in('blocked','other-target','ignored'):
            m=memory_for(self.fixture,a);args=self.arguments()
            if mode=='blocked':args['mask']|=1<<(a['number']-1)
            elif mode=='other-target':m.put_u32(a['registers']['esp']+4,1)
            else:args['action']=dict(args['action'],handler=1)
            with self.subTest(mode=mode),self.assertRaises(NotImplementedError):deliver_from_kill(m,a['registers'],bytes.fromhex(a['xstate']),**args)

    def test_other_recognized_vdso_abi_uses_saved_stack_and_landing_pad(self):
        a=self.call['entry'];m=memory_for(self.fixture,a);pc=m.u32(a['tls_base']+16);m.write(pc,bytes.fromhex('51525589e50f34cd805d5a59c3'));seen={}
        result=deliver_from_kill(m,a['registers'],bytes.fromhex(a['xstate']),**self.arguments(),observer=lambda phase,r,x,mask:seen.update({phase:r}))
        self.assertEqual(seen['kernel']['ebp'],seen['kernel']['esp']);self.assertEqual(seen['kernel']['eip'],pc+5)
        self.assertEqual(seen['interrupted']['eip'],pc+9);self.assertEqual(seen['interrupted']['ebp'],a['registers']['ebp']);self.assertEqual(seen['interrupted']['eflags']&0x200,0x200)
        self.assertEqual(result['registers']['eax'],a['number'])


if __name__=='__main__':unittest.main()

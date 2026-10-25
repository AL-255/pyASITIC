"""Original history/normalize/quit caller stores and independent outputs."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_dispatch_storage_original as capture
from audit_dispatch_storage_original import compare
from audit_loader_lookup_original import data,memory_for
from reasitic.command_storage import Characters,string
from reasitic.dispatch_storage import DispatchStorage
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class DispatchStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('dispatch_storage_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['dispatch_calls'])

    def test_all_original_jobs_boundaries_metadata_and_minimal_environments(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['dispatch_storage_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['history_shim_sha256'],'91bfdf1bce9990520d44fc1d66d7a0dbb0a14c5a096acaab1cfae93ec333d90f')
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['dispatch_calls']:
                self.assertEqual(set(call),{'entry','history','parse','parsed','kill'});a=call['entry'];self.assertLessEqual(set(a['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(a['environment'][key],value)
                s=a['registers']['esp'];stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
                for phase in call.values():
                    for r in phase['regions']:data(f,r)

    def test_every_complete_original_phase_memory_register_and_fp_byte(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,value in [('operations_checked',3),('words_checked',499815),('registers_checked',51),('fp_bytes_checked',7320)]:self.assertEqual(sum(r[key]for r in reports),value)

    def test_histories_without_dispatch_and_native_faults_remain_explicit(self):
        cases=self.fixture['cases'];self.assertEqual(sum(not c['dispatch_calls']for c in cases),133)
        self.assertEqual(collections.Counter(c['signal']for c in cases),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in cases),{0:130,-11:2,-6:2})
        self.assertEqual([(c['label'],c['cache_mode'])for c in cases if c['dispatch_calls']],[('prelude/fft/16/8','cold')])

    def test_later_memory_register_and_fp_outputs_cannot_seed_operations(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);call=c['dispatch_calls'][0];b=call['parse'];s=b['registers']['esp'];r=next(r for r in b['regions']if r['address']<=s<r['address']+r['size'])
        raw=bytearray(data(f,r));raw[s-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r['sha256']=key
        b['registers']['eax']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'dispatch-memory-word':1,'dispatch-register':1,'dispatch-fp-byte':1})
        b['regions'].pop();self.assertIn('dispatch-region-owners',[d['kind']for d in compare(f,c)['differences']])

    def test_history_scan_and_saved_words_follow_earlier_entry(self):
        a=self.case['dispatch_calls'][0]['entry'];m=memory_for(self.fixture,a);regs=dict(a['registers']);s=regs['esp'];line=m.u32(s+4);m.write(line,b'end\0');regs.update(edi=0x11223344,ebx=0xaabbccdd)
        engine=DispatchStorage(m,Characters(a['characters']),PltFixup(m,a['loader_base'],tls_base=a['tls_base']),a);result=engine.history(regs);records=s-4-4160
        self.assertEqual(result['ecx'],0xfffffffb);self.assertEqual(result['edi'],line+4);self.assertEqual(result['ebx'],line)
        self.assertEqual(m.u32(records-4),0x11223344);self.assertEqual(m.u32(records-8),0xaabbccdd);self.assertEqual(string(m,line),b'end')

    def test_normalization_abi_keeps_padding_and_semantic_output(self):
        a=self.case['dispatch_calls'][0]['history'];context=self.case['dispatch_calls'][0]['entry'];m=memory_for(self.fixture,a);f=a['registers']['ebp']-4160-24;m.write(f-8,b'ABCD')
        engine=DispatchStorage(m,Characters(context['characters']),PltFixup(m,context['loader_base'],tls_base=context['tls_base']),context);result=engine.before_parser(a['registers'])
        self.assertEqual(m.read(f-8,3),b'ABC');self.assertEqual(m.read(f-5,1),b'\0');self.assertEqual(result['edx'],ord('t'))
        self.assertEqual(m.u32(f-48),ord('t'));self.assertEqual(m.u32(f-40),1);self.assertEqual(m.u32(f-44),0)

    def test_continuing_entry_registers_come_from_source_main_state(self):
        from audit_command_transition_original import compare as continuing
        f=load('loader_transition_original.json.gz');c=next(c for c in f['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold');seen=[];history=DispatchStorage.history
        def observe(self,registers):seen.append(dict(registers));return history(self,registers)
        with patch.object(DispatchStorage,'history',observe):report=continuing(f,c)
        self.assertEqual(len(seen),1);native=self.case['dispatch_calls'][0]['entry']['registers']
        for key,value in seen[0].items():self.assertEqual(value,native[key],key)
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))


if __name__=='__main__':unittest.main()

"""Native complete PLT fixups and independence from later target values."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_plt_fixup_original as capture
from audit_loader_lookup_original import data,memory_for
from audit_plt_fixup_original import compare
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class PltFixupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('plt_fixup_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['plt_calls'])

    def test_all_jobs_provenance_and_minimal_environments(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        p=f['plt_fixup_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(p['loader_sha256'],'64f2864e740bf9cc15c01466c438d6ba25c7bc9cf9401d8122287ee7ed05e26d')
        self.assertEqual(p['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key])
            self.assertEqual(c['plt_pending'],0)
            for call in c['plt_calls']:
                a=call['before'];self.assertLessEqual(set(a['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(a['environment'][key],value)
                s=a['registers']['esp'];self.assertEqual(a['registers']['eip'],a['loader_base']+0x11ba0)
                stack=next(r for r in a['regions']if r['address']<=s<r['address']+r['size'])
                for part in data(f,stack).split(b'\0'):
                    key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                    if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))

    def test_all_complete_target_regions_registers_and_fp_are_exact(self):
        reports=[compare(self.fixture,c)for c in self.fixture['cases']]
        self.assertEqual([r['differences']for r in reports],[[]]*134)
        for key,total in [('calls_checked',8),('words_checked',1332840),('registers_checked',136),('fp_bytes_checked',19520)]:self.assertEqual(sum(r[key]for r in reports),total)

    def test_first_signal_target_is_not_overwritten_by_later_calls(self):
        call=self.case['plt_calls'][0];a,b=call['before'],call['after'];m=memory_for(self.fixture,a)
        self.assertEqual(m.u32(a['registers']['esp']+12),2)
        self.assertEqual(b['registers']['esp'],a['registers']['esp']+8)
        for name in ('eax','ebx','ecx','edx','esi','edi','ebp'):self.assertEqual(a['registers'][name],b['registers'][name])
        self.assertIn("if 'after'in self.item:return False",capture.OBSERVER);self.assertIn('self.enabled=False',capture.OBSERVER)
        self.assertNotIn('BP_HARDWARE_BREAKPOINT',capture.OBSERVER)

    def test_output_mutations_are_failures_not_inputs(self):
        f=copy.deepcopy(self.fixture);case=copy.deepcopy(self.case);case['plt_calls']=case['plt_calls'][:1];a,b=case['plt_calls'][0]['before'],case['plt_calls'][0]['after'];s=a['registers']['esp']
        r=next(r for r in b['regions']if r['address']<=s<r['address']+r['size']);raw=bytearray(data(f,r));raw[s-8-r['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();r['sha256']=key
        b['registers']['eip']^=1;b['xstate']='00'+b['xstate'][2:]
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,case)['differences']),{'plt-fixup-memory-word':1,'plt-fixup-register':1,'plt-fixup-fp-byte':1})

    def test_named_import_uses_relocation_and_bypasses_a_bound_slot(self):
        a=self.case['plt_calls'][0]['before'];m=memory_for(self.fixture,a);t=a['registers']['esp'];map_=m.u32(t);offset=m.u32(t+4);engine=PltFixup(m,a['loader_base'],tls_base=a['tls_base'])
        reloc=engine._dynamic(map_,23)+offset;symbol=engine._dynamic(map_,6)+16*(m.u32(reloc+4)>>8)
        name=engine._string(engine._dynamic(map_,5)+m.u32(symbol));plt=dict(address=m.u32(symbol+4)-16*(offset//8+1),size=16*(m.u32(m.u32(map_+40)+4)//8+1))
        registers=dict(a['registers']);registers['esp']=t+8
        result=engine.bind_import(registers,map_,name,plt);self.assertTrue(result['lazy'])
        before=[m.read(r['address'],r['size'])for r in a['regions']]
        again=engine.bind_import(registers,map_,name,plt);self.assertFalse(again['lazy']);self.assertEqual(again['target'],result['target'])
        self.assertEqual([m.read(r['address'],r['size'])for r in a['regions']],before)

    def test_ifunc_selection_uses_earlier_cpu_bits(self):
        a=self.case['plt_calls'][5]['before']
        for usable,preferred,sse2,offset in ((4,1,2,0xb6790),(0,0,2,0xb4d20),(0,0,0,0xbbc60)):
            m=memory_for(self.fixture,a);libc=next(x for x in a['maps']if x['name'].endswith('/libc.so.6'));base=m.u32(libc['address']);cpu=m.u32(base+0x22fe34+0x10c)
            m.write(cpu+0x7b,bytes([usable]));m.write(cpu+0x19c,bytes([preferred]));m.write(cpu+0x75,bytes([sse2]))
            self.assertEqual(PltFixup(m,a['loader_base'],tls_base=a['tls_base']).resolve(a['registers'])['target'],base+offset)

    def test_bind_not_preserves_the_existing_got_slot(self):
        a=self.case['plt_calls'][0]['before'];m=memory_for(self.fixture,a);engine=PltFixup(m,a['loader_base'],tls_base=a['tls_base']);t=a['registers']['esp'];map_=m.u32(t);reloc=engine._dynamic(map_,23)+m.u32(t+4);slot=m.u32(map_)+m.u32(reloc);old=m.u32(slot)
        m.put_u32(engine.got-0x458,1);result=engine.resolve(a['registers'])
        self.assertEqual(m.u32(slot),old);self.assertNotEqual(result['target'],old)

    def test_thread_and_audit_paths_are_explicit_before_stack_writes(self):
        a=self.case['plt_calls'][0]['before']
        for mode in ('thread','audit'):
            m=memory_for(self.fixture,a);engine=PltFixup(m,a['loader_base'],tls_base=a['tls_base']);t=a['registers']['esp']
            m.put_u32(a['tls_base']+12 if mode=='thread'else m.u32(t)+448,1);before=m.read(t-1000,1000)
            with self.assertRaises(NotImplementedError):engine.resolve(a['registers'])
            self.assertEqual(m.read(t-1000,1000),before)


if __name__=='__main__':unittest.main()

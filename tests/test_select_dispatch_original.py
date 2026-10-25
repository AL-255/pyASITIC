"""Complete native select64 setup, independent edge inputs and continuation."""
import collections,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_select_dispatch_original as capture
import capture_select_dispatch_probe as probe
from audit_select_dispatch_original import run,compare
from audit_poll_storage_original import compare as phases
from audit_loader_lookup_original import data,memory_for
from reasitic.select_storage import select64_dispatch,select_syscall_entry


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class SelectDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('select_dispatch_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['poll_calls']);cls.probe=load('select_dispatch_probe.json.gz')

    def test_all_jobs_inputs_native_outcomes_and_complete_owners(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(jobs),67);self.assertEqual(len(f['cases']),134)
        p=f['select_dispatch_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['libc_sha256'],probe.LIBC_SHA256)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['poll_calls']:
                self.assertEqual(set(call),{'entry','select','select64','syscall','vdso'})
                owners=[(r['address'],r['size'])for r in call['entry']['regions']]
                for point in call.values():
                    self.assertEqual([(r['address'],r['size'])for r in point['regions']],owners)
                    for r in point['regions']:self.assertEqual(len(data(f,r)),r['size'])

    def test_every_native_memory_gp_and_fp_target_is_required(self):
        report=run(self.fixture);self.assertEqual(report['cases'],134);self.assertEqual(report['cases_without_poll'],133)
        self.assertEqual(report['operations_checked'],4);self.assertEqual(report['registers_checked'],68);self.assertEqual(report['fp_bytes_checked'],9760)
        self.assertEqual(report['words_checked'],666420);self.assertEqual(report['differences'],0)

    def test_independent_null_normalized_overflow_time64_and_invalid_inputs(self):
        f=self.probe;self.assertEqual(f['requests'],probe.requests());self.assertEqual(f['source'],probe.source());self.assertEqual(f['observer'],probe.OBSERVER)
        self.assertEqual(f['source_sha256'],hashlib.sha256(f['source'].encode()).hexdigest());self.assertEqual(f['libc_sha256'],probe.LIBC_SHA256)
        self.assertEqual(f['native_exit'],0);self.assertEqual(f['plain']['returncode'],0)
        c=f['cases'][0];self.assertEqual(len(c['poll_calls']),13);self.assertEqual(collections.Counter(call['boundary']for call in c['poll_calls']),{'syscall':10,'return':3})
        for call,request in zip(c['poll_calls'],f['requests']):
            a=call['entry'];m=memory_for(f,a);s=a['registers']['esp'];pointer=m.u32(s+20)
            self.assertEqual(m.u32(s+4),1);self.assertEqual(pointer==0,request['null_timeout'])
            if pointer:
                self.assertEqual(m.u32(pointer),request['seconds']&0xffffffff);self.assertEqual(m.u32(pointer+4),(request['seconds']>>32)&0xffffffff);self.assertEqual(m.u32(pointer+8),request['microseconds']&0xffffffff)
            self.assertEqual(call['boundary'],'return'if request['seconds']<0 or request['microseconds']<0 else'syscall')
        report=phases(f,c,phases=[('dispatch','entry','after')]);self.assertEqual(report['operations_checked'],13);self.assertEqual(report['differences'],[])
        helpers=dict(c,poll_calls=[dict(call,syscall=call['after'])for call in c['poll_calls']if call['boundary']=='syscall'])
        report=phases(f,helpers,phases=[('syscall','syscall','vdso')]);self.assertEqual(report['operations_checked'],10);self.assertEqual(report['differences'],[])

    def test_helper_consumes_produced_dispatch_without_loading_inner_state(self):
        for call in self.probe['cases'][0]['poll_calls']:
            if call['boundary']!='syscall':continue
            a=call['entry'];m=memory_for(self.probe,a);base=m.u32(next(x['address']for x in a['maps']if x['name'].endswith('/libc.so.6')));kwargs=dict(libc_base=base,tls_base=a['tls_base'])
            registers=select64_dispatch(m,a['registers'],**kwargs);self.assertEqual(registers,call['after']['registers'])
            registers=select_syscall_entry(m,registers,**kwargs);self.assertEqual(registers,call['vdso']['registers'])
            for r in call['vdso']['regions']:self.assertEqual(m.read(r['address'],r['size']),data(self.probe,r))

    def test_later_targets_are_assertions_and_cannot_repair_execution(self):
        f=copy.deepcopy(self.fixture);c=copy.deepcopy(self.case);end=c['poll_calls'][0]['vdso'];address=end['registers']['esp']
        region=next(r for r in end['regions']if r['address']<=address<r['address']+r['size']);raw=bytearray(data(f,region));raw[address-region['address']]^=1;key=hashlib.sha256(raw).hexdigest();f['loader_regions'][key]=raw.hex();region['sha256']=key
        end['registers']['eax']^=1;raw=bytearray.fromhex(end['xstate']);raw[0]^=1;end['xstate']=raw.hex()
        self.assertEqual(collections.Counter(d['kind']for d in compare(f,c)['differences']),{'poll-memory-word':1,'poll-register':1,'poll-fp-byte':1})

    def test_missing_earlier_stack_does_not_use_later_copies(self):
        c=copy.deepcopy(self.case);a=c['poll_calls'][0]['select64'];s=a['registers']['esp'];a['regions']=[r for r in a['regions']if not r['address']<=s<r['address']+r['size']]
        report=compare(self.fixture,c);self.assertTrue(any(d['kind']=='poll-runtime'and d['phase']=='dispatch'and any(word in d['reason']for word in('Uninitialized','Unmapped'))for d in report['differences']))

    def test_helper_uses_live_arguments_and_cancellation_is_explicit(self):
        a=self.case['poll_calls'][0]['select64'];context=self.case['poll_calls'][0]['entry'];m=memory_for(self.fixture,a);base=m.u32(next(x['address']for x in context['maps']if x['name'].endswith('/libc.so.6')));kwargs=dict(libc_base=base,tls_base=context['tls_base'])
        r=select64_dispatch(m,a['registers'],**kwargs);s=r['esp'];m.put_u32(r['edi'],7);m.put_u32(r['edi']+8,0x12345678)
        after=select_syscall_entry(m,r,**kwargs);self.assertEqual(after['ebx'],7);self.assertEqual(after['ebp'],0x12345678);self.assertEqual(m.u32(s-12),r['ebp']);self.assertEqual(after['eflags'],r['eflags'])
        m.put_u32(context['tls_base']+12,1)
        with self.assertRaisesRegex(NotImplementedError,'cancellation'):select64_dispatch(m,a['registers'],**kwargs)

    def test_continuing_calls_share_source_memory_and_actual_registers(self):
        import reasitic.command_transition as transition
        from audit_command_transition_original import compare as continuing
        f=load('printf_transition_original.json.gz');c=next(c for c in f['cases']if c['label']==self.case['label']and c['cache_mode']==self.case['cache_mode']);seen=[]
        def wrap(function):
            def call(memory,registers,**kwargs):
                result=function(memory,registers,**kwargs);seen.append((memory,dict(registers),dict(result)));return result
            return call
        with patch.object(transition,'select64_dispatch',wrap(select64_dispatch)),patch.object(transition,'select_syscall_entry',wrap(select_syscall_entry)):report,_,_,memory=continuing(f,c,return_state=True)
        self.assertEqual(len(seen),2);self.assertTrue(all(item[0]is memory for item in seen));self.assertEqual(seen[0][2],seen[1][1]);self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))
        native=self.case['poll_calls'][0]
        self.assertEqual(seen[0][1],native['select64']['registers']);self.assertEqual(seen[0][2],native['syscall']['registers']);self.assertEqual(seen[1][2],native['vdso']['registers'])
        self.assertTrue(report['differences'],'The remaining continuation gate stays required')


if __name__=='__main__':unittest.main()

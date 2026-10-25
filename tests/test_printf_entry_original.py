"""Public printf calls retain every native state/helper target and earlier input."""
import collections,copy,gzip,hashlib,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_printf_entry_original as capture
import audit_printf_entry_original as audit
import capture_printf_entry_probe as probe_capture
from printf_archive import read_fixture
from printf_fixture import expand_state,unpack_state
from capture_getline_bytes_original import CPU_PROBE
from reasitic.memory import UnknownMemory


class PrintfEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(os.environ.get('PYASITIC_PRINTF_ENTRY_FIXTURE',ROOT/'tests/fixtures/printf_entry_original.manifest.json'));cls.case=cls.fixture['cases'][0];cls.one=dict(cls.case,printf_calls=[cls.case['printf_calls'][0]])
        cls.probe=json.loads(gzip.decompress((ROOT/'tests/fixtures/printf_entry_probe.json.gz').read_bytes()))

    def test_all_unchanged_jobs_complete_earlier_entry_ownership(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        calls=[c for case in f['cases']for c in case['printf_calls']]
        self.assertEqual(len(calls),3973);self.assertEqual(sum(len(c['children'])for c in calls),123122)
        self.assertEqual(collections.Counter(c['kind']for c in calls),{'printf':140,'fprintf':3833})
        self.assertEqual(sum(c['formatter']['children_end']-c['formatter']['children_start']for c in calls),98228)
        self.assertEqual(sum(ch['kind']=='vfprintf'for c in calls for ch in c['children']),3973)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in f['cases']),{0:128,-6:5,-11:1})
        self.assertEqual(f['integer_cpu']['probe'],CPU_PROBE);self.assertEqual(f['printf_entry_provenance']['observer'],capture.OBSERVER)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        entries={'printf':0x57db0,'fprintf':0x57670,'vfprintf_public':0x5e680}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                a=unpack_state(f,call['before']);info=a['format_inputs'];libc=next(e for e in info['elf_data']if e['path'].endswith('/libc.so.6'))
                self.assertEqual(libc['elf_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
                self.assertEqual(a['entry_kind'],call['kind']);self.assertEqual(a['registers']['eip'],libc['base']+entries[call['kind']]);self.assertEqual(info['pthread_size'],1216)
                self.assertEqual(info['static_tls']['address']+info['static_tls']['size'],a['tls_base']+1216)
                self.assertEqual(call['children'][0]['kind'],'vfprintf');self.assertEqual(call['children'][0]['before']['eip'],libc['base']+0x62110)

    def test_independent_native_probe_provenance_and_all_requests(self):
        p=self.probe;self.assertEqual(p['source'],probe_capture.source());self.assertEqual(p['source_sha256'],hashlib.sha256(p['source'].encode()).hexdigest());self.assertEqual(p['requests'],probe_capture.requests());self.assertEqual(p['observer'],probe_capture.OBSERVER)
        directory=p['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(p['gdb_commands'],probe_capture.commands(Path(directory)))
        self.assertEqual(p['libc_sha256'],probe_capture.LIBC_SHA256);self.assertEqual(p['integer_cpu']['probe'],CPU_PROBE);self.assertEqual(p['plain']['returncode'],0);self.assertEqual(p['plain']['stderr'],'')
        calls=p['cases'][0]['printf_calls'];self.assertEqual(len(calls),18);self.assertEqual([c['kind']for c in calls],[r['kind']for r in p['requests']]);self.assertEqual(sum(len(c['children'])for c in calls),548)
        self.assertEqual(p['cases'][0]['signal'],0);self.assertEqual(p['cases'][0]['native_exit'],0)
        for flag in('-m32','-fno-builtin','-nostdlib','-no-pie'):self.assertIn(flag,p['compile_command'])
        for call,request in zip(calls,p['requests']):
            a=expand_state(p,call['before']);m,storage=audit.engine(p,a);s=a['registers']['esp'];self.assertIsNone(storage.file.io.legacy)
            args=m.u32(s+12)if call['kind']=='vfprintf_public'else s+(8 if call['kind']=='printf'else 12)
            self.assertEqual(m.u32(args+4),request['integer']);self.assertEqual(m.read(args+8,8).hex(),request['double_bits']);self.assertEqual(m.read(m.u32(args),6),b'probe\0')

    def test_every_independent_native_public_entry_stays_required(self):
        report=audit.run(self.probe)
        if target:=os.environ.get('PYASITIC_PRINTF_ENTRY_PROBE_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report['calls_checked'],18);self.assertEqual(report['boundary_states_checked'],36);self.assertEqual(report['children_checked'],548)
        self.assertEqual(report['registers_checked'],306);self.assertEqual(report['child_registers_checked'],18632);self.assertEqual(report['fp_bytes_checked'],43920);self.assertEqual(report['boundary_fp_bytes_checked'],87840)
        self.assertEqual(report['differences'],0,'All extreme-value, old-FILE and kernel-owned native assertions remain required')

    def test_every_public_call_boundary_and_helper_remains_required(self):
        f=self.fixture;report=audit.run(f,shard=int(os.environ.get('PYASITIC_PRINTF_ENTRY_SHARD','1')),shards=int(os.environ.get('PYASITIC_PRINTF_ENTRY_SHARDS','1')))
        if target:=os.environ.get('PYASITIC_PRINTF_ENTRY_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        calls=[c for i in report['case_indices']for c in f['cases'][i]['printf_calls']]
        self.assertEqual(report['parent_calls_required'],len(calls));self.assertEqual(report['calls_checked'],len(calls));self.assertEqual(report['boundary_states_checked'],2*len(calls))
        self.assertEqual(report['registers_checked'],17*len(calls));self.assertEqual(report['boundary_registers_checked'],34*len(calls))
        self.assertEqual(report['children_checked'],sum(len(c['children'])for c in calls));self.assertEqual(report['child_registers_checked'],34*report['children_checked'])
        self.assertEqual(report['fp_bytes_checked'],sum(len(unpack_state(f,c['after'])['xstate'])//2 for c in calls));self.assertEqual(report['boundary_fp_bytes_checked'],sum(len(unpack_state(f,c['formatter'][p])['xstate'])//2 for c in calls for p in('before','after')))
        self.assertEqual(report['differences'],0,'Every public return, inner boundary, helper and kernel-owned word remains required')

    def test_execution_initializes_only_at_actual_public_entry(self):
        original=audit.engine;seen=[]
        def track(f,state):seen.append(state['registers']);return original(f,state)
        with patch.object(audit,'engine',track):r=audit.compare(self.fixture,self.one)
        self.assertEqual(seen,[unpack_state(self.fixture,self.one['printf_calls'][0]['before'])['registers']]);self.assertEqual(r['calls_checked'],1);self.assertEqual(r['boundary_states_checked'],2)

    def test_later_formatter_parent_and_helper_targets_cannot_supply_execution(self):
        base=audit.compare(self.fixture,self.one);c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        before=copy.deepcopy(expand_state(self.fixture,call['formatter']['before']));after=copy.deepcopy(expand_state(self.fixture,call['formatter']['after']));last=copy.deepcopy(expand_state(self.fixture,call['after']))
        before['registers']['eax']^=1;after['registers']['edx']^=1;after['xstate']='00'+after['xstate'][2:];after['heap']['top']+=16;last['registers']['eax']^=1
        call['formatter']['before']=before;call['formatter']['after']=after;call['after']=last;call['children'][0]['before']['eax']^=1;call['children'][0]['after']['ecx']^=1
        changed=audit.compare(self.fixture,c);self.assertEqual(changed['calls_checked'],1);self.assertEqual(changed['boundary_states_checked'],2)
        kinds=lambda r:collections.Counter((d['kind'],d.get('boundary'))for d in r['differences']);delta=kinds(changed)-kinds(base)
        for key in(('printf-register','formatter-before'),('printf-register','formatter-after'),('printf-fp-byte','formatter-after'),('state','formatter-after'),('printf-register',None)):self.assertEqual(delta[key],1,key)
        self.assertEqual(delta['printf-child-register',None],2)

    def test_actual_earlier_strings_reach_printf_and_fprintf(self):
        for kind,displacement,expected in(('printf',8,b'\nNEW'),('fprintf',12,b'\nNEW\n')):
            call=next(c for c in self.case['printf_calls']if c['kind']==kind);a=expand_state(self.fixture,call['before']);m,storage=audit.engine(self.fixture,a);r=a['registers'];s=r['esp'];m.write(m.u32(s+displacement),b'NEW\0')
            result=storage.entry(r);end=m.u32(a['file']+20);self.assertEqual(result['eax'],len(expected));self.assertEqual(m.read(end-len(expected),len(expected)),expected)

    def test_explicit_va_list_entry_uses_live_arguments(self):
        call=next(c for c in self.case['printf_calls']if c['kind']=='fprintf');a=expand_state(self.fixture,call['before']);m,storage=audit.engine(self.fixture,a);r=dict(a['registers'],eip=storage.libc+0x5e680);s=r['esp'];string=m.u32(s+12)
        m.put_u32(s+12,s+16);m.put_u32(s+16,string);m.write(string,b'NEW\0');result=storage.entry(r);end=m.u32(a['file']+20)
        self.assertEqual(result['eax'],5);self.assertEqual(m.read(end-5,5),b'\nNEW\n');self.assertEqual(storage.children[0]['before']['eax'],r['eax'])

    def test_string_calls_preserve_opaque_fp_and_floating_reads_still_fail(self):
        call=self.one['printf_calls'][0];a=expand_state(self.fixture,call['before']);m,storage=audit.engine(self.fixture,a);storage.xstate=None;storage.preserve_fp=True
        result=storage.entry(a['registers']);self.assertEqual(result,unpack_state(self.fixture,call['after'])['registers']);self.assertIsNone(storage.xstate,'String instructions must preserve unknown FP, not invent its bytes')
        call=next(c for c in self.case['printf_calls']if any(ch['kind']=='fp-l-buffer'for ch in c['children']));a=expand_state(self.fixture,call['before']);m,storage=audit.engine(self.fixture,a);storage.xstate=None;storage.preserve_fp=True
        with self.assertRaisesRegex(ValueError,'actual earlier XSAVE'):storage.entry(a['registers'])

    def test_missing_binding_fp_or_foreign_entry_fails(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=audit.engine(self.fixture,a);m.forget(storage.got+0xb8,4)
        with self.assertRaises(UnknownMemory):storage.entry(a['registers'])
        m,storage=audit.engine(self.fixture,a);storage.xstate=None
        with self.assertRaisesRegex(NotImplementedError,'actual earlier CPU/FP'):storage.entry(a['registers'])
        m,storage=audit.engine(self.fixture,a)
        with self.assertRaisesRegex(NotImplementedError,'Alternate printf entry'):storage.entry(dict(a['registers'],eip=0))

    def test_missing_or_invalid_inner_targets_fail(self):
        c=copy.deepcopy(self.one);del c['printf_calls'][0]['formatter']['after'];r=audit.compare(self.fixture,c);self.assertIn('vfprintf-whole-missing-boundary',[d['kind']for d in r['differences']])
        c=copy.deepcopy(self.one);c['printf_calls'][0]['formatter']['children_end']=-1
        with self.assertRaisesRegex(ValueError,'indices'):audit.compare(self.fixture,c)


if __name__=='__main__':unittest.main()

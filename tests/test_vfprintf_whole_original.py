"""All whole-parent state and inner boundaries remain required assertions."""
import collections,copy,hashlib,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_vfprintf_whole_original as capture
import audit_vfprintf_whole_original as audit
from audit_vfprintf_whole_original import compare,engine,run,selected_indices
from printf_archive import read_fixture
from printf_fixture import expand_state,unpack_state
from capture_getline_bytes_original import CPU_PROBE
from reasitic.memory import UnknownMemory


class WholeVfprintfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(os.environ.get('PYASITIC_VFPRINTF_WHOLE_FIXTURE',ROOT/'tests/fixtures/vfprintf_whole_original.manifest.json'));cls.case=cls.fixture['cases'][0];cls.one=dict(cls.case,printf_calls=[cls.case['printf_calls'][0]])

    def test_complete_unchanged_jobs_and_earlier_parent_ownership(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(sum(len(c['printf_calls'])for c in f['cases']),3973);self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})
        calls=[c for case in f['cases']for c in case['printf_calls']]
        self.assertEqual(sum(len(c['children'])for c in calls),119149)
        self.assertEqual(sum(c['formatter']['children_end']-c['formatter']['children_start']for c in calls),98228)
        self.assertEqual(sum(c['formatter']['children_start']+len(c['children'])-c['formatter']['children_end']for c in calls),20921)
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in f['cases']),{0:127,-6:6,-11:1})
        self.assertEqual(f['integer_cpu']['probe'],CPU_PROBE)
        self.assertEqual(f['vfprintf_whole_provenance']['observer'],capture.OBSERVER)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0];self.assertEqual(f['gdb_commands'],capture.commands(Path(directory)))
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            for call in c['printf_calls']:
                self.assertEqual(set(call),{'kind','before','after','children','formatter'});a=unpack_state(f,call['before']);info=a['format_inputs'];self.assertEqual(info['pthread_size'],1216)
                tls=info['static_tls'];self.assertEqual(tls['address']+tls['size'],a['tls_base']+1216)
                self.assertEqual(next(e['elf_sha256']for e in info['elf_data']if e['path'].endswith('/libc.so.6')),'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
                self.assertEqual(a['registers']['eip'],next(e['base']for e in info['elf_data']if e['path'].endswith('/libc.so.6'))+0x62110)
                boundary=call['formatter'];self.assertTrue(0<=boundary['children_start']<=boundary['children_end']<=len(call['children']))

    def test_every_whole_parent_and_produced_inner_state_stays_strict(self):
        f=self.fixture;report=run(f,shard=int(os.environ.get('PYASITIC_VFPRINTF_WHOLE_SHARD','1')),shards=int(os.environ.get('PYASITIC_VFPRINTF_WHOLE_SHARDS','1')))
        if target:=os.environ.get('PYASITIC_VFPRINTF_WHOLE_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        calls=[c for i in report['case_indices']for c in f['cases'][i]['printf_calls']]
        self.assertEqual(report['parent_calls_required'],len(calls));self.assertEqual(report['calls_checked'],len(calls));self.assertEqual(report['boundary_states_checked'],2*len(calls))
        self.assertEqual(report['registers_checked'],17*len(calls));self.assertEqual(report['boundary_registers_checked'],34*len(calls))
        self.assertEqual(report['children_checked'],sum(len(c['children'])for c in calls));self.assertEqual(report['child_registers_checked'],34*report['children_checked'])
        self.assertEqual(report['fp_bytes_checked'],sum(len(unpack_state(f,c['after'])['xstate'])//2 for c in calls))
        self.assertEqual(report['boundary_fp_bytes_checked'],sum(len(unpack_state(f,c['formatter'][p])['xstate'])//2 for c in calls for p in('before','after')))
        self.assertEqual(report['differences'],0,'Every parent, produced boundary, helper and kernel-owned word remains required')

    def test_one_parent_input_initializes_execution_and_boundaries_are_observed(self):
        original=audit.engine;seen=[]
        def track(f,state):seen.append(state['registers']);return original(f,state)
        with patch.object(audit,'engine',track):report=compare(self.fixture,self.one)
        self.assertEqual(seen,[unpack_state(self.fixture,self.one['printf_calls'][0]['before'])['registers']]);self.assertEqual(report['calls_checked'],1);self.assertEqual(report['boundary_states_checked'],2)

    def test_later_formatter_and_parent_state_never_supply_results(self):
        base=compare(self.fixture,self.one);c=copy.deepcopy(self.one);call=c['printf_calls'][0]
        before=copy.deepcopy(expand_state(self.fixture,call['formatter']['before']));after=copy.deepcopy(expand_state(self.fixture,call['formatter']['after']));last=copy.deepcopy(expand_state(self.fixture,call['after']))
        before['registers']['eax']^=1;after['registers']['edx']^=1;after['xstate']='00'+after['xstate'][2:];after['heap']['top']+=16;last['registers']['eax']^=1
        call['formatter']['before']=before;call['formatter']['after']=after;call['after']=last;call['children'][0]['after']['ecx']^=1
        changed=compare(self.fixture,c);self.assertEqual(changed['calls_checked'],1);self.assertEqual(changed['boundary_states_checked'],2)
        kinds=lambda r:collections.Counter((d['kind'],d.get('boundary'))for d in r['differences'])
        delta=kinds(changed)-kinds(base)
        for key in(('printf-register','formatter-before'),('printf-register','formatter-after'),('printf-fp-byte','formatter-after'),('state','formatter-after'),('printf-register',None),('printf-child-register',None)):self.assertEqual(delta[key],1,key)

    def test_actual_earlier_string_changes_whole_parent_output(self):
        a=expand_state(self.fixture,self.one['printf_calls'][0]['before']);m,storage=engine(self.fixture,a);r=a['registers'];s=r['esp'];args=m.u32(s+12);string=m.u32(args);m.write(string,b'NEW\0')
        result=storage.vfprintf(r);self.assertEqual(result['eax'],4);file=m.u32(s+4);end=m.u32(file+20);self.assertEqual(m.read(end-4,4),b'\nNEW')

    def test_missing_actual_parent_inputs_fail(self):
        call=next(c for c in self.case['printf_calls']if any(ch['kind']=='fp-l-buffer'for ch in c['children']));a=expand_state(self.fixture,call['before'])
        m,storage=engine(self.fixture,a);slot=(storage.tls+m.u32(storage.got+0x90))&0xffffffff;m.forget(slot,4)
        with self.assertRaises(UnknownMemory):storage.vfprintf(a['registers'])
        m,storage=engine(self.fixture,a);storage.xstate=None
        with self.assertRaisesRegex(NotImplementedError,'actual earlier CPU/FP'):storage.vfprintf(a['registers'])

    def test_missing_or_invalid_inner_targets_never_pass(self):
        c=copy.deepcopy(self.one);del c['printf_calls'][0]['formatter']['after'];report=compare(self.fixture,c);self.assertIn('vfprintf-whole-missing-boundary',[d['kind']for d in report['differences']])
        c=copy.deepcopy(self.one);c['printf_calls'][0]['formatter']['children_end']=-1
        with self.assertRaisesRegex(ValueError,'indices'):compare(self.fixture,c)


if __name__=='__main__':unittest.main()

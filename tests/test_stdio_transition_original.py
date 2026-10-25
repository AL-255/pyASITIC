"""Earlier stdio inputs on the full continuing simulation memory."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_stdio_transition_original as capture
import reasitic.command_transition as transition
from audit_command_transition_original import compare
from audit_loader_lookup_original import data
from reasitic.plt_fixup_storage import PltFixup
from reasitic.repl_storage import ReplStorage


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class StdioTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('stdio_transition_original.json.gz')
        cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_original_histories_earlier_streams_and_expanded_later_boundaries(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['stdio_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures/loader_transition_original.json.gz').read_bytes()).hexdigest(),p['parent_sha256'])
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(f['gdb_commands'],capture.loader.transition.commands(Path(directory),capture.OBSERVER))
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            inputs=c['transition_inputs'];ctx=inputs['stdio_context'];regions=inputs['loader_context']['regions']
            self.assertEqual(set(ctx['streams']),{'stdin','stdout','stderr'});self.assertEqual(ctx['sar31_af'],f['integer_cpu']['sar31_af'])
            self.assertEqual(set(ctx['registers']),{'eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ss','ds','es','fs','gs','orig_eax'})
            self.assertTrue(ctx['stdin_regular']);self.assertGreaterEqual(ctx['stdin_position'],0)
            self.assertLessEqual(ctx['stdin_position'],len(bytes.fromhex(inputs['stdin_stream']['file_data'])))
            if not int.from_bytes(bytes.fromhex(inputs['stdin_stream']['data'])[28:32],'little'):self.assertEqual(ctx['stdin_position'],0)
            self.assertLessEqual(set(inputs['environment']),allowed)
            owners=[(r['address'],r['size'])for r in ctx['regions']]
            for stream in ctx['streams'].values():
                for owner in ((stream['address'],152),(stream['lock'],12),(stream['vtable'],84)):self.assertIn(owner,owners)
            for r in ctx['regions']:
                original=next(v for v in regions if(v['address'],v['size'])==(r['address'],r['size']));data(f,original)
            for records in ([p['regions']for p in c['transition_points']]+[s['component_regions']for s in c['transition_states']]):
                self.assertEqual([(r['address'],len(r['data'])//2)for r in records[2:]],owners)
            for part in bytes.fromhex(inputs['initial_regions'][0]['data']).split(b'\0'):
                key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
            self.assertNotIn('poll_calls',c);self.assertNotIn('plt_calls',c)

    def test_full_generated_poll_select64_and_four_binding_register_sets(self):
        bindings=[];polls=[];wide=[];resolve=PltFixup.resolve;poll=transition.poll_select;adapter=transition.select64_entry
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        def entering(*args):polls.append(dict(args[1]));return poll(*args)
        def converted(*args,**kwargs):result=adapter(*args,**kwargs);wide.append(result);return result
        with patch.object(PltFixup,'resolve',binding),patch.object(transition,'poll_select',entering),patch.object(transition,'select64_entry',converted):report=compare(self.fixture,self.case)
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls']
        self.assertEqual(len(bindings),4)
        for actual,index in zip(bindings,(0,1,6,7)):self.assertEqual(actual,calls[index]['before']['registers'],index)
        native=next(c for c in load('poll_storage_original.json.gz')['cases']if c['poll_calls'])['poll_calls'][0]
        self.assertEqual(polls,[native['entry']['registers']]);self.assertEqual(wide,[native['select64']['registers']])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))
        w=self.case['transition_inputs']['workspace_address']
        self.assertTrue(report['differences'],'The unresolved continuing words must remain required failures')
        self.assertTrue(all(d['kind']in('transition-point-word','transition-component-word')and w<=d['address']<w+4460 for d in report['differences']))

    def test_later_static_stream_bytes_are_assertions_only(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'))
        self.assertEqual(compare(self.fixture,case)['differences'],[])
        lock=case['transition_inputs']['stdio_context']['streams']['stdout']['lock'];r=next(r for r in case['transition_points'][0]['regions']if r['address']==lock)
        raw=bytearray.fromhex(r['data']);raw[0]^=1;r['data']=raw.hex()
        result=compare(self.fixture,case)
        self.assertEqual([(d['kind'],d['address'])for d in result['differences']],[('transition-point-word',lock)])
        case['transition_points'][0]['regions'].pop()
        self.assertIn('transition-point-region-count',[d['kind']for d in compare(self.fixture,case)['differences']])

    def test_missing_earlier_lock_cannot_be_recovered_from_later_regions(self):
        case=copy.deepcopy(self.case);ctx=case['transition_inputs'];lock=ctx['stdio_context']['streams']['stdout']['lock']
        ctx['loader_context']['regions']=[r for r in ctx['loader_context']['regions']if r['address']!=lock]
        result=compare(self.fixture,case)
        self.assertTrue(any(d['kind']=='transition-runtime'and'Uninitialized guest memory'in d['reason']for d in result['differences']))

    def test_poll_register_pointer_follows_earlier_FILE_lock(self):
        before=ReplStorage.before_poll;seen=[]
        def changed(engine,parent,line):
            streams=engine.context['streams'];pointer=streams['stdin']['lock'];engine.m.put_u32(streams['stdout']['address']+72,pointer)
            result=before(engine,parent,line);seen.append((result['edx'],pointer));return result
        with patch.object(ReplStorage,'before_poll',changed):report=compare(self.fixture,self.case)
        self.assertEqual(len(seen),1);self.assertEqual(*seen[0]);self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))


if __name__=='__main__':unittest.main()

"""Source stdin/append stores and all eight native binding register sets."""
import collections,copy,gzip,hashlib,json,re,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_input_transition_original as capture
from audit_command_transition_original import compare
from audit_loader_lookup_original import data
from reasitic.command_transition import CommandTransition
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class InputTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('input_transition_original.json.gz')
        cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_histories_earlier_file_inputs_and_complete_added_regions(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['input_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/stdio_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(f['gdb_commands'],capture.stdio.loader.transition.commands(Path(directory),capture.OBSERVER))
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            inputs=c['transition_inputs'];ctx=inputs['stdio_context'];profile=ctx['input_abi'];stat=profile['stdin_stat']
            self.assertEqual(stat['st_mode']&0o170000,0o100000);self.assertEqual(stat['st_size'],len(bytes.fromhex(inputs['stdin_stream']['file_data'])))
            self.assertGreater(stat['st_blksize'],0);self.assertTrue(all(isinstance(value,int)for value in stat.values()))
            regions=inputs['loader_context']['regions'];owners=[(r['address'],r['size'])for r in ctx['regions']]
            self.assertEqual(len(owners),17);self.assertEqual(sum(size for _,size in owners),1884)
            self.assertIn((0x80b4800,160),owners);self.assertEqual(sum(size==1024 for _,size in owners),1)
            for owner in owners:data(f,next(r for r in regions if(r['address'],r['size'])==owner))
            for later in ([p['regions']for p in c['transition_points']]+[s['component_regions']for s in c['transition_states']]):
                self.assertEqual([(r['address'],len(r['data'])//2)for r in later[2:]],owners)
            for part in bytes.fromhex(inputs['initial_regions'][0]['data']).split(b'\0'):
                key=re.match(rb'^([A-Za-z_][A-Za-z0-9_]*)=',part)
                if key:self.assertIsNone(re.search(rb'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL',key.group(1),re.I))
            self.assertNotIn('plt_calls',c);self.assertNotIn('poll_calls',c)
        self.assertEqual(collections.Counter(c['signal']for c in f['cases']),{0:132,11:1,6:1})

    def test_all_eight_generated_complete_binding_register_sets_match_native(self):
        seen=[];resolve=PltFixup.resolve
        def binding(engine,registers):seen.append(dict(registers));return resolve(engine,registers)
        with patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,self.case)
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls']
        self.assertEqual(len(seen),8)
        for index,(actual,native)in enumerate(zip(seen,calls)):self.assertEqual(actual,native['before']['registers'],index)
        w=self.case['transition_inputs']['workspace_address'];self.assertTrue(report['differences'])
        self.assertEqual(report['unknown_bytes'],0)
        self.assertTrue(all(d['kind']in('transition-point-word','transition-component-word')and w<=d['address']<w+4460 for d in report['differences']))

    def test_later_main_input_buffer_is_an_assertion_not_a_seed(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'))
        self.assertEqual(compare(self.fixture,case)['differences'],[])
        owner=next(r for r in case['transition_inputs']['stdio_context']['regions']if r['size']==1024)
        later=next(r for r in case['transition_points'][0]['regions']if r['address']==owner['address']);raw=bytearray.fromhex(later['data']);raw[100]^=1;later['data']=raw.hex()
        report=compare(self.fixture,case)
        self.assertEqual([(d['kind'],d['address'])for d in report['differences']],[('transition-point-word',owner['address']+100)])
        case['transition_points'][0]['regions'].pop()
        self.assertIn('transition-point-region-count',[d['kind']for d in compare(self.fixture,case)['differences']])

    def test_missing_earlier_foreign_vtable_global_has_no_later_fallback(self):
        case=copy.deepcopy(self.case);regions=case['transition_inputs']['loader_context']['regions']
        libc=next(x for x in case['transition_inputs']['loader_context']['maps']if x['name'].endswith('/libc.so.6'))
        base=int.from_bytes(data(self.fixture,next(r for r in regions if r['address']==libc['address']))[:4],'little');slot=base+0x22fe34+0x1a30
        case['transition_inputs']['loader_context']['regions']=[r for r in regions if r['address']!=slot]
        report=compare(self.fixture,case)
        self.assertTrue(any(d['kind']=='transition-runtime'and'Uninitialized guest memory'in d['reason']for d in report['differences']))

    def test_buffer_request_and_read_binding_follow_earlier_file_stat(self):
        case=copy.deepcopy(self.case);case['transition_inputs']['stdio_context']['input_abi']['stdin_stat']['st_blksize']=8192
        allocations=[];bindings=[];allocate=CommandTransition.allocate;resolve=PltFixup.resolve
        def allocation(engine,name,size,allocator='malloc'):
            if name=='stdin.buffer':allocations.append(size)
            return allocate(engine,name,size,allocator)
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        with patch.object(CommandTransition,'allocate',allocation),patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,case)
        self.assertEqual(allocations,[8192]);self.assertEqual(len(bindings),8);self.assertEqual(bindings[4]['edx'],8192)
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))


if __name__=='__main__':unittest.main()

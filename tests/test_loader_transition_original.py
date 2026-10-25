"""Earlier loader context in the same continuing simulation Memory.

These integration tests do not replace the all-case strict continuation audit.
Unresolved stack words remain required failures there.
"""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_loader_transition_original as capture
from audit_command_transition_original import compare
from audit_loader_lookup_original import data
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class LoaderTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=load('loader_transition_original.json.gz')

    def test_every_original_job_earlier_context_and_full_boundary_are_retained(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        self.assertEqual(f['loader_transition_provenance']['observer'],capture.OBSERVER)
        for name,key in f['loader_transition_provenance']['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        directory=f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]
        self.assertEqual(f['gdb_commands'],capture.transition.commands(Path(directory),capture.OBSERVER))
        for c,job in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key])
            inputs=c['transition_inputs'];ctx=inputs['loader_context'];self.assertNotIn('plt_calls',c);self.assertNotIn('lookup_calls',c)
            self.assertEqual(len(ctx['maps']),19);self.assertTrue(any(x['address']==ctx['main_map']for x in ctx['maps']))
            stack=inputs['initial_regions'][0];self.assertTrue(all(r['address']!=stack['address']for r in ctx['regions']))
            for region in ctx['regions']:data(f,region)
            for state in c['transition_states']:
                self.assertEqual([len(r['data'])//2 for r in state['component_regions']],[4460,120])
                self.assertEqual([(r['address'],r['size'])for r in state['memory_regions']],[(m['start'],m['end']-m['start'])for m in state['maps']if m['path']=='[heap]'])

    def test_first_binding_registers_and_signal_mask_follow_earlier_source_state(self):
        case=next(c for c in self.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold');w=case['transition_inputs']['workspace_address'];observed=[];resolve=PltFixup.resolve
        def record(engine,registers):
            before=dict(registers);source=engine.m.u32(w+4180);result=resolve(engine,registers)
            observed.append((before,source,engine.m.u32(w+4180)));return result
        with patch.object(PltFixup,'resolve',record):report,heap,addresses,memory=compare(self.fixture,case,return_state=True)
        self.assertEqual(len(observed),3);registers,previous,current=observed[0]
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls']
        for source,index in zip(observed,(0,6,7)):
            native=calls[index]['before']['registers']
            for name,value in source[0].items():self.assertEqual(value,native[name],(index,name))
        self.assertEqual(previous,int.from_bytes(b'RECT','little'));self.assertEqual(current,1)
        self.assertEqual(memory.u32(w+3852),current)
        native_point=case['transition_points'][1]['regions'][0];self.assertEqual(bytes.fromhex(native_point['data'])[3852:3856],memory.read(w+3852,4))
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']))

    def test_later_boundary_bytes_are_assertions_only(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'))
        self.assertEqual(compare(self.fixture,case)['differences'],[])
        region=case['transition_points'][0]['regions'][0];raw=bytearray.fromhex(region['data']);raw[0]^=1;region['data']=raw.hex()
        result=compare(self.fixture,case);self.assertEqual([d['kind']for d in result['differences']],['transition-point-word'])

    def test_missing_earlier_loader_bytes_are_not_recovered_from_later_observations(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold'));ctx=case['transition_inputs']['loader_context']
        libc=next(x for x in ctx['maps']if x['name'].endswith('/libc.so.6'));regions=ctx['regions'];base=int.from_bytes(data(self.fixture,next(r for r in regions if r['address']==libc['address']))[:4],'little');address=base+0x22fe34+0xa0
        ctx['regions']=[r for r in regions if r['address']!=address]
        report=compare(self.fixture,case)
        self.assertTrue(any(d['kind']=='transition-runtime'and 'Uninitialized guest memory'in d['reason']for d in report['differences']))


if __name__=='__main__':unittest.main()

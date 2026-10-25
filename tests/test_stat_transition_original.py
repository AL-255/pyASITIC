"""Earlier statx facts on the same continuing allocator and memory."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_stat_transition_original as capture
from audit_command_transition_original import compare
from audit_loader_lookup_original import data
from reasitic.file_allocation import FileAllocation
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class StatTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('stat_transition_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_every_original_history_earlier_fact_and_full_target_remains(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['stat_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/input_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            ctx=c['transition_inputs']['stdio_context'];x=ctx['input_abi']['statx'];self.assertEqual(x['query_mask'],0x7ff);self.assertNotIn('raw',x)
            self.assertEqual(x['fields']['blksize'],ctx['input_abi']['stdin_stat']['st_blksize'])
            owners=[(r['address'],r['size'])for r in ctx['regions']];self.assertEqual(len(owners),19);self.assertEqual(sum(size for _,size in owners),1920)
            for later in ([p['regions']for p in c['transition_points']]+[s['component_regions']for s in c['transition_states']]):
                self.assertEqual([(r['address'],len(r['data'])//2)for r in later[2:]],owners)
            self.assertNotIn('allocation_calls',c)

    def test_generated_stat_caller_and_all_eight_binding_registers(self):
        seen=[];bindings=[];before=FileAllocation.before_malloc;resolve=PltFixup.resolve
        def stat(storage,registers):result=before(storage,registers);seen.append((dict(registers),result));return result
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        with patch.object(FileAllocation,'before_malloc',stat),patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,self.case)
        native=next(c for c in load('file_allocation_original.json.gz')['cases']if c['allocation_calls'])['allocation_calls'][0]
        self.assertEqual(seen,[(native['entry']['registers'],native['malloc']['registers'])])
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls'];self.assertEqual(bindings,[c['before']['registers']for c in calls])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences'])

    def test_later_vdso_assertions_are_not_earlier_inputs(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'))
        self.assertEqual(compare(self.fixture,case)['differences'],[])
        owner=next(r for r in case['transition_inputs']['stdio_context']['regions']if r['size']==32)
        r=next(r for r in case['transition_points'][0]['regions']if r['address']==owner['address']);raw=bytearray.fromhex(r['data']);raw[0]^=1;r['data']=raw.hex()
        self.assertEqual([(d['kind'],d['address'])for d in compare(self.fixture,case)['differences']],[('transition-point-word',owner['address'])])

    def test_missing_earlier_malloc_slot_is_not_recovered_from_later_regions(self):
        case=copy.deepcopy(self.case);ctx=case['transition_inputs']['loader_context'];libc=next(x for x in ctx['maps']if x['name'].endswith('/libc.so.6'))
        base=int.from_bytes(data(self.fixture,next(r for r in ctx['regions']if r['address']==libc['address']))[:4],'little');slot=base+0x22fe34+0x1c4
        ctx['regions']=[r for r in ctx['regions']if r['address']!=slot]
        self.assertTrue(any(d['kind']=='transition-runtime'and'Uninitialized guest memory'in d['reason']for d in compare(self.fixture,case)['differences']))

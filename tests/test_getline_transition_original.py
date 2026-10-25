"""Scalar getline callers on continuing state, with no per-call seeds."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_getline_transition_original as capture
from audit_command_transition_original import compare
from reasitic.getline_bytes import GetlineBytes
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class GetlineTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('getline_transition_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_histories_earlier_cpu_inputs_and_complete_targets(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['getline_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/read_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            ctx=c['transition_inputs']['stdio_context'];self.assertTrue(ctx['input_abi']['getline_bytes_abi']);self.assertEqual(ctx['input_abi']['shr1_af'],f['byte_cpu']['shr1_af'])
            owners=[(r['address'],r['size'])for r in ctx['regions']];self.assertEqual(len(owners),26);self.assertEqual(sum(size for _,size in owners),1942)
            for later in c['transition_points']+c['transition_states']:
                self.assertIn('stdin_position',later);regions=later.get('regions',later.get('component_regions'));self.assertEqual([(r['address'],len(r['data'])//2)for r in regions[2:]],owners)
            self.assertNotIn('byte_calls',c)

    def test_generated_search_copy_and_all_binding_registers(self):
        seen=[];bindings=[];search=GetlineBytes.memchr;copy_bytes=GetlineBytes.memcpy;resolve=PltFixup.resolve
        def operation(method,kind):
            def wrapped(storage,registers):
                result=method(storage,registers);seen.append((kind,dict(registers),result));return result
            return wrapped
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        with patch.object(GetlineBytes,'memchr',operation(search,'memchr')),patch.object(GetlineBytes,'memcpy',operation(copy_bytes,'memcpy')),patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,self.case)
        native=next(c for c in load('getline_bytes_original.json.gz')['cases']if c['label']==self.case['label']and c['cache_mode']=='cold')['byte_calls'];stdin=self.case['transition_inputs']['stdin_stream']['address'];calls=[c for c in native if c['before']['registers']['ebp']==stdin]
        self.assertEqual(seen,[(c['kind'],c['before']['registers'],c['after']['registers'])for c in calls]);self.assertEqual(len(seen),2)
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls'];self.assertEqual(bindings,[c['before']['registers']for c in calls])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences'])

    def test_later_memory_and_descriptor_positions_are_assertions(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'));self.assertEqual(compare(self.fixture,case)['differences'],[])
        point=case['transition_points'][0];point['stdin_position']+=1;region=point['regions'][0];raw=bytearray.fromhex(region['data']);raw[0]^=1;region['data']=raw.hex()
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['transition-point-stdin-position','transition-point-word'])

    def test_missing_earlier_cpu_behavior_does_not_use_native_return_flags(self):
        case=copy.deepcopy(self.case);del case['transition_inputs']['stdio_context']['input_abi']['shr1_af']
        self.assertTrue(any(d['kind']=='transition-runtime'and'earlier CPU'in d['reason']for d in compare(self.fixture,case)['differences']))


if __name__=='__main__':unittest.main()

"""Complete flush source on the continuing producer, with no call snapshots."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_flush_transition_original as capture
from audit_command_transition_original import compare
from audit_flush_storage_original import engine
from capture_command_transition_original import expand_case
from reasitic.flush_storage import FlushStorage
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class FlushTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('flush_transition_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_every_history_earlier_stream_binding_and_complete_later_target(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['flush_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER);self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/getline_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            ctx=c['transition_inputs']['stdio_context'];self.assertTrue(ctx['flush_abi']);owners=[(r['address'],r['size'])for r in ctx['regions']]
            self.assertEqual(len(owners),33);self.assertEqual(sum(size for _,size in owners),2362)
            for later in c['transition_points']+c['transition_states']:
                self.assertIn('stdin_position',later);regions=later.get('regions',later.get('component_regions'));self.assertEqual([(r['address'],len(r['data'])//2)for r in regions[2:]],owners)
            self.assertNotIn('flush_calls',c)

    def test_generated_flush_returns_writes_and_all_existing_binding_entries(self):
        seen=[];bindings=[];flush=FlushStorage.flush;resolve=PltFixup.resolve
        def wrapped(storage,registers):
            start=len(storage.writes);stream=storage.m.u32(registers['esp']+4);result=flush(storage,registers);seen.append((dict(registers),stream,dict(result),storage.writes[start:]));return result
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        with patch.object(FlushStorage,'flush',wrapped),patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,self.case)
        f=load('flush_storage_original.json.gz');native=next(c for c in f['cases']if c['label']==self.case['label']and c['cache_mode']=='cold')['flush_calls']
        # Independent captures have different timestamped log headers. Assert
        # every emitted byte against this continuing capture's complete later
        # heap, never against another run's date or against generated memory.
        # These target bytes are read only after compare() has finished.
        targets=expand_case(self.fixture,self.case)['transition_states'][0]['memory_regions']
        self.assertEqual(len(seen),4)
        for (before,stream,after,writes),call in zip(seen,native[-4:]):
            m,_=engine(f,call['before']);self.assertEqual(stream,m.u32(call['before']['registers']['esp']+4))
            # printf/poll volatile entry registers remain separate work. These
            # callee-saved/segment inputs, complete returns and every write are
            # required; independent mutation tests prove unused input values
            # cannot supply any missing child bytes or return register.
            for key in ('ebx','esi','edi','ebp','esp','eip','cs','ss','ds','es','fs','gs','orig_eax'):self.assertEqual(before[key],call['before']['registers'][key],key)
            expected=copy.deepcopy(call['writes'])
            for write in expected:
                region=next(r for r in targets if r['address']<=write['address']and write['address']+write['count']<=r['address']+len(r['data'])//2)
                offset=write['address']-region['address'];write['data']=bytes.fromhex(region['data'])[offset:offset+write['count']].hex()
            self.assertEqual(after,call['after']['registers']);self.assertEqual(writes,expected)
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls'];self.assertEqual(bindings,[c['before']['registers']for c in calls])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences'])

    def test_later_log_stream_targets_and_offsets_are_assertions(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'));self.assertEqual(compare(self.fixture,case)['differences'],[])
        point=case['transition_points'][0];point['stdin_position']+=1;owner=next(r for r in case['transition_inputs']['stdio_context']['regions']if r['address']==0x80d7e24);region=next(r for r in point['regions']if r['address']==owner['address']);raw=bytearray.fromhex(region['data']);raw[0]^=1;region['data']=raw.hex()
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['transition-point-stdin-position','transition-point-word'])

    def test_missing_earlier_modern_vtable_does_not_use_later_copies(self):
        case=copy.deepcopy(self.case);ctx=case['transition_inputs']['loader_context'];owners=case['transition_inputs']['stdio_context']['regions'];vt=next(r for r in owners[26:]if r['size']==84)
        ctx['regions']=[r for r in ctx['regions']if r['address']!=vt['address']]
        self.assertTrue(any(d['kind']=='transition-runtime'and'Uninitialized guest memory'in d['reason']for d in compare(self.fixture,case)['differences']))


if __name__=='__main__':unittest.main()

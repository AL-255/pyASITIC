"""Read syscall callers and descriptor offsets on continuing process state."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_read_transition_original as capture
from audit_command_transition_original import compare
from reasitic.read_storage import ReadStorage
from reasitic.plt_fixup_storage import PltFixup


def load(name):return json.loads(gzip.decompress((ROOT/'tests/fixtures'/name).read_bytes()))


class ReadTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('read_transition_original.json.gz');cls.case=next(c for c in cls.fixture['cases']if c['label']=='prelude/fft/16/8'and c['cache_mode']=='cold')

    def test_all_histories_earlier_offsets_and_complete_later_targets(self):
        f=self.fixture;jobs=list(capture.jobs());self.assertEqual(len(f['cases']),134);self.assertEqual(len(jobs),67)
        p=f['read_transition_provenance'];self.assertEqual(p['observer'],capture.OBSERVER)
        self.assertEqual(p['parent_sha256'],hashlib.sha256((ROOT/'tests/fixtures/malloc_transition_original.json.gz').read_bytes()).hexdigest())
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        for c,j in zip(f['cases'],(j for j in jobs for _ in range(2))):
            for key in ('label','request','script','stdin','variant'):self.assertEqual(c[key],j[key])
            inputs=c['transition_inputs'];ctx=inputs['stdio_context'];self.assertTrue(ctx['input_abi']['read_abi'])
            start=inputs['stdin_stream']['file_position'];length=len(bytes.fromhex(inputs['stdin_stream']['file_data']))
            self.assertIsInstance(start,int);self.assertGreaterEqual(start,0);self.assertLessEqual(start,length)
            owners=[(r['address'],r['size'])for r in ctx['regions']];self.assertEqual(len(owners),26);self.assertEqual(sum(size for _,size in owners),1942)
            for later in c['transition_points']+c['transition_states']:
                self.assertIsInstance(later['stdin_position'],int);self.assertGreaterEqual(later['stdin_position'],start);self.assertLessEqual(later['stdin_position'],length)
                regions=later.get('regions',later.get('component_regions'))
                self.assertEqual([(r['address'],len(r['data'])//2)for r in regions[2:]],owners)
            self.assertNotIn('read_calls',c)

    def test_generated_read_entry_return_offset_and_all_binding_registers(self):
        seen=[];bindings=[];read=ReadStorage.read;resolve=PltFixup.resolve
        def operation(storage,registers,data,position):
            result=read(storage,registers,data,position);seen.append((dict(registers),position,result));return result
        def binding(engine,registers):bindings.append(dict(registers));return resolve(engine,registers)
        with patch.object(ReadStorage,'read',operation),patch.object(PltFixup,'resolve',binding):report=compare(self.fixture,self.case)
        native=next(c for c in load('read_storage_original.json.gz')['cases']if c['read_calls'])['read_calls'][0]
        self.assertEqual(len(seen),1);a,position,result=seen[0]
        self.assertEqual(a,native['before']['registers']);self.assertEqual(result['registers'],native['after']['registers'])
        self.assertEqual(position,native['before']['external_stdin']['position']);self.assertEqual(result['position'],native['after']['position'])
        calls=next(c for c in load('plt_fixup_original.json.gz')['cases']if c['plt_calls'])['plt_calls'];self.assertEqual(bindings,[c['before']['registers']for c in calls])
        self.assertFalse(any(d['kind']=='transition-runtime'for d in report['differences']));self.assertTrue(report['differences']);self.assertEqual(report['stdin_positions_checked'],3)

    def test_later_point_and_final_descriptor_positions_are_assertions(self):
        case=copy.deepcopy(next(c for c in self.fixture['cases']if c['label']=='prelude/fft/8/8'and c['cache_mode']=='cold'))
        self.assertEqual(compare(self.fixture,case)['differences'],[])
        case['transition_points'][0]['stdin_position']+=1;case['transition_states'][-1]['stdin_position']+=1
        self.assertEqual([d['kind']for d in compare(self.fixture,case)['differences']],['transition-point-stdin-position','transition-final-stdin-position'])

    def test_missing_earlier_descriptor_position_is_not_a_later_result(self):
        case=copy.deepcopy(self.case);del case['transition_inputs']['stdin_stream']['file_position']
        self.assertTrue(any(d['kind']=='transition-runtime'and'earlier descriptor position'in d['reason']for d in compare(self.fixture,case)['differences']))


if __name__=='__main__':unittest.main()

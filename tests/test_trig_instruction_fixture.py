"""Native trig evidence integrity; this does not assert instruction parity."""
import collections,gzip,hashlib,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_trig_instructions_native as capture


class NativeTrigInstructionFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/trig_instructions_native.json.gz').read_bytes()))

    def test_all_independent_inputs_and_driver_provenance(self):
        f=self.fixture;self.assertEqual(f['source'],capture.SOURCE);self.assertEqual(hashlib.sha256(f['source'].encode()).hexdigest(),f['source_sha256'])
        self.assertEqual((f['control_before'],f['control_after']),(0x37f,0x37f));self.assertEqual(len(f['cases']),11669)
        independent=list(capture.independent_cases());self.assertEqual(len(independent),11664)
        self.assertEqual([{k:row[k]for k in('label','operation','input_words')}for row in f['cases'][:11664]],independent)
        for row in f['cases']:
            self.assertIn(row['operation'],(0,1));self.assertEqual(len(row['input_words']),1)
            for value in [*row['input_words'],row['output_words']]:self.assertEqual(len(bytes.fromhex(value)),10)
        for key in('compiler','libc_sha256','loader_sha256','compile_flags','cpu'):self.assertTrue(f[key])

    def test_every_selected_original_instruction_is_preserved(self):
        f=self.fixture;parents={};expected=[]
        for name,digest in f['parents'].items():
            data=(ROOT/'tests/fixtures'/name).read_bytes();self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
            parent=json.loads(gzip.decompress(data)if name.endswith('.gz')else data);parents[name]=parent
            for ci,c in enumerate(parent['cases']):
                for ei,e in enumerate(c['events']):
                    for mi,op in enumerate(e.get('math',[])):
                        if op['operation']in('fcos','fsin'):expected.append([name,ci,ei,mi])
        anchors=f['cases'][11664:];self.assertEqual(len(anchors),f['original_anchor_count']);self.assertEqual(len(anchors),5)
        self.assertEqual([row['parent']for row in anchors],expected)
        for row in anchors:
            name,ci,ei,mi=row['parent'];source=parents[name]['cases'][ci]['events'][ei]['math'][mi]
            self.assertEqual(row['operation'],int(source['operation']=='fsin'));self.assertEqual(row['input_words'],source['input_words'])
            self.assertEqual(row['output_words'],source['output_words']);self.assertEqual(row['output_words'],row['original_output_words'])

    def test_operand_classes_and_unchanged_out_of_range_results(self):
        counts=collections.Counter(row['label']for row in self.fixture['cases'])
        self.assertEqual(counts,{
            'ordinary-binary64':4096,'ordinary-extended':2048,'extended-angle-neighbors':2112,
            'binary64-angle-neighbors':2048,'tiny-extended':1024,'wide-argument':320,
            'zero':8,'out-of-range':8,'actual-original-command':5})
        zero_count=0
        for row in self.fixture['cases']:
            if row['label']=='out-of-range':self.assertEqual(row['output_words'],row['input_words'][0])
            sig,exponent=struct.unpack('<QH',bytes.fromhex(row['input_words'][0]))
            if not sig:
                zero_count+=1;self.assertEqual(row['output_words'],row['input_words'][0]if row['operation']else capture.double(1.))
        self.assertEqual(zero_count,4)

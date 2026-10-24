"""Integrity of native-instruction evidence, not a claim of logarithm parity."""
import gzip,hashlib,importlib.util,json,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class NativeLogInstructionFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/log_instructions_native.json.gz').read_bytes()))

    def test_complete_independent_requests_and_driver_provenance(self):
        f=self.fixture;path=ROOT/'tools/capture_log_instructions_native.py';spec=importlib.util.spec_from_file_location('log_capture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(f['source'],module.SOURCE);self.assertEqual(hashlib.sha256(f['source'].encode()).hexdigest(),f['source_sha256'])
        self.assertEqual((f['control_before'],f['control_after']),(0x37f,0x37f));self.assertEqual(len(f['cases']),8182)
        independent=list(module.independent_cases());self.assertEqual(len(independent),8115)
        self.assertEqual([{k:r[k]for k in('label','operation','input_words')}for r in f['cases'][:8115]],independent)
        for row in f['cases']:
            self.assertIn(row['operation'],(0,1));self.assertEqual(len(row['input_words']),2)
            for value in [*row['input_words'],row['output_words']]:self.assertEqual(len(bytes.fromhex(value)),10)
        for key in('compiler','libc_sha256','loader_sha256','cpu'):self.assertTrue(f[key])

    def test_every_original_command_instruction_is_retained(self):
        f=self.fixture;parents={}
        for name,digest in f['parents'].items():
            path=ROOT/'tests/fixtures'/name;self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest);parents[name]=json.loads(path.read_text())
        expected=[]
        for name,parent in parents.items():
            for ci,c in enumerate(parent['cases']):
                for ei,e in enumerate(c['events']):
                    for mi,op in enumerate(e.get('math',[])):
                        if op['operation']in('fyl2x','fyl2xp1'):expected.append([name,ci,ei,mi])
        captured=f['cases'][8115:];self.assertEqual(len(captured),67);self.assertEqual([c['parent']for c in captured],expected)
        for row in captured:
            name,ci,ei,mi=row['parent'];op=parents[name]['cases'][ci]['events'][ei]['math'][mi]
            self.assertEqual(row['input_words'],op['input_words']);self.assertEqual(row['output_words'],op['output_words']);self.assertEqual(row['output_words'],row['original_output_words'])

    def test_multiplier_requests_and_native_width_evidence(self):
        f=json.loads(gzip.decompress((ROOT/'tests/fixtures/log_multipliers_native.json.gz').read_bytes()))
        path=ROOT/'tools/capture_log_instructions_native.py';spec=importlib.util.spec_from_file_location('multiplier_capture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(f['suite'],'multipliers');self.assertEqual(f['source'],module.SOURCE);self.assertEqual(hashlib.sha256(f['source'].encode()).hexdigest(),f['source_sha256'])
        self.assertEqual((f['control_before'],f['control_after']),(0x37f,0x37f));self.assertEqual(len(f['cases']),10327)
        requests=list(module.multiplier_cases());self.assertEqual(len(requests),10260)
        self.assertEqual([{k:r[k]for k in('label','group','operation','input_words')}for r in f['cases'][:10260]],requests)
        self.assertEqual(f['parents'],self.fixture['parents']);self.assertEqual(f['cases'][10260:],self.fixture['cases'][8115:])
        for key in('cpu','compiler','libc_sha256','loader_sha256','compile_flags'):self.assertEqual(f[key],self.fixture[key])
        for row in f['cases']:
            for value in [*row['input_words'],row['output_words']]:self.assertEqual(len(bytes.fromhex(value)),10)
        path=ROOT/'tools/audit_log_multiplier_width.py';spec=importlib.util.spec_from_file_location('multiplier_audit',path);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
        groups=audit.infer(f['cases']);self.assertEqual(len(groups),10)
        self.assertTrue(all(g['intersection_nonempty']and g['lattices'][68]['count']==1 for g in groups))
        self.assertEqual(sum(g['lattices'][67]['count']==0 for g in groups),6)

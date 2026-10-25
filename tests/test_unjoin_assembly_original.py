"""Every original UNJOIN upper entry remains a strict numerical assertion."""
import ast,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_unjoin_assembly_original as capture
import capture_unjoin_mutual_traces_original as trace_capture
from audit_unjoin_assembly_original import compare,compare_traces,compare_model,run


class UnjoinAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/unjoin_assembly_original.json.gz').read_bytes()))
        cls.traces=json.loads(gzip.decompress((ROOT/'tests/fixtures/unjoin_mutual_traces_original.json.gz').read_bytes()))
        models=json.loads(gzip.decompress((ROOT/'tests/fixtures/unjoin_sessions_original.json.gz').read_bytes()))
        cls.model=next(c for c in models['cases']if c['label']==trace_capture.LABEL)

    def test_unchanged_cohort_provenance_and_complete_defined_upper(self):
        f=self.fixture;self.assertEqual(f['gdb_commands'],capture.COMMANDS)
        parents={}
        for name,digest in f['parents'].items():
            raw=(ROOT/'tests/fixtures'/name).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest);parents[name]=json.loads(gzip.decompress(raw))
        sessions=parents['unjoin_sessions_original.json.gz']['cases'];plain=parents['unjoin_plain_outcomes_original.json.gz']['cases']
        self.assertEqual([c['label']for c in f['cases']],[c['label']for c in sessions]);self.assertEqual(len(sessions),8);self.assertEqual(len(plain),9)
        self.assertEqual({c['label']for c in f['cases']},{c['label']for c in plain if c['produced_model']})
        entries=0
        for c,p in zip(f['cases'],sessions):
            for key in('request','script','stdin'):self.assertEqual(c[key],p[key])
            self.assertEqual((c['control_before'],c['control_after']),(0x37f,0x37f));self.assertEqual(len(c['records']),c['n'])
            size=c['n']*(c['n']+1)//2;self.assertEqual(len(bytes.fromhex(c['upper_bits'])),16*size);entries+=size
            self.assertLessEqual(set(c['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
            for r in c['records']:self.assertEqual(len(bytes.fromhex(r['wire_bits'])),64);self.assertEqual(len(bytes.fromhex(r['input']['segment'])),240)
        self.assertEqual(entries,1685)

    def test_every_original_upper_entry(self):
        report=run(self.fixture);self.assertEqual(report['cases'],8);self.assertEqual(report['upper_entries_checked'],1685)
        self.assertEqual(report['differences'],0,report)

    def test_changed_later_target_and_missing_upper_are_detected(self):
        c=copy.deepcopy(self.fixture['cases'][0]);self.assertEqual(compare(c)['differences'],[])
        raw=bytearray.fromhex(c['upper_bits']);raw[0]^=1;c['upper_bits']=raw.hex();self.assertEqual(len(compare(c)['differences']),1)
        c['upper_bits']=c['upper_bits'][:-2]
        with self.assertRaisesRegex(ValueError,'Incomplete native upper matrix'):compare(c)

    def test_earlier_frequency_changes_output_without_target_substitution(self):
        c=copy.deepcopy(self.fixture['cases'][0]);c['frequency']*=2
        self.assertTrue(compare(c)['differences'])

    def test_actual_trace_arguments_and_provenance(self):
        f=self.traces;assembly={c['label']:c for c in self.fixture['cases']}
        self.assertEqual([(c['first'],c['second'])for c in f['cases']],[(9,42),(9,45)])
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        for c in f['cases']:
            a=assembly[c['label']];self.assertEqual(c['input_bits'],a['records'][c['first']]['wire_bits']+a['records'][c['second']]['wire_bits']);self.assertEqual((c['control_before'],c['control_after']),(0x37f,0x37f))
            self.assertEqual((c['script'],c['stdin']),(a['script'],a['stdin']))
            self.assertEqual(c['ordinal'],sum(a['n']-1-i for i in range(c['first']))+c['second']-c['first']-1)
            points=ast.literal_eval(c['gdb_commands'].split('math_points=',1)[1].splitlines()[0])
            self.assertEqual({hex(k):json.loads(json.dumps(v))for k,v in points.items()},f['math_instruction_points'])
            self.assertEqual(c['gdb_commands'],trace_capture.commands(c['ordinal'],points))
            for event in c['events']:
                self.assertEqual((event['control_before'],event['control_after']),(0x37f,0x37f))
                for op in event.get('math',[]):
                    self.assertEqual(len(bytes.fromhex(op['output_words'])),10)
                    for value in op['input_words']:self.assertEqual(len(bytes.fromhex(value)),10)

    def test_every_original_helper_and_instruction(self):
        report=compare_traces(self.traces);self.assertEqual(report['cases'],2);self.assertEqual(sum(report['counts'].values()),30)
        self.assertEqual(report['differences'],[],report)

    def test_complete_production_coupled_model_and_inputs(self):
        assembly=next(c for c in self.fixture['cases']if c['label']==self.model['label']);report=compare_model(self.model,assembly)
        for key,count in(('assembly-calls',1),('filament-count',1),('filament-input',47),('filament-material',47),('production-upper',1128),('capacitance_matrix',4418),('inductive_admittance_matrix',4418),('model',23),('scattering',8)):self.assertEqual(report['counts'][key],count)
        self.assertEqual(report['differences'],[],report)


if __name__=='__main__':unittest.main()

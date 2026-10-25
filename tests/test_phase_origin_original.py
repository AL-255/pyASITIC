"""Earlier loader stores, later capacitor phase and immutable native targets."""
import copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_phase_origin_original as capture
from audit_phase_origin_original import compare,run
from audit_loader_lookup_original import memory_for
from reasitic.plt_fixup_storage import PltFixup


class PhaseOriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/phase_origin_original.json.gz').read_bytes()))

    def test_all_plain_scripts_observers_inputs_and_native_phase_provenance(self):
        f=self.fixture;self.assertEqual(len(f['cases']),4);self.assertEqual(f['observer'],capture.OBSERVER)
        debug=Path(f['gdb_commands'].split('set debug-file-directory ',1)[1].splitlines()[0]);self.assertEqual(f['gdb_commands'],capture.commands(debug))
        self.assertEqual(f['original_sha256'],'72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f')
        self.assertEqual(f['libc_sha256'],'e936bd40e5479b27721efeade1b502623436a8be2bd8bd0f0ccf8c4f7229a0d0')
        self.assertEqual(f['loader_sha256'],'64f2864e740bf9cc15c01466c438d6ba25c7bc9cf9401d8122287ee7ed05e26d')
        for name,key in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),key)
        allowed={'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'}
        for c,job in zip(f['cases'],capture.jobs()):
            for key in('label','parameters','stdin'):self.assertEqual(c[key],job[key])
            self.assertEqual(c['script'],job['script']+'WHO\n');self.assertEqual(c['plain']['returncode'],0);self.assertEqual(c['plt_pending'],0)
            context,final=c['phase_context'],c['final_context'];self.assertEqual((context['control'],final['control']),(0x37f,0x37f))
            self.assertEqual(context['write_count'],0);self.assertEqual(final['write_count'],len(c['phase_writes']))
            self.assertEqual(len(c['plt_calls']),1)
            for a in(context,final,c['plt_calls'][0]['before']):
                self.assertLessEqual(set(a['environment']),allowed)
                for key,value in f['environment_overrides'].items():self.assertEqual(a['environment'][key],value)

    def test_every_native_target_word_register_fp_byte_and_later_phase_matches(self):
        report=run(self.fixture);self.assertEqual(report['differences'],0,json.dumps(report,indent=2))
        self.assertEqual((report['calls_checked'],report['words_checked'],report['registers_checked'],report['fp_bytes_checked'],report['phase_words_checked']),(4,666424,68,9760,16))

    def test_later_phase_values_do_not_seed_or_repair_the_source_stack(self):
        c=copy.deepcopy(self.fixture['cases'][0]);a=c['plt_calls'][0]['before'];memory=memory_for(self.fixture,a);slot=a['registers']['esp']-140
        initial=memory.u32(slot);engine=PltFixup(memory,a['loader_base'],tls_base=a['tls_base']);engine.resolve(a['registers']);produced=memory.u32(slot)
        self.assertNotEqual(initial,produced)
        c['phase_context']['phase']^=1;c['final_context']['phase']^=1
        differences=compare(self.fixture,c)['differences'];self.assertEqual([d['kind']for d in differences],['phase-constructor','phase-descriptor'])
        self.assertEqual(memory.u32(slot),produced)


if __name__=='__main__':unittest.main()

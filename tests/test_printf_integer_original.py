"""Independent native int32 text outputs supplement all ASITIC state targets."""
import copy,gc,gzip,hashlib,json,os,sys,unittest,weakref
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from capture_printf_integer_original import PROBE,LIBC_SHA256,requests
from audit_printf_integer_original import Inputs,run
import audit_printf_integer_original as audit
from printf_archive import read_fixture
from reasitic.memory import UnknownMemory


class PrintfIntegerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=read_fixture(ROOT/'tests/fixtures/printf_format_original.manifest.json')
        cls.probe=json.loads(gzip.decompress((ROOT/'tests/fixtures/printf_integer_original.json.gz').read_bytes()));cls.inputs=Inputs(cls.fixture)

    def test_original_probe_provenance_and_every_request(self):
        p=self.probe;self.assertEqual(p['libc_sha256'],LIBC_SHA256);self.assertEqual(p['libc_sha256'],self.inputs.libc_sha256)
        self.assertEqual(p['probe'],PROBE);self.assertEqual([{k:c[k]for k in ('format','value')}for c in p['cases']],requests());self.assertEqual(len(p['cases']),5472)
        raw=''.join(c['format']+'\t'+format(c['value'],'x')+'\n'for c in requests());self.assertEqual(p['stdin_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(set(p['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH'})
        for flag in ('-m32','-nostdlib','-no-pie','-Wl,-e,_start'):self.assertIn(flag,p['compile_command'])

    def test_every_independent_native_int32_output(self):
        report=run(self.fixture,self.probe)
        if target:=os.environ.get('PYASITIC_PRINTF_INTEGER_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report['cases_required'],5472);self.assertEqual(report['cases_checked'],5472);self.assertEqual(report['differences'],[])

    def test_changed_requests_do_not_use_original_text(self):
        request=dict(self.probe['cases'][0],value=123,original=b'not used'.hex());self.assertEqual(self.inputs.format(request),b'P:123:S')

    def test_digit_output_depends_on_actual_earlier_table_bytes(self):
        inputs=copy.copy(self.inputs);inputs.sections=list(inputs.sections);digit=inputs.libc+0x22fe34-0x68454+7
        for i,(address,raw)in enumerate(inputs.sections):
            if address<=digit<address+len(raw):
                offset=digit-address;inputs.sections[i]=(address,raw[:offset]+b'Z'+raw[offset+1:]);break
        else:self.fail('Earlier native digit table is missing')
        self.assertEqual(inputs.format(dict(format='P:%d:S',value=7)),b'P:Z:S')

    def test_missing_earlier_table_and_foreign_probe_fail(self):
        inputs=copy.copy(self.inputs);inputs.sections=[s for s in inputs.sections if s[0]!=inputs.libc+0x1a9000]
        with self.assertRaises(UnknownMemory):inputs.format(dict(format='%d',value=7))
        probe=dict(self.probe,libc_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'different libc'):run(self.fixture,probe)

    def test_later_target_changes_remain_required(self):
        probe=copy.deepcopy(self.probe);probe['cases'][0]['original']=b'WRONG'.hex();report=run(self.fixture,probe)
        self.assertEqual(report['cases_checked'],5472);self.assertEqual(len(report['differences']),1);self.assertEqual(report['differences'][0]['case'],0);self.assertEqual(report['differences'][0]['kind'],'text')

    def test_request_memory_is_released_without_cyclic_collection(self):
        constructor=audit.PrintfFormat;references=[]
        def track(*args,**kwargs):
            f=constructor(*args,**kwargs);references.extend((weakref.ref(f),weakref.ref(f.m)));return f
        enabled=gc.isenabled();gc.disable()
        try:
            with patch.object(audit,'PrintfFormat',track):
                for value in (0,1,7,0x80000000,0xffffffff):self.inputs.format(dict(format='%d',value=value))
            self.assertTrue(all(r()is None for r in references),'Formatter helpers must not retain entire request memories')
        finally:
            if enabled:gc.enable()


if __name__=='__main__':unittest.main()

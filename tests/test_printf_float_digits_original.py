"""Native decimal text and mantissa probes; full formatter gates stay required."""
import gzip,hashlib,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from capture_printf_float_digits_original import PROBE,requests
from capture_printf_integer_original import LIBC_SHA256
from audit_printf_float_digits_original import run
from reasitic.printf_float_digits import format_binary64,extract_double


class PrintfFloatDigitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe=json.loads(gzip.decompress((ROOT/'tests/fixtures/printf_float_digits_original.json.gz').read_bytes()))

    def test_probe_provenance_and_every_declared_request(self):
        p=self.probe;self.assertEqual(p['libc_sha256'],LIBC_SHA256);self.assertEqual(p['probe'],PROBE)
        self.assertEqual([{k:v for k,v in c.items()if k not in('original','extraction')}for c in p['cases']],requests())
        self.assertEqual(len(p['cases']),73360);self.assertEqual(p['extract_double_offset'],0x51ed0);self.assertEqual(p['tzcnt_zero'],32)
        raw=''.join(c['format']+'\t'+format(c['word']>>32,'x')+' '+format(c['word']&0xffffffff,'x')+' '+str(c['rounding'])+'\n'for c in requests())
        self.assertEqual(p['stdin_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(set(p['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH'})
        for flag in('-m32','-nostdlib','-no-pie','-Wl,-e,_start'):self.assertIn(flag,p['compile_command'])
        self.assertEqual({(c['word']>>52)&2047 for c in p['cases']},set(range(2048)))
        self.assertEqual({c['rounding']for c in p['cases']},set(range(4)))
        self.assertEqual({c['spec']for c in p['cases']},set('eEfFgG'))
        self.assertEqual(max(c['precision']for c in p['cases']),1074);self.assertEqual(max(c['width']for c in p['cases']),4096)

    def test_every_independent_native_output_and_extraction(self):
        report=run(self.probe)
        if target:=os.environ.get('PYASITIC_PRINTF_FLOAT_DIGITS_REPORT'):Path(target).write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(report,dict(cases_required=73360,cases_checked=73360,extractions_checked=70281,differences=[]))

    def test_changed_inputs_and_rounding_are_computed(self):
        word=0x4004000000000000 # 2.5: exactly halfway at zero fractional precision.
        self.assertEqual(format_binary64(word,'f',0),b'2')
        self.assertEqual(format_binary64(word+1,'f',0),b'3')
        self.assertEqual(format_binary64(word,'f',0,rounding=2),b'3')
        self.assertEqual(format_binary64(word|(1<<63),'f',0,rounding=1),b'-3')
        self.assertEqual(format_binary64(word,'f',0,8,'0+'),b'+0000002')
        self.assertEqual(format_binary64(1<<63,'g'),b'-0')

    def test_changed_text_and_extraction_targets_remain_required(self):
        p=dict(self.probe,cases=list(self.probe['cases']))
        p['cases'][0]=dict(p['cases'][0],original=b'WRONG'.hex())
        p['cases'][1]=dict(p['cases'][1],extraction=dict(p['cases'][1]['extraction'],limbs=[0,0,0,0]))
        report=run(p);self.assertEqual(report['cases_checked'],73360);self.assertEqual(report['extractions_checked'],70281)
        self.assertEqual([(d['case'],d['kind'])for d in report['differences']],[(0,'text'),(1,'extraction')])

    def test_foreign_native_contract_is_rejected(self):
        for key,value,message in(('libc_sha256','0'*64,'different libc'),('tzcnt_zero',0,'TZCNT'),('extract_double_offset',0,'different extraction')):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,message):run(dict(self.probe,**{key:value}))

    def test_unsupported_inputs_do_not_silently_use_host_formatting(self):
        for word in(-1,1<<64,True,1.5):
            with self.assertRaisesRegex(ValueError,'binary64 bits'):format_binary64(word)
        for field in(dict(spec='a'),dict(flags="'")):
            with self.assertRaises(NotImplementedError):format_binary64(0,**field)
        for field in(dict(precision=1<<31),dict(width=True)):
            with self.assertRaisesRegex(ValueError,'int32'):format_binary64(0,**field)
        with self.assertRaisesRegex(ValueError,'Nonfinite'):extract_double(0x7ff0000000000000)


if __name__=='__main__':unittest.main()

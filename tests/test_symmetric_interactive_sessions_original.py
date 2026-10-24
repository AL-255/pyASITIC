"""Full original interactive models and captured invalid-contact histories."""
from fractions import Fraction
import hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic.bridge import handle,request_json
from reasitic.network_metrics import PI_KEYS,probe


class OriginalSymmetricInteractiveSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'symmetric_interactive_sessions_original.json').read_text())
        assert hashlib.sha256((root/'symmetric_interactive_original.json').read_bytes()).hexdigest()==cls.fixture['parent_sha256']
        assert len(cls.fixture['cases'])==6

    def test_every_finite_original_output(self):
        for index in(0,2,3):
            c=self.fixture['cases'][index]
            with self.subTest(case=index):
                before=repr(c);r=handle(c['request']);y=r['admittance_matrix']
                self.assertEqual([struct.pack('<d',v).hex()for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],c['model']['Y']);self.assertEqual(c['model']['Y'],c['scattering']['Y'])
                self.assertEqual([struct.pack('<d',v).hex()for v in[r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]]],c['model']['M'])
                self.assertEqual([struct.pack('<d',v).hex()for row in r['scattering_matrix']for z in row for v in z],c['scattering']['S'])
                sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
                expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
                self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected));self.assertEqual(repr(c),before)

    def test_original_nonfinite_contact_histories(self):
        for index in(1,4,5):
            c=self.fixture['cases'][index]
            with self.subTest(case=index):
                self.assertEqual(c['plain_returncode'],0);self.assertIn('nan',c['plain_stdout'].lower());self.assertEqual(c['model']['Y'],c['scattering']['Y'])
                values=[struct.unpack('<d',bytes.fromhex(v))[0]for v in c['model']['Y']];self.assertTrue(all(math.isnan(v)for v in values))
                row=[0.,struct.unpack('<d',bytes.fromhex(c['model']['M'][0]))[0],1.,0.,50.,0.,*values,*([0.]*12)];output=probe([row])[0]
                for actual,bits in zip([*output[1:13],*output[21:29]],[*c['model']['M'],*c['scattering']['S']]):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',actual).hex(),bits)
                    else:self.assertTrue(math.isnan(actual))
                contact=c['contact_capture'];self.assertTrue(contact['success']);self.assertEqual(contact['control_before'],0x37f);self.assertEqual(contact['control_after'],0x37f)
                invalid=[a['indices']for r in contact['records']for a in r['contacts']if not(0<=a['indices'][0]<a['indices'][1]<=128 and 0<=a['indices'][2]<a['indices'][3]<=128)]
                self.assertTrue(invalid);self.assertTrue(all(a[0]==a[1]or a[2]==a[3]for a in invalid))
                with self.assertRaisesRegex(ValueError,'contact collapses'):handle(c['request'])
                self.assertIn('contact collapses',json.loads(request_json(json.dumps(c['request'])))['error'])

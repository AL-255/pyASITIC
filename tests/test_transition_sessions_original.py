"""Original finite electrical outputs and retained nonfinite gap histories."""
from fractions import Fraction
import hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic.bridge import handle,request_json
from reasitic.network_metrics import PI_KEYS,probe


class OriginalTransitionSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'transition_sessions_original.json').read_text())
        assert hashlib.sha256((root/'transition_original.json').read_bytes()).hexdigest()==cls.fixture['parent_sha256']
        assert len(cls.fixture['cases'])==6

    def check_finite(self,index):
        c=self.fixture['cases'][index];before=repr(c);r=handle(c['request']);y=r['admittance_matrix']
        self.assertEqual([struct.pack('<d',v).hex()for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],c['model']['Y'])
        self.assertEqual(c['model']['Y'],c['scattering']['Y'])
        self.assertEqual([struct.pack('<d',v).hex()for v in[r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]]],c['model']['M'])
        self.assertEqual([struct.pack('<d',v).hex()for row in r['scattering_matrix']for z in row for v in z],c['scattering']['S'])
        sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
        expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
        self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected));self.assertEqual(repr(c),before)

    def test_omitted_polygon_complete_model(self):self.check_finite(3)
    def test_negative_polygon_complete_model(self):self.check_finite(5)

    def test_original_nonfinite_histories_and_bounded_web_errors(self):
        for index in(0,1,2,4):
            c=self.fixture['cases'][index]
            with self.subTest(case=index):
                self.assertEqual(c['plain_returncode'],0);self.assertIn('nan',c['plain_stdout'].lower())
                self.assertEqual(c['control_before'],0x37f);self.assertEqual(c['control_after'],0x37f)
                values=[struct.unpack('<d',bytes.fromhex(v))[0]for v in c['model']['Y']]
                self.assertTrue(all(math.isnan(v)for v in values));self.assertEqual(c['model']['Y'],c['scattering']['Y'])
                row=[0.,struct.unpack('<d',bytes.fromhex(c['model']['M'][0]))[0],1.,0.,50.,0.,*values,*([0.]*12)]
                output=probe([row])[0]
                for actual,bits in zip(output[1:13],c['model']['M']):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',actual).hex(),bits)
                    else:self.assertTrue(math.isnan(actual))
                for actual,bits in zip(output[21:29],c['scattering']['S']):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',actual).hex(),bits)
                    else:self.assertTrue(math.isnan(actual))
                self.assertTrue(math.isnan(output[15]))
                contact=c['contact_capture'];self.assertTrue(contact['success']);self.assertEqual(contact['control_before'],0x37f);self.assertEqual(contact['control_after'],0x37f)
                invalid=[r for r in contact['records']if any(not(0<=a['indices'][0]<a['indices'][1]<=128 and 0<=a['indices'][2]<a['indices'][3]<=128)for a in r['contacts'])]
                self.assertTrue(invalid)
                if index in(1,4):
                    error='nonzero planar segment length';r=invalid[0];self.assertEqual(r['segment']['points'][0],r['segment']['points'][1])
                    self.assertEqual(r['contacts'][0]['indices'][:4],[-2147483648]*4)
                    self.assertTrue(all(math.isnan(v)for v in struct.unpack('<4d',bytes.fromhex(r['contacts'][0]['bounds_bits']))))
                    # Original CIF also emits the zero-length metal record.
                    polygons=[line[1:].rstrip(';').split()for line in c['cif'].splitlines()if line.startswith('P')]
                    self.assertTrue(any(p[:2]==p[2:4] and p[4:6]==p[6:8]for p in polygons))
                else:error='contact collapses'
                with self.assertRaisesRegex(ValueError,error):handle(c['request'])
                response=json.loads(request_json(json.dumps(c['request'])));self.assertIn(error,response['error'])

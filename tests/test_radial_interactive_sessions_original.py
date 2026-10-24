"""Complete interactive radial electrical stores and independent native CIF."""
import copy,gzip,json,math,struct,unittest
from fractions import Fraction
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import handle,_shape
from reasitic.network_metrics import PI_KEYS
from reasitic.retained_scalar import Real as R


class OriginalRadialInteractiveSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/radial_interactive_sessions_original.json.gz').read_bytes()))

    def test_every_original_electrical_store(self):
        self.assertEqual(len(self.fixture['cases']),6)
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index):
                before=copy.deepcopy(c);r=handle(c['request']);y=r['admittance_matrix']
                self.assertEqual(c['control_before'],0x37f);self.assertEqual(c['control_after'],0x37f);self.assertEqual(c['plain_returncode'],0)
                self.assertEqual([struct.pack('<d',v).hex()for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],c['model']['Y']);self.assertEqual(c['model']['Y'],c['scattering']['Y'])
                for value,bits in zip([r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]],c['model']['M']):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits)
                    else:self.assertIsNone(value)
                self.assertEqual([struct.pack('<d',v).hex()for row in r['scattering_matrix']for z in row for v in z],c['scattering']['S'])
                sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
                if exponent&0x7fff==0x7fff:self.assertIsNone(r['pi']['resonant_frequency_hz'])
                else:
                    expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
                    if not sig:expected=math.copysign(0.,-1 if exponent&0x8000 else 1)
                    self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))
                self.assertEqual(c,before)

    def test_unobserved_original_cif_polygons(self):
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index):
                tech=Technology.from_text(c['request']['technology']);shape=_shape(c['request'],tech)
                native=[[int(v)for v in line[1:].rstrip(';').split()]for line in c['cif'].splitlines()if line.startswith('P')]
                actual=[[int((R(1000)*(R(shape.origin[axis])+R(point[axis]))).value)for point in s.polygon for axis in range(2)]for s in shape.segments]
                self.assertEqual(actual,native);self.assertEqual(len(native),len(shape.segments));self.assertIn('LM4;',c['cif'])

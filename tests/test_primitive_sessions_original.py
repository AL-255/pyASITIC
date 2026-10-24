"""Complete capacitor models at unchanged original electrical output stores."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS


class OriginalPrimitiveSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'primitive_sessions_original.json').read_text())
        assert hashlib.sha256((root/'primitive_original.json').read_bytes()).hexdigest()==cls.fixture['parent_sha256']
        assert len(cls.fixture['cases'])==4

    def check_case(self,index):
        c=self.fixture['cases'][index]
        saved=repr(c);r=handle(c['request']);y=r['admittance_matrix']
        self.assertEqual([struct.pack('<d',v).hex()for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],c['model']['Y'])
        self.assertEqual(c['model']['Y'],c['scattering']['Y'])
        actual=[r['frequency_hz'],*[r['pi'][key]for key in PI_KEYS]];self.assertEqual(len(actual),len(c['model']['M']))
        for j,(value,bits)in enumerate(zip(actual,c['model']['M'])):
            if math.isfinite(struct.unpack('<d',bytes.fromhex(bits))[0]):self.assertEqual(struct.pack('<d',value).hex(),bits,f'Model output {j}')
            else:self.assertIsNone(value)
        self.assertEqual([struct.pack('<d',v).hex()for row in r['scattering_matrix']for z in row for v in z],c['scattering']['S'])
        sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
        if exponent&0x7fff==0x7fff:self.assertIsNone(r['pi']['resonant_frequency_hz'])
        else:
            expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
            self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))
        self.assertEqual(repr(c),saved)

    def test_native_adjacent_plates(self):self.check_case(0)
    def test_native_rotation_and_eddy(self):self.check_case(1)
    def test_interactive_radian_orientation(self):self.check_case(2)
    def test_native_same_metal_plates(self):self.check_case(3)

    def test_original_standalone_via_fault(self):
        self.assertEqual(len(self.fixture['via_faults']),1)
        for c in self.fixture['via_faults']:
            self.assertEqual(c['returncode'],-11)
            with self.assertRaisesRegex(ValueError,'standalone VIA Pi2'):handle(c['request'])

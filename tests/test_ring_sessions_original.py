"""Complete ring electrical sessions at unchanged original output stores."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS


class OriginalRingSessionTests(unittest.TestCase):
    def test_complete_original_ring_pi2_and_eddy_sessions(self):
        root=Path(__file__).parent/'fixtures';fixture=json.loads((root/'ring_sessions_original.json').read_text())
        self.assertEqual(hashlib.sha256((root/'ring_original.json').read_bytes()).hexdigest(),fixture['parent_sha256'])
        self.assertEqual(len(fixture['cases']),3)
        for i,c in enumerate(fixture['cases']):
            with self.subTest(case=i,eddy=c['request']['eddy']):
                before=repr(c);r=handle(c['request']);y=r['admittance_matrix']
                actual=[v for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z]
                self.assertEqual([struct.pack('<d',v).hex()for v in actual],c['model']['Y'])
                self.assertEqual(c['model']['Y'],c['scattering']['Y'])
                actual=[r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]]
                self.assertEqual(len(actual),len(c['model']['M']))
                for j,(value,bits)in enumerate(zip(actual,c['model']['M'])):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits,f'Model output {j}')
                    else:self.assertIsNone(value)
                actual=[v for row in r['scattering_matrix']for z in row for v in z]
                self.assertEqual([struct.pack('<d',v).hex()for v in actual],c['scattering']['S'])
                sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
                self.assertNotEqual(exponent&0x7fff,0x7fff,'Original ring resonance is finite')
                expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
                self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))
                self.assertEqual(repr(c),before)

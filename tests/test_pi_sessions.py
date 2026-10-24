"""Complete portable Pi2 regressions at actual original CLI output stores."""
from fractions import Fraction
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS


class OriginalPi2SessionTests(unittest.TestCase):
    def test_original_square_session_bits(self):
        self.session(1)

    def test_original_polygon_session_bits(self):
        self.session(3)

    def session(self,index):
        root=Path(__file__).parent/'fixtures'
        cases=json.loads((root/'pi_sessions_original.json').read_text())['cases']
        session,c=next((i,c)for i,c in enumerate(cases)if c['fixture']=='network'and c['index']==index)
        metrics=json.loads((root/'network_metrics_original.json').read_text())['cases']
        captured=next(c for c in metrics if c.get('session_index')==session and c['input'][2:4]==[0,0])
        r=handle(c['request']);y=r['admittance_matrix']
        actual=[v for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z]
        self.assertEqual([struct.pack('<d',v).hex()for v in actual],c['model']['Y'])
        actual=[r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]]
        self.assertEqual(len(actual),len(c['model']['M']))
        for value,bits in zip(actual,c['model']['M']):
            expected=struct.unpack('<d',bytes.fromhex(bits))[0]
            if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits)
            else:self.assertIsNone(value)
        raw=bytes.fromhex(captured['output_bits'])
        actual=b''.join(struct.pack('<dd',*z)for row in r['scattering_matrix']for z in row)
        self.assertEqual(actual,raw[160:224])
        significand,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
        expected=float(Fraction(significand)*Fraction(2)**((exponent&0x7fff)-16383-63)*(-1 if exponent&0x8000 else 1))
        self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))

"""Every captured complete Pi session at actual original CLI output stores."""
from fractions import Fraction
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS


class OriginalPiSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures'
        cls.cases=json.loads((root/'pi_sessions_original.json').read_text())['cases']
        metrics=json.loads((root/'network_metrics_original.json').read_text())['cases']
        cls.metrics={c['session_index']:c for c in metrics if 'session_index'in c and c['input'][2:4]==[0,0]}
        assert len(cls.cases)==41 and len(cls.metrics)==41
        assert {c['fixture']for c in cls.cases}=={'network','network_eddy','pi_models','pi_models_eddy','pix','gf180_network'}

    def fixture(self,name):
        selected=[(i,c)for i,c in enumerate(self.cases)if c['fixture']==name]
        self.assertTrue(selected)
        for session,c in selected:
            with self.subTest(session=session,index=c['index']):self.session(session,c)

    def test_original_pi2(self):self.fixture('network')
    def test_original_pi2_eddy(self):self.fixture('network_eddy')
    def test_original_pi3_pi4(self):self.fixture('pi_models')
    def test_original_pi3_pi4_eddy(self):self.fixture('pi_models_eddy')
    def test_original_pix(self):self.fixture('pix')
    def test_original_gf180(self):self.fixture('gf180_network')

    def session(self,session,c):
        before=repr(c);captured=self.metrics[session]
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
        if exponent&0x7fff==0x7fff:self.assertIsNone(r['pi']['resonant_frequency_hz'])
        else:
            expected=float(Fraction(significand)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
            if not significand:expected=math.copysign(0.,-1 if exponent&0x8000 else 1)
            self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))
        self.assertEqual(repr(c),before,'Original request changed')

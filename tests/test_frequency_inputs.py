"""Complete actual-original fractional command inputs and typed-SI compatibility."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle,_frequency
from reasitic.command_numbers import binary32
from reasitic.network_metrics import PI_KEYS
from reasitic.transformer import MODEL_KEYS


class FrequencyInputTests(unittest.TestCase):
    def test_actual_original_fractional_pi_sessions(self):
        root=Path(__file__).parent/'fixtures';fixture=json.loads((root/'frequency_inputs_original.json').read_text())
        self.assertEqual(hashlib.sha256((root/'pi_sessions_original.json').read_bytes()).hexdigest(),fixture['parent_sha256'])
        self.assertEqual(len(fixture['cases']),17)
        for index,c in enumerate(fixture['cases']):
            with self.subTest(index=index,ghz=c['command_ghz']):
                before=repr(c);r=handle(c['request']);y=r['admittance_matrix']
                self.assertEqual([struct.pack('<d',v).hex()for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],c['model']['Y'])
                values=[r['frequency_hz'],*[r['pi'][key]for key in PI_KEYS]]
                for actual,bits in zip(values,c['model']['M']):
                    expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(expected):self.assertEqual(struct.pack('<d',actual).hex(),bits)
                    else:self.assertIsNone(actual)
                sig,exponent=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
                if exponent&0x7fff==0x7fff:self.assertIsNone(r['pi']['resonant_frequency_hz'])
                else:
                    expected=float(Fraction(sig)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
                    self.assertEqual(struct.pack('<d',r['pi']['resonant_frequency_hz']),struct.pack('<d',expected))
                self.assertEqual(repr(c),before,'Caller request changed')

    def test_actual_original_fractional_coupled_sessions(self):
        root=Path(__file__).parent/'fixtures';fixture=json.loads((root/'frequency_inputs_original.json').read_text())
        self.assertEqual(hashlib.sha256((root/'transformer_network.json').read_bytes()).hexdigest(),fixture['coupled_parent_sha256'])
        self.assertEqual(len(fixture['coupled_cases']),3)
        for c in fixture['coupled_cases']:
            with self.subTest(ghz=c['command_ghz']):
                before=repr(c);r=handle(c['request']);y=r['admittance_matrix'];z=r['impedance_matrix']
                self.assertEqual(struct.pack('<d',r['frequency_hz']).hex(),c['frequency_bits'])
                values=[v for pair in(y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1])for v in pair]
                values.extend(r['model'][key]for key in MODEL_KEYS)
                self.assertEqual(len(values),len(c['raw_output_bits']))
                for value,bits in zip(values,c['raw_output_bits']):
                    if math.isfinite(struct.unpack('<d',bytes.fromhex(bits))[0]):self.assertEqual(struct.pack('<d',value).hex(),bits)
                    else:self.assertIsNone(value)
                self.assertEqual(repr(c),before,'Caller coupled request changed')

    def test_native_ghz_and_typed_hz_are_distinct_input_boundaries(self):
        self.assertEqual(_frequency(dict(frequency_ghz=.1234567)),123456704.)
        self.assertEqual(_frequency(dict(frequency_hz=123456700.)),123456700.)
        self.assertEqual(_frequency(dict(frequency_hz=123456700.,frequency_ghz=.1234567)),123456704.)
        self.assertEqual(_frequency(dict(first_ghz=.1234567),'first'),123456704.)
        self.assertEqual(_frequency(dict(first_hz=123456700.),'first'),123456700.)
        with self.assertRaises(KeyError):_frequency({},'first')
        for value in(0.,-1.,1e-11,math.nan,math.inf):
            with self.assertRaises(ValueError):_frequency(dict(frequency_ghz=value))

    def test_binary32_store_has_no_binary64_double_rounding(self):
        # A retained value just above a float midpoint must round upward,
        # even when its binary64 store is exactly that midpoint.
        value=Fraction(1)+Fraction(1,1<<24)+Fraction(1,1<<63)
        from reasitic.retained_scalar import Real
        self.assertEqual(binary32(Real(value)),1.+2.**-23)
        self.assertEqual(struct.unpack('<f',struct.pack('<f',float(value)))[0],1.)

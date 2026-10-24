"""Complete wire models at unchanged original electrical output stores."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest
from reasitic.bridge import handle,request_json
from reasitic.network_metrics import PI_KEYS


class OriginalWireSessionTests(unittest.TestCase):
    def test_complete_original_wire_pi2_and_eddy_sessions(self):
        root=Path(__file__).parent/'fixtures';fixture=json.loads((root/'wire_sessions_original.json').read_text())
        self.assertEqual(hashlib.sha256((root/'wire_original.json').read_bytes()).hexdigest(),fixture['parent_sha256'])
        self.assertEqual(len(fixture['cases']),6)
        for i,c in enumerate(fixture['cases']):
            with self.subTest(case=i,keyword=c['request']['native_keyword'],eddy=c['request']['eddy']):
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

        self.assertEqual(len(fixture['undefined_cases']),2)
        for c in fixture['undefined_cases']:
            from types import SimpleNamespace
            from reasitic.contact_geometry import groups
            from reasitic.model import Shape,Segment
            from reasitic.network_metrics import probe
            from reasitic.potential import Contact
            self.assertIn('nan',c['stdout'].lower());self.assertIn(c['index'],(2,7))
            values=[struct.unpack('<d',bytes.fromhex(v))[0]for v in c['model']['Y']]
            self.assertTrue(all(math.isnan(v)for v in values))
            row=[0.,struct.unpack('<d',bytes.fromhex(c['model']['M'][0]))[0],1.,0.,50.,0.,*values,*([0.]*12)]
            output=probe([row])[0]
            for value,bits in zip(output[1:13],c['model']['M']):
                expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits)
                else:self.assertTrue(math.isnan(value))
            for value,bits in zip(output[21:29],c['scattering']['S']):
                expected=struct.unpack('<d',bytes.fromhex(bits))[0]
                if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits)
                else:self.assertTrue(math.isnan(value))
            self.assertTrue(math.isnan(output[15]))
            capture=c['contact_capture'];o=capture['options'];self.assertEqual(len(capture['records']),1)
            r=capture['records'][0];segment=r['segment'];shape=Shape('Probe','wire',r['origin'],{},[Segment(*segment['points'],segment['width'],0.,segment['metal'],segment['nx'],segment['ny'],segment['primary_width'])]);seen=[]
            expected=[a['indices']for a in r['contacts']]
            if c['index']==2:
                self.assertEqual(expected,[[14,34,15,15,4]])
                with self.assertRaisesRegex(ValueError,'contact collapses'):
                    groups(shape,SimpleNamespace(metals=[None]*o['metal_count']),o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
                with self.assertRaisesRegex(ValueError,'contact collapses'):handle(c['request'])
            else:
                self.assertEqual(expected,[[16,56,16,17,4]])
                actual=groups(shape,SimpleNamespace(metals=[None]*o['metal_count']),o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
                self.assertEqual([[a.x0,a.x1,a.y0,a.y1,a.metal]for a in actual[0]],expected)
                model=handle(c['request']);self.assertTrue(all(math.isnan(v)for row in model['admittance_matrix']for z in row for v in z))
                for key,bits in zip(PI_KEYS,c['model']['M'][1:]):
                    value=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(value):self.assertEqual(struct.pack('<d',model['pi'][key]).hex(),bits)
                    else:self.assertIsNone(model['pi'][key])
                for value,bits in zip((v for row in model['scattering_matrix']for z in row for v in z),c['scattering']['S']):
                    target=struct.unpack('<d',bytes.fromhex(bits))[0]
                    if math.isfinite(target):self.assertEqual(struct.pack('<d',value).hex(),bits)
                    else:self.assertTrue(math.isnan(value))
                response=json.loads(request_json(json.dumps(c['request'])));self.assertIn('nonfinite admittance',response['error'])
            self.assertEqual([struct.pack('<4d',*v).hex()for v in reversed(seen)],[a['bounds_bits']for a in r['contacts']])

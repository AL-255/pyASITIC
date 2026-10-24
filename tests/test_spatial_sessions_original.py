"""Exact original Pi2/CALCTRANS outputs after spatial editing histories."""
import gzip,hashlib,json,math,struct,unittest
from fractions import Fraction
from pathlib import Path
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS
from reasitic.transformer import MODEL_KEYS


class OriginalSpatialSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'spatial_sessions_original.json.gz').read_bytes()))
        assert len(cls.fixture['cases'])==3
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest

    def test_complete_edited_models_and_native_node_matrices(self):
        bits=lambda v:struct.pack('<d',v).hex()
        for c in self.fixture['cases']:
            with self.subTest(label=c['label']):
                saved=repr(c);r=handle(dict(c['request'],include_matrices=True));y=r['admittance_matrix'];actual=[v for cell in(y[1][1],y[1][0],y[0][1],y[0][0])for v in cell]
                if c['request']['action']=='pi2':
                    self.assertEqual(list(map(bits,actual)),c['model']['Y']);self.assertEqual(c['scattering']['Y'],c['model']['Y'])
                    for value,expected in zip([r['frequency_hz'],*[r['pi'][k]for k in PI_KEYS]],c['model']['M']):
                        target=struct.unpack('<d',bytes.fromhex(expected))[0]
                        if math.isfinite(target):self.assertEqual(bits(value),expected)
                        else:self.assertIsNone(value)
                    sig,e=struct.unpack('<QH',bytes.fromhex(c['resonance']['extended_bits']))
                    if e&0x7fff==0x7fff:self.assertIsNone(r['pi']['resonant_frequency_hz'])
                    else:self.assertEqual(bits(r['pi']['resonant_frequency_hz']),bits(float(Fraction(sig)*Fraction(2)**(((e&0x7fff)or 1)-16383-63)*(-1 if e&0x8000 else 1))))
                    scattering=c['scattering']['S']
                else:
                    self.assertEqual((c['signal'],c['pending']),(0,0));self.assertEqual(len(c['records']),1);self.assertEqual(len(c['nodes']),2);self.assertEqual(c['nodes'][0],c['nodes'][1]);self.assertEqual(c['raw_output_bits'][:23],c['raw_output_bits'][23:])
                    z=r['impedance_matrix'];actual+=[v for cell in(z[0][0],z[0][1],z[1][0],z[1][1])for v in cell]+[r['model'][k]for k in MODEL_KEYS]
                    self.assertEqual(list(map(bits,actual)),c['raw_output_bits'][:23]);self.assertEqual(c['records'][0]['Y'],c['raw_output_bits'][:8]);scattering=c['records'][0]['S']
                    for native,key in[('capacitance','capacitance_matrix'),('inductance','inductive_admittance_matrix')]:
                        event=c['nodes'][0];n=event['size'];self.assertEqual(b''.join(struct.pack('<2d',*r[key][i][j])for j in range(n)for i in range(n)).hex(),event[native])
                self.assertEqual([bits(v)for row in r['scattering_matrix']for cell in row for v in cell],scattering);self.assertEqual(repr(c),saved)

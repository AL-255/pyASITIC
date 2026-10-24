"""Raw original 3D winding LMAT returns and native failed coupled histories."""
import hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic.bridge import handle,request_json


class OriginalTransformer3DSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'transformer3d_sessions_original.json').read_text())
        assert hashlib.sha256((root/'transformer3d_original.json').read_bytes()).hexdigest()==cls.fixture['parent_sha256'];assert len(cls.fixture['cases'])==6

    def check_case(self,index):
        c=self.fixture['cases'][index];saved=repr(c)
        for winding,m in enumerate(c['lmat']):
            self.assertEqual(m['name'],('P','S')[winding]);self.assertEqual(m['impedance'],1)
            r=handle(m['request']);n=m['size'];self.assertEqual(m['success'],1);self.assertEqual(len(r['matrix']),n)
            self.assertEqual(struct.pack('<d',r['frequency_hz']).hex(),m['frequency_bits'])
            self.assertEqual(b''.join(struct.pack('<2d',*r['matrix'][i][j])for j in range(n)for i in range(n)).hex(),m['matrix_bits'],(index,winding))
        # Preserve every selected coupled history. No native crash/NaN session
        # is silently replaced by a different geometry or successful model.
        if c['signal']:
            self.assertEqual(c['signal'],11);self.assertEqual(c['plain_returncode'],-11);self.assertEqual(c['raw_output_bits'],[]);self.assertIsNone(c['scattering'])
        else:
            self.assertEqual(c['plain_returncode'],0);self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(b))[0])for b in c['raw_output_bits']));self.assertEqual(len(c['raw_output_bits']),23)
            self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(b))[0])for b in c['scattering']['S']))
        with self.assertRaisesRegex(ValueError,'nonzero planar segment length'):handle(c['request'])
        self.assertRegex(json.loads(request_json(json.dumps(c['request'])))['error'],'nonzero planar segment length')
        self.assertEqual(repr(c),saved)

    def test_turn_one(self):self.check_case(0)
    def test_fractional_phase_eddy(self):self.check_case(1)
    def test_wide_metal_span(self):self.check_case(2)
    def test_reversed_metal_span(self):self.check_case(3)
    def test_multi_turn_eddy(self):self.check_case(4)
    def test_larger_fractional_turn(self):self.check_case(5)

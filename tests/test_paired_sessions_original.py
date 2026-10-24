"""Exact original paired CALCTRANS/2PORTTRANS SI outputs after native creation."""
import hashlib,json,math,struct,unittest
from reasitic import Technology
from reasitic.bridge import _shapes,request_json
from reasitic.network import _join_for_pads
from reasitic.solver import discretize,filament_counts,filament
from pathlib import Path
from unittest.mock import patch
from reasitic.impedance import assemble
from reasitic.bridge import handle
from reasitic.transformer import MODEL_KEYS


class OriginalPairedSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'paired_sessions_original.json').read_text())
        assert hashlib.sha256((root/'paired_original.json').read_bytes()).hexdigest()==cls.fixture['parent_sha256']
        assert len(cls.fixture['cases'])==6

    def check_case(self,index):
        c=self.fixture['cases'][index];saved=repr(c)
        def observed_assembly(*args,**kwargs):
            matrix=assemble(*args,**kwargs);n=c['assembly']['n']
            self.assertEqual(b''.join(struct.pack('<2d',matrix[i][j].real,matrix[i][j].imag)for j in range(n)for i in range(j+1)).hex(),c['assembly']['upper_bits'])
            return matrix
        with patch('reasitic.solver.assemble_impedance',side_effect=observed_assembly):self.check_model(c,index,saved)

    def check_model(self,c,index,saved):
        if index==3:
            # Keep the native all-NaN reference history, with the existing bounded
            # public diagnostic rather than a fabricated finite circuit.
            self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(b))[0])for b in c['raw_output_bits']))
            self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(b))[0])for b in c['scattering']['S']))
            with self.assertRaisesRegex(ValueError,'nonfinite inductive kernel'):handle(c['request'])
            self.assertIn('nonfinite inductive kernel',json.loads(request_json(json.dumps(c['request'])))['error'])
            return
        r=handle(dict(c['request'],include_matrices=True));y,z=r['admittance_matrix'],r['impedance_matrix']
        actual=[v for cell in [y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]]for v in cell]+[r['model'][key]for key in MODEL_KEYS]
        self.assertEqual(len(actual),len(c['raw_output_bits']))
        for value,bits in zip(actual,c['raw_output_bits']):
            expected=struct.unpack('<d',bytes.fromhex(bits))[0]
            if math.isfinite(expected):self.assertEqual(struct.pack('<d',value).hex(),bits)
            elif value is not None:
                self.assertTrue(math.isnan(value)if math.isnan(expected)else value==expected)
        self.assertEqual([struct.pack('<d',v).hex()for row in r['scattering_matrix']for cell in row for v in cell],c['scattering']['S'])
        self.assertEqual(c['scattering']['Y'],c['raw_output_bits'][:8]);self.assertEqual(repr(c),saved)
        for native,key in [('capacitance','capacitance_matrix'),('inductance','inductive_admittance_matrix')]:
            event=c['node_events'][0];n=event['size']
            self.assertEqual(b''.join(struct.pack('<2d',*r[key][i][j])for j in range(n)for i in range(n)).hex(),event[native])

    def test_original_joined_conductors_and_filaments(self):
        for i,c in enumerate(self.fixture['cases']):
            request=c['request'];tech=Technology.from_text(request['technology']);a,b=_shapes(request,tech)
            for shape,winding in zip((a,b),c['geometry']['windings']):
                self.assertEqual(struct.pack('<2d',*shape.origin).hex(),winding['origin_bits'])
                self.assertEqual([struct.pack('<18d',*(v for p in s.points for v in p)).hex()for s in shape.segments],[s['coordinates_bits']for s in winding['segments']])
            if request.get('ground'):
                for segment in a.segments:segment.nx=segment.ny=-1
            a,b=[discretize(s,1000,1000)for s in(a,b)];b.segments.reverse();joined=_join_for_pads(a,b);position=0
            for segment in joined.segments:
                if segment.metal>=len(tech.metals):continue
                ny,nz=filament_counts(segment,1000,1000)
                for yi in range(ny):
                    for zi in range(nz):
                        record=c['assembly']['records'][position];position+=1;raw=bytes.fromhex(record['input']['segment'])
                        self.assertEqual(struct.pack('<18d',*(v for p in segment.points for v in p)),b''.join(raw[o:o+24]for o in(0,24,0x44,0x5c,0x88,0xa0)),(i,position))
                        self.assertEqual(struct.pack('<2d',segment.width,segment.thickness),raw[0xcc:0xdc])
                        self.assertEqual(struct.pack('<8d',*filament(segment,joined.origin,yi,zi,ny,nz,1000,9,tech)).hex(),record['wire_bits'],(i,position))
            self.assertEqual(position,c['assembly']['n'])

    def test_keyword_unequal_quarter_turns(self):self.check_case(0)
    def test_keyword_exit_rotation_phase_reference_eddy(self):self.check_case(1)
    def test_keyword_unequal_balun_widths(self):self.check_case(2)
    def test_interactive_transformer(self):self.check_case(3)
    def test_interactive_balun_eddy(self):self.check_case(4)
    def test_keyword_low_turn_same_metal_balun(self):self.check_case(5)

"""Actual original CELL/CCELL parsing, cloning, filaments and electrical stores."""
import copy,gzip,json,math,struct,unittest
from fractions import Fraction
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _mesh,_shape,handle
from reasitic.command_numbers import mesh_cell_um
from reasitic.filament import filament_records,record
from reasitic.mesh import MESH_KEYS
from reasitic.network_metrics import PI_KEYS
from reasitic.solver import discretize,filament_counts


def bits(value):return struct.pack('<d',value).hex()


class OriginalMeshInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/mesh_inputs_original.json.gz').read_bytes()))

    def test_original_cell_globals_counts_and_filaments(self):
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index):
                request=c['request'];before=copy.deepcopy(request);tech=Technology.from_text(request['technology']);mesh=_mesh(request,tech)
                self.assertEqual(struct.pack('<5d',*[mesh[k]for k in MESH_KEYS]).hex(),c['pi2']['model']['mesh_bits'])
                self.assertEqual(struct.pack('<2d2i',tech.chip['chipx'],tech.chip['chipy'],int(tech.chip['fftx']),int(tech.chip['ffty'])).hex(),c['pi2']['model']['chip_bits'])
                shape=_shape(request,tech);meshed=discretize(shape,mesh['capacitance_length_cell'],mesh['length_cell']);rows=[];sizes=[]
                for segment in meshed.segments:
                    w,t=filament_counts(segment,mesh['width_cell'],mesh['thickness_cell']);sizes.append((w,t))
                    rows.extend(record(segment,shape.origin,i,j,w,t,mesh['width_cell'],500,tech)for i in range(w)for j in range(t))
                native=c['lmat'];self.assertEqual(native['signal'],0);self.assertEqual(native['pending'],0);self.assertEqual(len(native['counts']),1)
                count=native['counts'][0]
                self.assertEqual([w for w,t in sizes],count['width']);self.assertEqual([t for w,t in sizes],count['thickness'])
                actual={struct.pack('<8d',*r[:8]).hex()+struct.pack('<i',int(r[8])).hex()for r in filament_records(rows)}
                expected={r['bits']+struct.pack('<i',r['metal']).hex()for r in native['filaments']}
                self.assertEqual(actual,expected)
                self.assertEqual(handle(dict(request,action='mesh',model='lmat'))['filaments'],count['total'])
                self.assertEqual(before,request)

    def test_complete_original_lmat_reports(self):
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index):
                result=handle(dict(c['request'],action='lmat'))
                self.assertEqual(struct.pack('<2d',result['inductance_h'],result['resistance_ohm']).hex(),c['lmat']['reports'][0]['bits'])

    def test_complete_original_pi2_stores(self):
        for index,c in enumerate(self.fixture['cases']):
            with self.subTest(index=index):
                request=dict(c['request'],action='pi2');before=copy.deepcopy(request);result=handle(request);y=result['admittance_matrix'];native=c['pi2']
                self.assertEqual([bits(v)for z in(y[1][1],y[1][0],y[0][1],y[0][0])for v in z],native['model']['Y'])
                self.assertEqual([bits(v)for z in result['scattering_matrix']for pair in z for v in pair],native['scattering']['S'])
                for value,word in zip([result['frequency_hz'],*[result['pi'][k]for k in PI_KEYS]],native['model']['M']):
                    expected=struct.unpack('<d',bytes.fromhex(word))[0]
                    if math.isfinite(expected):self.assertEqual(bits(value),word)
                    else:self.assertIsNone(value)
                significand,exponent=struct.unpack('<QH',bytes.fromhex(native['resonance']['extended_bits']))
                if exponent&0x7fff==0x7fff:self.assertIsNone(result['pi']['resonant_frequency_hz'])
                else:
                    value=float(Fraction(significand)*Fraction(2)**(((exponent&0x7fff)or 1)-16383-63)*(-1 if exponent&0x8000 else 1))
                    self.assertEqual(bits(result['pi']['resonant_frequency_hz']),bits(value))
                self.assertEqual(native['control_before'],0x37f);self.assertEqual(native['control_after'],0x37f);self.assertEqual(before,request)

    def test_typed_mesh_boundary_maxnw_and_invalid_native_cells(self):
        tech=Technology.default();mesh=dict(zip(MESH_KEYS,(20.0000001,1.90476191,.33333333,1.42857145,3.3333333)),max_width_cells=2147483647)
        request=dict(mesh=mesh);self.assertEqual(_mesh(request,tech),mesh)
        parsed=_mesh(dict(request,native_mesh=True),tech)
        self.assertEqual(parsed['max_width_cells'],2147483647);self.assertEqual(parsed['width_cell'],1.899999976158142)
        self.assertEqual(parsed['capacitance_width_cell'],4.);self.assertEqual(parsed['capacitance_length_cell'],4.)
        cap=_mesh(dict(action='capacitance',mesh=dict(length_cell=1.42857145,width_cell=3.3333333),native_mesh=True),tech)
        self.assertEqual(cap,dict(length_cell=4.,width_cell=4.))
        for v in(0,-1,math.nan,math.inf,1e300,1e-300,.001):
            with self.subTest(value=v):
                with self.assertRaises(ValueError):mesh_cell_um(v)

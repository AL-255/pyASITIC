"""Unmodified original COUPLING reports, retained normalization and mutation history."""
import gzip,hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shape,_shapes,handle
from reasitic.conductor_metrics import _records
from reasitic.coupling_metrics import retained_coupling
from reasitic.retained_scalar import Real as R
from test_conductor_metrics_original import rows


def bits(value):return struct.pack('<d',float(value)).hex()
def raw(value):return struct.pack('<IIH',*value.words()).hex()
def number(word):return struct.unpack('<d',bytes.fromhex(word))[0]
def shape_records(shape,technology):return b''.join(struct.pack('<16d',*p)for p in _records(shape,technology))
def native_records(observed):return b''.join(struct.pack('<16d',*p)for p in rows(dict(inputs=observed['segments'])))
def shapes(c):
    tech=Technology.from_text(c['technology'])
    return tech,[_shape(c[key],tech)for key in('first','second')]if 'first'in c else _shapes(c['public'],tech)
def check_geometry(test,shape,native):
    test.assertEqual(struct.pack('<2d',*shape.origin).hex(),native['origin_bits']);test.assertEqual(shape.name,native['name']);test.assertEqual(len(shape.segments),len(native['segments']))
    for actual,expected in zip(shape.segments,native['segments']):
        test.assertEqual(struct.pack('<6d',*actual.start,*actual.end).hex(),expected['endpoints_bits'])
        test.assertEqual(struct.pack('<12d',*actual.outer_start,*actual.outer_end,*actual.inner_start,*actual.inner_end).hex(),expected['edges_bits'])


class OriginalCouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'coupling_original.json.gz').read_bytes()));cls.cases=cls.fixture['cases']
        assert len(cls.cases)==112
        for name,want in cls.fixture['parents'].items():assert hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest()==want

    def test_original_binary64_accumulation_and_raw_normalization(self):
        pairs=calls=0
        for c in self.cases:
            self.assertEqual(c['signal'],0);self.assertIsNone(c['unfinished'])
            for e,report in zip(c['calls'],c['reports']):
                with self.subTest(label=c['label'],call=calls):
                    mutual=0.
                    for p in e['pairs']:
                        self.assertEqual(p['status'],0);mutual=float(R(mutual)+R(number(p['value_bits'])));self.assertEqual(bits(mutual),p['sum_bits']);pairs+=1
                    self.assertEqual(bits(mutual),e['mutual_bits']);self.assertEqual(e['mutual_bits'],report['mutual_bits'])
                    l1,l2=map(number,e['inductance_bits']);coefficient=R(mutual)/(R(l1)*R(l2)).sqrt()if R(1e-10)<R(l1)and R(1e-10)<R(l2)else R(0.)
                    self.assertEqual(raw(coefficient),e['extended_bits']);self.assertEqual(bits(coefficient),report['coefficient_bits']);self.assertEqual(e['control_before'],0x37f);self.assertEqual(e['control_after'],0x37f);self.assertEqual(report['control'],0x37f);calls+=1
        self.assertEqual(calls,428);self.assertEqual(pairs,81996)

    def test_complete_public_calls_and_native_translation_history(self):
        calls=0
        for c in self.cases:
            if not c['calls']:
                self.assertIn('Error:',c['stdout']);continue
            tech,initial=shapes(c);by_name={s.name:s for s in initial}
            for e,report in zip(c['calls'],c['reports']):
                with self.subTest(label=c['label'],call=calls):
                    a,b=(by_name[e[side+'_before']['name']]for side in('first','second'))
                    self.assertEqual(shape_records(a,tech),native_records(e['first_before']));self.assertEqual(shape_records(b,tech),native_records(e['second_before']))
                    mutual,coefficient=retained_coupling(a,b,tech)
                    self.assertEqual(bits(mutual),report['mutual_bits']);self.assertEqual(bits(coefficient),report['coefficient_bits']);self.assertEqual(raw(coefficient),e['extended_bits'])
                    check_geometry(self,a,e['first_after']);check_geometry(self,b,e['second_after']);calls+=1
        self.assertEqual(calls,428)

    def test_typed_alias_bounds_and_bridge(self):
        c=self.cases[0];tech,windings=shapes(c)
        with self.assertRaisesRegex(ValueError,'self-coupling'):retained_coupling(windings[0],windings[0],tech)
        a,b=windings;a.segments=a.segments*1001;b.segments=b.segments*1001
        with self.assertRaisesRegex(ValueError,'one million'):retained_coupling(a,b,tech)
        duplicate=self.cases[81]['public']
        with self.assertRaisesRegex(ValueError,'self-coupling'):handle(dict(action='coupling',first=dict(duplicate,winding=0),second=dict(duplicate,winding=1)))
        definition=c['public'];result=handle(dict(action='coupling',technology=c['technology'],first=dict(definition,winding=0),second=dict(definition,winding=1)))
        self.assertEqual(bits(result['mutual_nh']),c['reports'][0]['mutual_bits']);self.assertEqual(bits(result['k']),c['reports'][0]['coefficient_bits'])

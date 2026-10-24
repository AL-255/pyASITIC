"""Raw unchanged-original RESIS/RESISHF returns and public metric stores."""
from fractions import Fraction
import hashlib,json,math
from pathlib import Path
import struct,unittest
from reasitic import Technology,build,resistance_dc,resistance_hf
from reasitic.model import Shape,Segment
from reasitic.resistance import _records,_retained

ROOT=Path(__file__).parent/'fixtures'


def unpack(bits):
    sig,exponent=struct.unpack('<QH',bytes.fromhex(bits));power=exponent&0x7fff
    if power==0x7fff:return math.nan if sig&((1<<63)-1)else(-math.inf if exponent&0x8000 else math.inf)
    if not sig:return -0. if exponent&0x8000 else 0.
    return float(Fraction(sig)*Fraction(2)**((power or 1)-16383-63)*(-1 if exponent&0x8000 else 1))


def replay(c):
    tech=Technology.from_text(c['technology']);segments=[]
    for r in c['inputs']:
        p=r['endpoints'];segments.append(Segment(p[:3],p[3:],p[:3],p[3:],p[:3],p[3:],r['width'],r.get('thickness',0.),r['metal'],r.get('nx',0),r.get('ny',0)))
        actual=tech.vias[r['metal']-len(tech.metals)]if r['via']else tech.metals[r['metal']]
        assert struct.pack('<d',actual.resistance)==struct.pack('<d',r['resistance'])
        if not r['via']:assert struct.pack('<d',actual.thickness)==struct.pack('<d',r['thickness'])
    return Shape('A','probe',[0,0],{},segments),tech


class OriginalResistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/'resistance_original.json').read_text());cls.cases=cls.fixture['cases']
        assert len(cls.cases)==34
        for parent,sha in cls.fixture['parents'].items():assert hashlib.sha256((ROOT/(parent+'.json')).read_bytes()).hexdigest()==sha

    def test_every_original_retained_return_and_public_output(self):
        finite=undefined=0
        for c in self.cases:
            with self.subTest(label=c['label']):
                before=repr(c);shape,tech=replay(c);records=_records(shape,tech);self.assertEqual(len(c['events']),8)
                for e in c['events']:
                    actual=_retained(records,e.get('frequency_hz'));expected=unpack(e['extended_bits'])
                    if math.isfinite(expected):
                        self.assertEqual(struct.pack('<IIH',*actual.words()).hex(),e['extended_bits'])
                        output=resistance_dc(shape,tech)if e['operation']=='dc'else resistance_hf(shape,tech,e['frequency_hz'])
                        self.assertEqual(struct.pack('<d',output),struct.pack('<d',expected));finite+=1
                    else:
                        self.assertTrue(math.isnan(expected));self.assertEqual(actual.kind,2)
                        with self.assertRaisesRegex(ValueError,'width ≥ metal thickness'):resistance_hf(shape,tech,e['frequency_hz'])
                        undefined+=1
                self.assertEqual(repr(c),before)
        self.assertEqual((finite,undefined),(270,2))

    def test_public_creator_modes_and_complete_matching_histories(self):
        pending=[];matched=0
        for c in self.cases:
            expected,tech=replay(c);p=c['public'];shape=build(p['kind'],technology=tech,native_keyword=p.get('native_keyword',False),**p['parameters'])
            # Compare every consumed store before attributing an output
            # difference to resistance rather than an unported creator input.
            if len(shape.segments)!=len(expected.segments)or any(struct.pack('<12d',*a)!=struct.pack('<12d',*b)for a,b in zip(_records(shape,tech),_records(expected,tech))):
                pending.append(c['label']);continue
            matched+=1
            for e in c['events']:
                expected_value=unpack(e['extended_bits'])
                if math.isnan(expected_value):
                    with self.assertRaisesRegex(ValueError,'width ≥ metal thickness'):resistance_hf(shape,tech,e['frequency_hz'])
                else:
                    result=resistance_dc(shape,tech)if e['operation']=='dc'else resistance_hf(shape,tech,e['frequency_hz'])
                    self.assertEqual(struct.pack('<d',result),struct.pack('<d',expected_value),c['label'])
        # These existing creator gaps remain explicit; every one of their
        # actual original resistance input/return records is required above.
        self.assertEqual(pending,['analysis/11'])
        self.assertEqual(matched,33)

    def test_zero_frequency_empty_shape_and_invalid_frequency(self):
        tech=Technology.default();empty=Shape('Empty','wire',[0,0],{},[])
        self.assertEqual(resistance_dc(empty,tech),0.);self.assertEqual(resistance_hf(empty,tech,0.),0.)
        wire=build('wire',length=40,width=5,metal='M1')
        self.assertEqual(struct.pack('<d',resistance_dc(wire,tech)),struct.pack('<d',resistance_hf(wire,tech,0.)))
        for f in(-1.,math.inf,math.nan):
            with self.assertRaisesRegex(ValueError,'finite and nonnegative'):resistance_hf(wire,tech,f)

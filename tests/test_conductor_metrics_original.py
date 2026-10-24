"""Original complete conductor command stores and consumed input boundaries."""
import hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shape,handle
from reasitic.command_numbers import frequency_ghz
from reasitic.conductor_metrics import _records,_self_and_dc,retained_estimates,qlf
from reasitic.retained_scalar import Real as R


def rows(case):
    def number(record,key):return struct.unpack('<d',bytes.fromhex(record[key+'_bits']))[0]if key+'_bits'in record else 0.
    return [[*struct.unpack('<6d',bytes.fromhex(r['endpoints_bits'])),number(r,'width'),number(r,'thickness'),number(r,'resistance'),float(r['via']),r.get('nx',0),r.get('ny',0),number(r,'via_width'),number(r,'via_spacing'),number(r,'primary_width'),number(r,'primary_thickness')]for r in case['inputs']]


class OriginalConductorMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads((root/'conductor_metrics_original.json').read_text());cls.cases=cls.fixture['cases']
        assert len(cls.cases)==56
        for name,want in cls.fixture['parents'].items():assert hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest()==want

    def test_self_operands_dc_returns_and_aggregate_output_stores(self):
        traces=0;reports=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                self.assertEqual(c['signal'],0);self.assertIsNone(c['unfinished']);seen=[]
                self_total,dc=_self_and_dc(rows(c),seen.append);native=c['inductance'][0];self.assertEqual(len(seen),len(native['self_terms']))
                for actual,expected in zip(seen,native['self_terms']):
                    self.assertEqual(actual['segment'],expected['segment'])
                    for key in('length','width','thickness','log_argument'):
                        if key in expected:self.assertEqual(struct.pack('<IIH',*actual[key].words()).hex(),expected[key])
                    traces+=1
                mutual=R(0.)
                for pair in native['pairs']:
                    self.assertEqual(pair['status'],0);mutual=mutual+R(struct.unpack('<d',bytes.fromhex(pair['value_bits']))[0])
                total=(mutual+mutual)+self_total
                for event in c['dc']:self.assertEqual(struct.pack('<IIH',*dc.words()).hex(),event['extended_bits']);self.assertEqual(event['control'],0x37f)
                for event in c['inductance']:self.assertEqual(event['control_before'],0x37f);self.assertEqual(event['control_after'],0x37f)
                for event in c['reports']:self.assertEqual(event['control'],0x37f)
                self.assertEqual(struct.pack('<d',float(total)).hex(),c['reports'][0]['output_bits'])
                for ghz,event in zip(c['frequency_ghz'],c['reports'][1:]):self.assertEqual(struct.pack('<d',qlf(total,dc,frequency_ghz(ghz))).hex(),event['output_bits']);reports+=1
        self.assertEqual(reports,392);self.assertEqual(traces,sum(len(c['inputs'])for c in self.cases))

    def test_public_consumed_records_and_complete_metrics(self):
        total=0
        for i,c in enumerate(self.cases):
            with self.subTest(case=i,label=c['label']):
                before=repr(c);t=Technology.from_text(c['technology']);s=_shape(c['public'],t)
                self.assertEqual(b''.join(struct.pack('<16d',*r)for r in _records(s,t)),b''.join(struct.pack('<16d',*r)for r in rows(c)))
                inductance,dc=retained_estimates(s,t);self.assertEqual(struct.pack('<d',float(inductance)).hex(),c['reports'][0]['output_bits'])
                self.assertEqual(struct.pack('<IIH',*dc.words()).hex(),c['dc'][0]['extended_bits'])
                for ghz,event in zip(c['frequency_ghz'],c['reports'][1:]):self.assertEqual(struct.pack('<d',qlf(inductance,dc,frequency_ghz(ghz))).hex(),event['output_bits']);total+=1
                self.assertEqual(repr(c),before)
        self.assertEqual(total,392)

    def test_native_ghz_and_typed_si_sweep_metrics(self):
        c=self.cases[0];base=c['public']
        r=handle(dict(base,action='simulate',frequency_ghz=c['frequency_ghz'][1]))
        self.assertEqual(struct.pack('<d',r['inductance_nh']).hex(),c['reports'][0]['output_bits']);self.assertEqual(struct.pack('<d',r['qlf']).hex(),c['reports'][2]['output_bits'])
        r=handle(dict(base,action='sweep',first_ghz=1,last_ghz=100,count=3))
        for row,event in zip(r['rows'],c['reports'][3:6]):self.assertEqual(struct.pack('<d',row['qlf']).hex(),event['output_bits'])
        r=handle(dict(base,action='sweep',first_ghz=.1234567,last_ghz=2.34567891,count=3))
        for row in r['rows']:
            direct=handle(dict(base,action='simulate',frequency_ghz=row['frequency_hz']/1e9));self.assertEqual(row['frequency_hz'],direct['frequency_hz']);self.assertEqual(row['qlf'],direct['qlf'])
        r=handle(dict(base,action='sweep',first_hz=123456700.,last_hz=2345678910.,count=3))
        self.assertEqual(r['rows'][0]['frequency_hz'],123456700.)

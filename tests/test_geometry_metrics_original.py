"""Original complete GEOM and METALAREA operands, accumulators and actual stores."""
import gzip,hashlib,json,math,struct,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shape,handle
from reasitic.geometry_metrics import _portable,retained_geometry_metrics


def bits(value):return struct.pack('<d',float(value)).hex()
def raw(value):return struct.pack('<IIH',*value.words()).hex()
def records(event):return [struct.unpack('<7d',bytes.fromhex(p))for p in event['records']]


class OriginalGeometryMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures';cls.fixture=json.loads(gzip.decompress((root/'geometry_metrics_original.json.gz').read_bytes()));cls.cases=cls.fixture['cases']
        assert len(cls.cases)==264
        for name,want in cls.fixture['parents'].items():assert hashlib.sha256((root/(name+'.json')).read_bytes()).hexdigest()==want

    def test_every_native_operand_running_store_and_raw_return(self):
        terms=reports=0
        for c in self.cases:
            self.assertEqual(c['signal'],0);self.assertIsNone(c['unfinished'])
            if not c['geom']:self.assertIn('Could not Find Spiral',c['stdout']);continue
            with self.subTest(label=c['label']):
                g,a=c['geom'][0],c['metalarea'][0];self.assertEqual(g['records'],a['records']);seen=[];length,area,metal=_portable(records(g),seen.append)
                self.assertEqual(bits(length),c['reports'][0]['length_bits']);self.assertEqual(bits(area),c['reports'][0]['area_bits']);self.assertEqual(bits(metal),c['reports'][1]['area_bits']);self.assertEqual(raw(metal),a['extended_bits'])
                self.assertEqual(len(seen),len(g['terms']));self.assertEqual(len(seen),len(a['terms']))
                for got,geom,metal in zip(seen,g['terms'],a['terms']):
                    for expected in(geom,metal):
                        self.assertEqual(got['segment'],expected['segment']);self.assertEqual(raw(got['length']),expected['length']);self.assertEqual(raw(got['width']),expected['width'])
                    self.assertEqual(bits(got['length_sum']),geom['length_sum_bits']);self.assertEqual(bits(got['area_sum']),geom['area_sum_bits']);self.assertEqual(raw(got['metal_area']),metal['accumulator']);terms+=1
                for e in(g,a):self.assertEqual(e['control_before'],0x37f);self.assertEqual(e['control_after'],0x37f)
                for e in c['reports']:self.assertEqual(e['control'],0x37f)
                reports+=1
        self.assertEqual(reports,260);self.assertEqual(terms,3007)

    def test_all_public_consumed_records_and_metrics(self):
        count=0
        for c in self.cases:
            if not c['geom']:continue
            with self.subTest(label=c['label']):
                tech=Technology.from_text(c['technology']);shape=_shape(c['public'],tech);before=repr(shape.segments);g=c['geom'][0]
                self.assertEqual(b''.join(struct.pack('<7d',*s.start,*s.end,s.width)for s in shape.segments),b''.join(bytes.fromhex(p)for p in g['records']))
                length,area,metal=retained_geometry_metrics(shape)
                self.assertEqual(bits(length),c['reports'][0]['length_bits']);self.assertEqual(bits(area),c['reports'][0]['area_bits']);self.assertEqual(bits(metal),c['reports'][1]['area_bits']);self.assertEqual(raw(metal),c['metalarea'][0]['extended_bits'])
                data=shape.to_dict();self.assertEqual(bits(data['length']),bits(length));self.assertEqual(bits(data['area']),bits(area));self.assertEqual(bits(data['metal_area']),bits(metal));self.assertEqual(repr(shape.segments),before);count+=1
        self.assertEqual(count,260)

    def test_bridge_native_metrics(self):
        c=next(c for c in self.cases if c['public']['kind']=='transformer3d');before=repr(c)
        r=handle(dict(c['public'],action='build',technology=c['technology']))
        self.assertEqual(bits(r['length']),c['reports'][0]['length_bits']);self.assertEqual(bits(r['area']),c['reports'][0]['area_bits']);self.assertEqual(bits(r['metal_area']),c['reports'][1]['area_bits']);self.assertEqual(repr(c),before)


class OriginalGeometryPrimitiveTests(unittest.TestCase):
    def test_original_threshold_extreme_and_nonfinite_words(self):
        cases=json.loads((Path(__file__).parent/'fixtures/geometry_primitives_original.json').read_text())['cases'];self.assertEqual(len(cases),538)
        from reasitic.geometry_metrics import _evaluate
        for c in cases:
            with self.subTest(label=c['label']):
                key=b''.join(bytes.fromhex(p)for p in c['records']);computed=_evaluate(key)
                for got,field in zip(computed,('length_bits','area_bits','metal_area_bits')):
                    self.assertEqual(bits(got),c[field])
                self.assertEqual(raw(computed[2]),c['metal_area_extended_bits'])

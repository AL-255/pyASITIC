"""Consumed original contact geometry at identical native segment inputs."""
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from reasitic.contact_geometry import groups
from reasitic.model import Shape,Segment
from reasitic.potential import Contact,_contacts

ROOT=Path(__file__).parent/'fixtures'


class OriginalContactGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads((ROOT/'contact_geometry_original.json').read_text())

    def test_every_original_physical_bound_grid_index_and_metal(self):
        f=self.fixture;self.assertEqual(len(f['cases']),50)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/(name+'.json')).read_bytes()).hexdigest(),digest)
        builders=contacts=invalid=0
        for case in f['cases']:
            self.assertTrue(case['success']);self.assertEqual((case['control_before'],case['control_after']),(0x37f,0x37f))
            o=case['options'];tech=SimpleNamespace(metals=[None]*o['metal_count'])
            for index,r in enumerate(case['records']):
                with self.subTest(parent=case['parent'],case=case['index'],builder=index):
                    before=repr(r);s=r['segment'];shape=Shape('Probe','wire',r['origin'],{},[Segment(*s['points'],s['width'],0.,s['metal'],s['nx'],s['ny'],s['primary_width'])])
                    expected=[item['indices']for item in r['contacts']]
                    seen=[]
                    valid=all(0<=a<b<=o['nx']and 0<=c<d<=o['ny']for a,b,c,d,_ in expected)
                    if valid:
                        actual=groups(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
                        self.assertEqual([[a.x0,a.x1,a.y0,a.y1,a.metal]for a in actual[0]],expected)
                        self.assertEqual(len(actual[0]),r['counts'][0]*r['counts'][1])
                    else:
                        with self.assertRaisesRegex(ValueError,'collapses'):groups(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact,observe=seen.append)
                        invalid+=1
                    self.assertEqual([struct.pack('<4d',*v).hex()for v in reversed(seen)],[item['bounds_bits']for item in r['contacts']])
                    self.assertEqual(repr(r),before)
                    builders+=1;contacts+=len(expected)
        self.assertEqual((builders,contacts,invalid),(280,338,1))

    def test_potential_wrapper_preserves_the_same_original_contact_records(self):
        for case in self.fixture['cases']:
            o=case['options'];tech=SimpleNamespace(metals=[None]*o['metal_count'])
            for r in case['records']:
                s=r['segment'];shape=Shape('Probe','wire',r['origin'],{},[Segment(*s['points'],s['width'],0.,s['metal'],s['nx'],s['ny'],s['primary_width'])])
                if any(not(0<=a<b<=o['nx']and 0<=c<d<=o['ny'])for a,b,c,d,_ in(item['indices']for item in r['contacts'])):
                    with self.assertRaisesRegex(ValueError,'collapses'):_contacts(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024)
                    continue
                actual=_contacts(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024)
                self.assertEqual([[a.x0,a.x1,a.y0,a.y1,a.metal]for a in actual[0]],[item['indices']for item in r['contacts']])

    def test_cached_contacts_preserve_edits_limits_and_caller_isolation(self):
        case=self.fixture['cases'][0];o=case['options'];r=case['records'][0];s=r['segment']
        tech=SimpleNamespace(metals=[None]*o['metal_count'])
        shape=Shape('Probe','wire',r['origin'].copy(),{},[Segment(*[p.copy()for p in s['points']],s['width'],0.,s['metal'],s['nx'],s['ny'],s['primary_width'])])
        def cached(maximum=1024):return _contacts(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],maximum)
        def fresh():return groups(shape,tech,o['nx'],o['ny'],o['width'],o['height'],o['length_step'],o['width_step'],1024,Contact)
        expected=fresh();initial=cached();self.assertEqual(initial,expected)
        initial[0].clear();initial.clear();self.assertEqual(cached(),expected)
        with self.assertRaisesRegex(ValueError,'contact limit'):cached(0)
        # Each edit changes an input used by the original geometry routines.
        shape.origin[0]+=o['width']/o['nx'];self.assertNotEqual(cached(),expected);self.assertEqual(cached(),fresh())
        shape.segments[0].end[0]+=o['width']/o['nx'];self.assertEqual(cached(),fresh())
        shape.segments[0].nx=shape.segments[0].ny=-1;self.assertEqual(cached(),fresh())

"""Original storage lifetimes, complete selected outcomes and cache provenance."""
import collections,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import capture_trailing_via_heap_original as capture
from audit_trailing_via_heap import compare
from reasitic import Technology
from reasitic.bridge import _shapes,_mesh
from reasitic.solver import discretize,filament_counts
from reasitic.network import _join_for_pads
from reasitic.potential import _contacts


class OriginalAllocationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/trailing_via_heap_original.json.gz').read_bytes()))

    def test_every_selected_job_cache_pair_and_capture_provenance(self):
        f=self.fixture;self.assertEqual(f['gdb_commands'],capture.COMMANDS);self.assertEqual(len(f['cases']),130)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        expected=list(capture.jobs());self.assertEqual(len(expected),65)
        for i,job in enumerate(expected):
            cold,warm=f['cases'][2*i:2*i+2]
            for c,mode in((cold,'cold'),(warm,'warm')):
                self.assertEqual(c['cache_mode'],mode)
                for key in('label','request','script','stdin','variant'):self.assertEqual(c[key],job[key])
                self.assertEqual(c['pending'],0);self.assertEqual(c['events'][0]['control'],0x37f)
                for name,value in(('process.tek',job['request']['technology']),('input.asit',job['script']),('answers.txt',job['stdin']),('capture.gdb',capture.COMMANDS)):
                    self.assertEqual(c['initial_files'][name],dict(size=len(value.encode()),sha256=hashlib.sha256(value.encode()).hexdigest()))
            self.assertEqual(cold['initial_cache'],{});self.assertTrue(cold['cache_after_plain']);self.assertEqual(warm['initial_cache'],cold['cache_after_plain']);self.assertEqual(warm['cache_after_plain'],warm['initial_cache'])
            for c in(cold,warm):
                generated='Generating data at'in c['stdout'];plain_generated='Generating data at'in c['plain']['stdout']
                self.assertEqual(generated,c['cache_mode']=='cold');self.assertEqual(plain_generated,generated)

    def test_all_original_requests_free_identities_and_fault_prefixes(self):
        node=0;faults=0;events=0;aliases=collections.Counter()
        for c in self.fixture['cases']:
            with self.subTest(label=c['label'],mode=c['cache_mode']):
                self.assertEqual(compare(c),[]);events+=sum(e['kind']in('allocate','free')for e in c['events']);v=c['via'];n=v['matrix']['size'];cap=c['matrices']['cap_output']['data']
                self.assertEqual(v['control_before'],0x37f)
                if c['node']is None:
                    faults+=1;self.assertEqual((c['label'],c['cache_mode'],c['signal']),('square/64/contacts','cold',11));self.assertIsNone(v['writes'][-1]['before']);self.assertNotIn('after',v['writes'][-1]);self.assertNotIn('return_status',v)
                else:
                    node+=1;self.assertEqual((c['signal'],v['control_after'],v['return_status'],c['node']['control']),(0,0x37f,1,0x37f));self.assertEqual(c['node']['cap_address'],cap);self.assertEqual(c['node']['ind_address'],v['matrix']['data'])
                for w in v['writes']:
                    self.assertEqual(len(bytes.fromhex(w['resistance_extended'])),10)
                    if w['index']<n:continue
                    delta=w['address']-cap;inside=0<=delta<16*n*n and delta%16==0
                    aliases[c['cache_mode']+('/CAP'if inside else'/outside-CAP')]+=1
                    if inside:self.assertEqual(delta,16*(n-1));self.assertNotEqual(w['before'],w['after'])
        self.assertEqual((node,faults,events),(129,1,12877));self.assertEqual(aliases,{'cold/CAP':25,'cold/outside-CAP':40,'warm/CAP':25,'warm/outside-CAP':40})
        self.assertEqual(collections.Counter(c['plain']['returncode']for c in self.fixture['cases']),{0:125,-6:3,-11:2})
        # The earlier experiment is kept intact and clearly separate: its GDB
        # run was warmed by its preceding cold plain run, not a same-state pair.
        earlier=json.loads(gzip.decompress((ROOT/'tests/fixtures/trailing_via_heap_mixed_cache_original.json.gz').read_bytes()));self.assertEqual(len(earlier['cases']),65)
        self.assertTrue(any(c['plain']['returncode']for c in earlier['cases']))

    def test_plan_dimensions_from_ported_geometry_contacts_and_filaments(self):
        for c in self.fixture['cases'][::2]:
            with self.subTest(label=c['label']):
                r=c['request'];tech=Technology.from_text(r['technology']);shapes=_shapes(r,tech);mesh=_mesh(r,tech);length=mesh['length_cell'];cap_length=mesh['capacitance_length_cell']
                if r['action']=='pi2':shape=discretize(shapes[r['winding']],cap_length,length)
                else:
                    a,b=(discretize(shapes[r[key]],cap_length,length)for key in('first_winding','second_winding'));b.segments.reverse();shape=_join_for_pads(a,b)
                chip=tech.chip;groups=_contacts(shape,tech,int(chip['fftx']),int(chip['ffty']),float(chip['chipx']),float(chip['chipy']),cap_length,mesh['capacitance_width_cell'])
                self.assertEqual([len(g)for g in groups],[len(g['contacts'])for g in c['contact_groups']])
                conductors=[s for s in shape.segments if s.metal<len(tech.metals)]
                filaments=sum(ny*nz for s in conductors for ny,nz in[filament_counts(s,mesh['width_cell'],mesh['thickness_cell'],500)])
                self.assertEqual(len(conductors),c['via']['matrix']['size']);self.assertEqual(filaments,c['matrices']['ind_full']['size']);self.assertEqual(len(shape.segments),len(c['via']['segments']))

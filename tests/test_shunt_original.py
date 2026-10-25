"""Original JOINSHUNT geometry graphs, native outcomes and branch GDS."""
import base64,copy,gzip,hashlib,importlib.util,json,struct,sys,tempfile,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import handle
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_shunt_original import run


class ShuntTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_original.json.gz').read_bytes()))

    def test_all_original_geometry_links_and_phase_words(self):
        report=run(self.fixture)
        self.assertEqual((report['cases'],report['states_checked'],report['records_checked'],report['coordinate_words_checked'],report['links_checked'],report['phase_words_checked']),(19,124,2871,51678,5742,211))
        self.assertEqual(report['differences'],0,json.dumps([r for r in report['results']if r['differences']],indent=2))

    def test_original_provenance_plain_faults_aliases_and_immutable_input(self):
        import capture_shunt_original as capture
        f=self.fixture;self.assertEqual(f['gdb_commands'],capture.COMMANDS)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual([c['label']for c in capture.jobs()],[c['label']for c in f['cases']])
        for c in f['cases']:
            with self.subTest(label=c['label']):
                fault=c['label']in('source-longer','duplicates');self.assertEqual((c['signal'],c['plain']['returncode']),(11,-11)if fault else(0,0))
                self.assertEqual(len(c['states']),len(c['operations'])+(0 if fault else 1))
                if fault:
                    with self.assertRaisesRegex(ValueError,'original JOINSHUNT faults'):handle(dict(c['public'],technology=c['technology'],action='build',edits=c['operations']))
                for state in c['states']:
                    self.assertEqual(state['control'],0x37f)
                    self.assertLessEqual(set(state['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
                    for shape in state['shapes']:
                        for parent in shape['segments']:
                            for record in(parent,*parent['secondary']):self.assertEqual(len(bytes.fromhex(record['raw'])),240)
        c=next(c for c in f['cases']if c['label']=='series/wire');index=next(i for i,op in enumerate(c['operations'])if op['command']=='JOINSHUNT')
        request=dict(c['public'],technology=c['technology'],action='build',edits=c['operations'][:index+1]);saved=copy.deepcopy(request);expected=handle(request)
        for alias in('JOINSHUNT','ADDSHUNT','MATESHUNT','SHUNT'):
            changed=copy.deepcopy(request);changed['edits'][-1]['command']=alias;self.assertEqual(handle(changed),expected)
        self.assertEqual(request,saved)
        c=next(c for c in f['cases']if c['label']=='self');self.assertEqual(handle(dict(c['public'],technology=c['technology'],action='build',edits=c['operations']))['windings'],[])

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_every_primary_and_parallel_branch_in_independent_gds_reader(self):
        import gdstk
        states=0
        with tempfile.TemporaryDirectory(prefix='pyasitic-shunt-gds-')as directory:
            path=Path(directory)/'layout.gds'
            for c in self.fixture['cases']:
                tech=Technology.from_text(c['technology'])
                for i,state in enumerate(c['states']):
                    with self.subTest(label=c['label'],state=i):
                        request=dict(c['public'],technology=c['technology'],edits=c['operations'][:i]);path.write_bytes(base64.b64decode(handle(dict(request,action='gds'))['base64']));polygons=gdstk.read_gds(str(path)).cells[0].polygons;position=0
                        for native in reversed(state['shapes']):
                            ox,oy=struct.unpack('<2d',bytes.fromhex(native['origin_bits']))
                            for parent in native['segments']:
                                for record in(parent,*parent['secondary']):
                                    if record['metal']<len(tech.metals):
                                        points=struct.unpack('<18d',bytes.fromhex(record['coordinates_bits']));expected=[(round((points[k]+ox)*1000),round((points[k+1]+oy)*1000))for k in(6,9,15,12)]
                                        self.assertEqual([tuple(round(v*1000)for v in point)for point in polygons[position].points],expected);self.assertEqual((polygons[position].layer,polygons[position].datatype),(record['metal']+1,0));position+=1
                                    else:
                                        index=record['metal']-len(tech.metals);via=tech.vias[index];layers=[via.bottom+1,via.top+1]+[100+index]*(record['nx']*record['ny'])
                                        self.assertEqual([p.layer for p in polygons[position:position+len(layers)]],layers);position+=len(layers)
                        self.assertEqual(position,len(polygons));states+=1
        self.assertEqual(states,124)


if __name__=='__main__':unittest.main()

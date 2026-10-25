"""Exact original breakup records, descriptor reuse, empty faults and GDS."""
import copy,gzip,hashlib,importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology
from reasitic.bridge import _shapes,handle

ROOT=Path(__file__).resolve().parents[1]
KINDS=dict(square=0,polygon=1,wire=2,transformer=3,balun=5,transformer3d=10,via=14,symmetric_square=16,symmetric_polygon=17,capacitor=21,multimetal=21,joined=21,ring=22)


def check_scene(test,c,state,edits):
    tech=Technology.from_text(c['technology']);request=dict(c['public'],technology=c['technology'],edits=edits);shapes,links=_shapes(request,tech,with_links=True)
    # Native prepends descriptors; the public scene displays creation order.
    expected=list(reversed(state['shapes']));test.assertEqual([s.name for s in shapes],[s['name']for s in expected]);words=0
    for i,(shape,native)in enumerate(zip(shapes,expected)):
        test.assertEqual(KINDS[shape.kind],native['native_kind']);test.assertEqual(struct.pack('<2d',*shape.origin).hex(),native['origin_bits']);test.assertEqual(len(shape.segments),len(native['segments']))
        test.assertEqual(shapes[links[i]].name if links[i]is not None else None,native['partner']);test.assertEqual(bool(shapes.dangling_partners[i]),native['dangling_partner'])
        if c['public']['kind']=='capacitor'and native['attributes']>0:test.assertGreater(shape.electrical_phase,0)
        else:test.assertEqual(shape.electrical_phase,native['attributes'])
        if hasattr(shape,'_native_divisions'):
            test.assertEqual(shape._native_divisions,native['native_n'])
            if shape._native_turns is not None:test.assertEqual(struct.pack('<d',shape._native_turns).hex(),native['turns_bits'])
        for segment,record in zip(shape.segments,native['segments']):
            test.assertEqual(struct.pack('<18d',*(v for p in segment.points for v in p)).hex(),record['coordinates_bits']);words+=18
            test.assertEqual(segment.metal,record['metal']);test.assertEqual(struct.pack('<d',segment.width).hex(),record['width_bits'])
            if'thickness_bits'in record:
                for value,key in((segment.thickness,'thickness_bits'),(segment.width if segment.primary_width is None else segment.primary_width,'primary_width_bits'),(segment.thickness if segment.primary_thickness is None else segment.primary_thickness,'primary_thickness_bits')):test.assertEqual(struct.pack('<d',value).hex(),record[key])
            else:test.assertEqual((segment.nx,segment.ny),(record['nx'],record['ny']))
    return shapes,links,words


class BreakupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/breakup_original.json.gz').read_bytes()))

    def test_all_original_coordinates_materials_headers_and_links(self):
        words=states=0;saved=copy.deepcopy(self.fixture)
        for c in self.fixture['cases']:
            for i,state in enumerate(c['states']):
                with self.subTest(label=c['label'],state=i):
                    self.assertEqual(state['control'],0x37f);_,_,count=check_scene(self,c,state,c['operations'][:i]);words+=count;states+=1
        self.assertEqual(self.fixture,saved);self.assertEqual(words,22788);self.assertEqual(states,111)

    def test_provenance_and_all_plain_observed_outcomes(self):
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        import capture_breakup_original as capture
        f=self.fixture;self.assertEqual(f['gdb_commands'],capture.COMMANDS);self.assertEqual(len(f['cases']),20)
        for name,digest in f['parents'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual([c['label']for c in capture.jobs()],[c['label']for c in f['cases']])
        for c in f['cases']:
            with self.subTest(label=c['label']):
                self.assertEqual((c['signal'],c['plain']['returncode']),(11,-11)if c['label']=='empty/fault'else(0,0))
                self.assertEqual(len(c['states']),len(c['operations'])+(0 if c['signal']else 1))
                if c['signal']:
                    with self.assertRaisesRegex(ValueError,'SPTOWIRE faults on an empty segment chain'):handle(dict(c['public'],technology=c['technology'],action='build',edits=c['operations']))
                for state in c['states']:self.assertLessEqual(set(state['environment']),{'PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','TERM','INPUTRC','LINES','COLUMNS','PWD','SHLVL','_'})
        c=next(c for c in f['cases']if c['label']=='series/wire');request=dict(c['public'],technology=c['technology'],action='build',edits=c['operations'][:1]);expected=handle(request)
        for alias in('SPTOWIRE','DEMOLISH','SP2WIRE','BREAKUP'):
            r=copy.deepcopy(request);r['edits'][0]['command']=alias;self.assertEqual(handle(r),expected)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_every_scene_through_independent_gds_reader(self):
        import base64,gdstk
        with tempfile.TemporaryDirectory(prefix='pyasitic-breakup-gds-')as directory:
            path=Path(directory)/'layout.gds'
            for c in self.fixture['cases']:
                tech=Technology.from_text(c['technology'])
                for i,state in enumerate(c['states']):
                    with self.subTest(label=c['label'],state=i):
                        request=dict(c['public'],technology=c['technology'],edits=c['operations'][:i]);path.write_bytes(base64.b64decode(handle(dict(request,action='gds'))['base64']));polygons=gdstk.read_gds(str(path)).cells[0].polygons;position=0
                        for native in reversed(state['shapes']):
                            ox,oy=struct.unpack('<2d',bytes.fromhex(native['origin_bits']))
                            for segment in native['segments']:
                                if segment['metal']<len(tech.metals):
                                    points=struct.unpack('<18d',bytes.fromhex(segment['coordinates_bits']));expected=[(round((points[k]+ox)*1000),round((points[k+1]+oy)*1000))for k in(6,9,15,12)]
                                    self.assertEqual([tuple(round(v*1000)for v in point)for point in polygons[position].points],expected);self.assertEqual((polygons[position].layer,polygons[position].datatype),(segment['metal']+1,0));position+=1
                                else:
                                    index=segment['metal']-len(tech.metals);via=tech.vias[index];layers=[via.bottom+1,via.top+1]+[100+index]*(segment['nx']*segment['ny'])
                                    self.assertEqual([p.layer for p in polygons[position:position+len(layers)]],layers);position+=len(layers)
                        self.assertEqual(position,len(polygons))


if __name__=='__main__':unittest.main()

"""Unchanged-original primitive names and interactive paired input boundaries."""
import gzip,hashlib,importlib.util,json,math,struct,tempfile,unittest
from pathlib import Path
from reasitic import Technology,build,build_device,write_gds
from reasitic.bridge import _shapes,handle,request_json
from reasitic.contact_geometry import groups
from reasitic.network import _join_for_pads
from reasitic.potential import Contact
from reasitic.solver import discretize
from reasitic.transformer import MODEL_KEYS

ROOT=Path(__file__).parent/'fixtures'
def fixture(name):return json.loads(gzip.decompress((ROOT/(name+'.json.gz')).read_bytes()))
def bits(value):return struct.pack('<d',value).hex()


class OriginalRemainingInteractiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bounds=fixture('paired_interactive_bounds_original');cls.names=fixture('primitive_names_original');cls.sessions=fixture('paired_interactive_bounds_sessions_original')
        assert len(cls.bounds['cases'])==20 and len(cls.names['cases'])==9 and len(cls.sessions['cases'])==3
        assert cls.sessions['parent_sha256']==hashlib.sha256((ROOT/'paired_interactive_bounds_original.json.gz').read_bytes()).hexdigest()

    def exact(self,shape,winding):
        self.assertEqual(shape.name,winding['name'])
        self.assertEqual(struct.pack('<2d',*shape.origin).hex(),winding.get('origin_bits',struct.pack('<2d',*winding['origin']).hex()))
        self.assertEqual(len(shape.segments),len(winding['segments']))
        for a,b in zip(shape.segments,winding['segments']):
            self.assertEqual(struct.pack('<18d',*(v for point in a.points for v in point)).hex(),b['coordinates_bits'])
            self.assertEqual(bits(a.width),b['width_bits']);self.assertEqual(a.metal,b['metal'])
            if 'thickness_bits'in b:self.assertEqual(bits(a.thickness),b['thickness_bits'])
            else:self.assertEqual((a.nx,a.ny),(b['nx'],b['ny']))

    def creations(self):
        for c in self.bounds['cases']:
            tech=Technology.from_text(c['technology']);shapes=build_device(c['kind'],technology=tech,native_interactive=True,**c['parameters'])
            yield c,tech,shapes,c['windings']
        tech=Technology.from_text(self.names['technology'])
        for c in self.names['cases']:yield c,tech,[build(c['kind'],technology=tech,native_interactive=True,**c['parameters'])],[c]

    def test_every_captured_name_coordinate_material_and_warning(self):
        total=0;saved=repr((self.bounds,self.names))
        for c,tech,shapes,windings in self.creations():
            with self.subTest(kind=c['kind'],parameters=c['parameters']):
                self.assertEqual((c['control_before'],c['control_after']),(0x37f,0x37f))
                for shape,winding in zip(shapes,windings):
                    self.exact(shape,winding);total+=18*len(shape.segments)
                    for warning in shape.warnings:self.assertIn(warning,c['stdout'])
        self.assertEqual(total,10296);self.assertEqual(repr((self.bounds,self.names)),saved)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_all_original_windings_through_independent_gds_reader(self):
        import gdstk
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'interactive.gds'
            for c,tech,shapes,windings in self.creations():
                path.write_bytes(write_gds(shapes,tech));library=gdstk.read_gds(path);polygons=library.cells[0].polygons;position=0
                self.assertEqual(library.unit,1e-6);self.assertEqual(library.precision,1e-9)
                for winding in windings:
                    for s in winding['segments']:
                        if s['metal']<len(tech.metals):
                            values=struct.unpack('<18d',bytes.fromhex(s['coordinates_bits']));ox,oy=winding['origin']
                            expected=[(round((values[k]+ox)*1000),round((values[k+1]+oy)*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in point)for point in polygons[position].points],expected)
                            self.assertEqual((polygons[position].layer,polygons[position].datatype),(s['metal']+1,0));position+=1
                        else:
                            index=s['metal']-len(tech.metals);via=tech.vias[index];expected=[via.bottom+1,via.top+1]+[100+index]*(s['nx']*s['ny'])
                            self.assertEqual([p.layer for p in polygons[position:position+len(expected)]],expected);position+=len(expected)
                self.assertEqual(position,len(polygons))

    def test_prompt_bounds_and_ignored_fields(self):
        for kind,index in [('balun',0),('transformer',10)]:
            c=self.bounds['cases'][index];tech=Technology.from_text(c['technology']);p=c['parameters']
            actual=build_device(kind,technology=tech,native_interactive=True,**dict(p,angle=999,phase=-1,secondary_turns=999))
            for shape,winding in zip(actual,c['windings']):self.exact(shape,winding)
            invalid=[dict(width=1e-11),dict(spacing=0),dict(spacing=1e-11),dict(spacing=513),dict(x=-1),dict(y=513)]
            invalid+=([dict(turns=2.99),dict(secondary_width=1e-11),dict(secondary_width=p['length'])]if kind=='balun'else[dict(turns=.99),dict(height=513)])
            for change in invalid:
                with self.subTest(kind=kind,change=change):
                    with self.assertRaises(ValueError):build_device(kind,technology=tech,native_interactive=True,**dict(p,**change))
        for kind in('wire','capacitor','via'):
            with self.assertRaisesRegex(ValueError,'Name'):build(kind,native_interactive=True,name='  \t  ')
        self.assertEqual(build('wire',name='miXed').name,'miXed')

    def test_complete_finite_coupled_sessions(self):
        for c in self.sessions['cases']:
            if c['parent_index']==6:continue
            with self.subTest(label=c['label']):
                saved=repr(c);self.assertEqual((c['signal'],c['pending']),(0,0));self.assertEqual(c['raw_output_bits'][:23],c['raw_output_bits'][23:])
                self.assertEqual(c['nodes'][0],c['nodes'][1]);self.assertEqual(len(c['records']),1)
                self.assertEqual((c['records'][0]['control_before'],c['records'][0]['control_after']),(0x37f,0x37f))
                r=handle(dict(c['request'],include_matrices=True));y,z=r['admittance_matrix'],r['impedance_matrix']
                actual=[v for cell in[y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1]]for v in cell]+[r['model'][k]for k in MODEL_KEYS]
                self.assertTrue(all(math.isfinite(struct.unpack('<d',bytes.fromhex(v))[0])for v in c['raw_output_bits']))
                self.assertEqual(list(map(bits,actual)),c['raw_output_bits'][:23]);self.assertEqual(c['records'][0]['Y'],c['raw_output_bits'][:8])
                self.assertEqual([bits(v)for row in r['scattering_matrix']for cell in row for v in cell],c['records'][0]['S'])
                for native,key in[('capacitance','capacitance_matrix'),('inductance','inductive_admittance_matrix')]:
                    event=c['nodes'][0];n=event['size'];self.assertEqual(b''.join(struct.pack('<2d',*r[key][i][j])for j in range(n)for i in range(n)).hex(),event[native])
                self.assertEqual(repr(c),saved)

    def test_original_nonfinite_capacitance_and_collapsed_grid_diagnostic(self):
        c=self.sessions['cases'][1];self.assertEqual(c['parent_index'],6);self.assertEqual((c['signal'],c['pending']),(0,0))
        self.assertEqual(c['raw_output_bits'][:23],c['raw_output_bits'][23:]);self.assertEqual(c['nodes'][0],c['nodes'][1])
        self.assertEqual(c['records'][0]['Y'],c['raw_output_bits'][:8]);self.assertEqual((c['records'][0]['control_before'],c['records'][0]['control_after']),(0x37f,0x37f))
        self.assertTrue(all(math.isnan(struct.unpack('<d',bytes.fromhex(v))[0])for v in c['raw_output_bits']+c['records'][0]['S']))
        values=lambda key:[v[0]for v in struct.iter_unpack('<d',bytes.fromhex(c['nodes'][0][key]))]
        self.assertTrue(all(map(math.isnan,values('capacitance'))));self.assertTrue(all(map(math.isfinite,values('inductance'))))
        request=c['request'];tech=Technology.from_text(request['technology']);a,b=[discretize(s,1000,1000)for s in _shapes(request,tech)];b.segments.reverse();joined=_join_for_pads(a,b)
        observed=[]
        with self.assertRaisesRegex(ValueError,'contact collapses'):
            groups(joined,tech,128,128,256,256,1000,1000,256,Contact,observe=observed.append)
        low_x,high_x,low_y,high_y=observed[-1]
        self.assertTrue(int(low_x/2)==int(high_x/2)or int(low_y/2)==int(high_y/2))
        with self.assertRaisesRegex(ValueError,'contact collapses'):handle(request)
        self.assertIn('contact collapses',json.loads(request_json(json.dumps(request)))['error'])

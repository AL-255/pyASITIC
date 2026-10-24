"""Exact original spatial-command histories, retained rotations and GDS exports."""
import copy,gzip,hashlib,importlib.util,json,math,struct,tempfile,unittest
from fractions import Fraction
from pathlib import Path
from reasitic import Technology,write_gds
from reasitic.bridge import _shapes,handle,request_json
from reasitic.editing import ALIASES
from reasitic.mutual_geometry import angle
from reasitic.precision import rotate_xy,_trig
from reasitic.retained_scalar import Real as R

ROOT=Path(__file__).parent/'fixtures'
def load(name):return json.loads(gzip.decompress((ROOT/(name+'.json.gz')).read_bytes()))
def bits(v):return struct.pack('<d',v).hex()
def raw(v):return struct.pack('<IIH',*v.words()).hex()


class OriginalSpatialEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=load('spatial_edits_original');cls.points=load('rotation_points_original')
        assert len(cls.fixture['cases'])==15 and sum(len(c['states'])for c in cls.fixture['cases'])==186
        for name,digest in cls.fixture['parents'].items():assert hashlib.sha256((ROOT/(name+'.json')).read_bytes()).hexdigest()==digest

    def states(self):
        for c in self.fixture['cases']:
            tech=Technology.from_text(c['technology'])
            for index,event in enumerate(c['states']):
                request=dict(c['public'],edits=c['operations'][:index])
                yield c,index,event,tech,request,_shapes(request,tech)

    def test_every_original_state_coordinate_material_and_origin(self):
        total=0;saved=copy.deepcopy(self.fixture);base_warnings={}
        for c,index,event,tech,request,shapes in self.states():
            with self.subTest(case=c['label'],state=index):
                self.assertEqual(event['control'],0x37f);expected={s['name']:s for s in event['shapes']};self.assertEqual(len(expected),len(shapes))
                for shape in shapes:
                    native=expected[shape.name];self.assertEqual(struct.pack('<2d',*shape.origin).hex(),native['origin_bits']);self.assertEqual(len(shape.segments),len(native['segments']))
                    for segment,target in zip(shape.segments,native['segments']):
                        self.assertEqual(struct.pack('<18d',*(v for p in segment.points for v in p)).hex(),target['coordinates_bits']);total+=18
                        self.assertEqual(bits(segment.width),target['width_bits']);self.assertEqual(segment.metal,target['metal'])
                        if 'thickness_bits'in target:
                            self.assertEqual(bits(segment.thickness),target['thickness_bits'])
                            self.assertEqual(bits(segment.primary_width if segment.primary_width is not None else segment.width),target['primary_width_bits'])
                            self.assertEqual(bits(segment.primary_thickness if segment.primary_thickness is not None else segment.thickness),target['primary_thickness_bits'])
                        else:self.assertEqual((segment.nx,segment.ny),(target['nx'],target['ny']))
                    if index==0:base_warnings[c['label'],shape.name]=shape.warnings.copy()
                    previous=base_warnings[c['label'],shape.name]
                    self.assertEqual(shape.warnings[:len(previous)],previous)
                    for warning in shape.warnings[len(previous):]:self.assertIn(warning,c['stdout'])
        self.assertEqual(total,29052);self.assertEqual(self.fixture,saved)

    @unittest.skipUnless(importlib.util.find_spec('gdstk'),'Install gdstk for independent GDS readback')
    def test_every_original_state_through_independent_gds_reader(self):
        import gdstk
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'edited.gds'
            for c,index,event,tech,request,shapes in self.states():
                outside=any(not -(1<<31)<=round((value+shape.origin[axis])*1000)<(1<<31)for shape in shapes for segment in shape.segments if segment.metal<len(tech.metals)for point in segment.polygon for axis,value in enumerate(point))
                if outside:
                    with self.assertRaisesRegex(ValueError,'signed 32-bit GDS coordinate range'):write_gds(shapes,tech)
                    self.assertIn('signed 32-bit GDS coordinate range',json.loads(request_json(json.dumps(dict(request,action='gds',technology=c['technology']))))['error'])
                    continue
                path.write_bytes(write_gds(shapes,tech));library=gdstk.read_gds(path);polygons=library.cells[0].polygons;position=0;expected={s['name']:s for s in event['shapes']}
                self.assertEqual((library.unit,library.precision),(1e-6,1e-9))
                for shape in shapes:
                    native=expected[shape.name];ox,oy=struct.unpack('<2d',bytes.fromhex(native['origin_bits']))
                    for target in native['segments']:
                        if target['metal']<len(tech.metals):
                            values=struct.unpack('<18d',bytes.fromhex(target['coordinates_bits']));points=[(round((values[k]+ox)*1000),round((values[k+1]+oy)*1000))for k in(6,9,15,12)]
                            self.assertEqual([tuple(round(v*1000)for v in p)for p in polygons[position].points],points);self.assertEqual((polygons[position].layer,polygons[position].datatype),(target['metal']+1,0));position+=1
                        else:
                            v=tech.vias[target['metal']-len(tech.metals)];layers=[v.bottom+1,v.top+1]+[100+target['metal']-len(tech.metals)]*(target['nx']*target['ny'])
                            self.assertEqual([p.layer for p in polygons[position:position+len(layers)]],layers);position+=len(layers)
                self.assertEqual(position,len(polygons))

    def test_original_retained_point_instructions_and_cancellation(self):
        self.assertEqual(len(self.points['points']),60);instructions=0
        for index,c in enumerate(self.points['points']):
            self.assertEqual(c['control'],0x37f);px,py,theta,cx,cy=struct.unpack('<5d',bytes.fromhex(c['input_bits']))
            self.assertEqual(struct.pack('<2d',*rotate_xy(px,py,cx,cy,theta)).hex(),c['output_bits'],index)
            x,y=R(px)-R(cx),R(py)-R(cy);radius=(x*x+y*y).sqrt();self.assertEqual(raw(radius),c['radius'])
            if 'polar'not in c:continue
            polar=angle(y,x);rotated=R(float(polar))+R(theta);cosine=R(_trig(rotated.value,True));sine=R(_trig(Fraction(float(rotated)),False))
            for key,value in [('polar',polar),('rotated',rotated),('cosine',cosine),('sine',sine),('x_accumulator',cosine*radius+R(cx)),('y_accumulator',sine*radius+R(cy))]:
                self.assertEqual(raw(value),c[key],(index,key));instructions+=1
        self.assertEqual(instructions,360)

    def test_aliases_error_boundaries_and_input_immutability(self):
        for x,y in[(-0.,0.),(0.,-0.),(-0.,-0.),(0.,0.)]:
            self.assertEqual(struct.pack('<2d',*rotate_xy(x,y,0.,0.,0.)),struct.pack('<2d',x,y))
        c=self.fixture['cases'][0];tech=Technology.from_text(c['technology']);request=dict(c['public']);before=copy.deepcopy(request)
        for alias,canonical in ALIASES.items():
            op=dict(command=alias,winding=0,x=.125,y=-.25,angle=17.123456789,name='TEMP',other=0,metal='M2')
            actual=_shapes(dict(request,edits=[op]),tech);expected=_shapes(dict(request,edits=[dict(op,command=canonical)]),tech)
            self.assertEqual([s.to_dict()for s in actual],[s.to_dict()for s in expected])
        for edits in ({},[None],[{}],[dict(command='unknown')],[dict(command='MOVE',winding=-1,x=1,y=1)],[dict(command='MOVE',winding=.5,x=1,y=1)],[dict(command='MOVE',winding=True,x=1,y=1)],[dict(command='MOVE',x=math.nan,y=1)]):
            response=json.loads(request_json(json.dumps(dict(request,action='build',edits=edits))))
            self.assertIn('error',response)
        self.assertEqual(request,before)

"""Original TRANS/BALUN descriptors and retained paired construction stores."""
import math,re
from .retained_scalar import Real as R
from .command_numbers import length_um,binary32,angle_radians,quantize_turns
from .model import Shape
from .geometry import _square
from .symmetric_geometry import symmetric_square

_UPPER=str.maketrans('abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ')


def _name(value):
    text=str(value).split('\0',1)[0]
    text=''.join(c for c in text if ord(c)>=32 and ord(c)!=127 or c in '\t\n\r\v\f')
    return re.sub(r'[ \t\n\r\v\f]+',' ',text).strip(' ').translate(_UPPER)


def construct(kind,tech,configs,parameters=None):
    shapes=[Shape(c['name'],kind,[c['x'],c['y']],dict(parameters or {},turns=c['turns']))for c in configs]
    for s,c in zip(shapes,configs):
        if kind=='transformer':_square(s,tech,c['metal'],c['exit_metal'],c['length'],c['height'],c['width'],c['spacing'],c['turns'],c['angle'],c['phase'])
        else:symmetric_square(s,tech,c['metal'],c['exit_metal'],c['length'],c['height'],c['width'],c['spacing'],c['turns'],c['angle'],c['phase'])
    primary,secondary=shapes;p,q=configs
    secondary.reflect(0)
    if kind=='balun':
        for segment in secondary.segments:segment.reverse()
        return shapes
    secondary.reflect(1)
    shift_a=R(p['width'])+(R(q['spacing'])-R(p['width']))*R(.5)
    for point in (secondary.segments[0].start,secondary.segments[0].outer_start,secondary.segments[0].inner_start):point[0]=float(R(point[0])+shift_a)
    shift_b=(R(p['spacing'])-R(q['width']))*R(.5)+R(q['width'])
    for point in (primary.segments[0].start,primary.segments[0].outer_start,primary.segments[0].inner_start):point[0]=float(R(point[0])-shift_b)
    offset=(R(q['spacing'])-R(q['width']))*R(.5)+R(q['width'])
    for axis in (0,1):primary.origin[axis]=float(offset+R(primary.origin[axis]))
    fraction=R(q['turns'])-R(math.floor(q['turns']))
    if q['exit_metal']!=-1:
        axis=0 if fraction in (R(.25),R(.75))else 1
        change=R(q['width'])if fraction in (R(.25),R(0))else-R(q['width'])
        primary.origin[axis]=float(R(primary.origin[axis])+change)
    return shapes


def build_paired(kind,tech,parameters):
    p=dict(parameters);keyword=bool(p.pop('native_keyword',False));interactive=bool(p.pop('native_interactive',False));warnings=[]
    if keyword and interactive:raise ValueError('Choose one native input mode')
    def number(key,default):
        v=float(p.get(key,default))
        if not math.isfinite(v):raise ValueError(f'{key} must be finite')
        return v
    if keyword:
        fields=[('length',100),('width',3),('spacing',2),('x',0),('y',0)]
        if kind=='transformer':fields.append(('height',p.get('length',100)))
        elif 'secondary_width'in p:fields.append(('secondary_width',p['secondary_width']))
        for key,default in fields:p[key]=length_um(p.get(key,default),grid_size=.1)
        p['turns']=binary32(float(p.get('turns',1.5 if kind=='transformer'else 3)))
        if kind=='transformer'and'secondary_turns'in p:p['secondary_turns']=binary32(float(p['secondary_turns']))
    length,width,spacing=number('length',100),number('width',3),number('spacing',2)
    x,y=number('x',0),number('y',0);angle=0. if interactive else number('angle',0)
    if min(length,width)<=0 or spacing<0 or max(length,width)>1e6 or abs(angle)>360:raise ValueError('Invalid transformer dimensions or orientation')
    if interactive:
        chipx=float(tech.chip.get('chipx',512));chipy=float(tech.chip.get('chipy',512))
        if not 0<=x<=chipx or not 0<=y<=chipy or(kind=='balun'and length>chipx):raise ValueError('Interactive paired dimensions/origin exceed chip bounds')
        angle=0.;p['angle']=0.
    radians=angle_radians(angle)if keyword else 0. if interactive else math.radians(angle)
    metal=tech.metal_index(p.get('metal',len(tech.metals)-1));name=str(p.get('name','T1'))
    if keyword and kind=='transformer':
        primary_name=_name(p.get('primary_name',name))
        if 'secondary_name'in p:secondary_name=_name(p['secondary_name'])
        else:primary_name,secondary_name=primary_name+'-p',primary_name+'-s'
    elif (keyword or interactive)and kind=='balun':primary_name,secondary_name=_name(name)+'-P',_name(name)+'-S'
    else:
        primary_name=str(p.get('primary_name',name+'-P'));secondary_name=str(p.get('secondary_name',name+'-S'))
        if interactive:primary_name,secondary_name=_name(primary_name),_name(secondary_name)
    if not all(0<len(n)<=79 and(not(keyword or interactive)or len(n.encode('utf8'))<=79) for n in (primary_name,secondary_name))or(not(keyword or interactive)and primary_name==secondary_name):raise ValueError('Windings need distinct names of 1–79 characters')
    chip=min(float(tech.chip.get('chipx',512)),float(tech.chip.get('chipy',512)))
    if kind=='transformer':
        height=number('height',length)
        if not 0<height<=1e6:raise ValueError('Invalid transformer height')
        if (keyword or interactive)and max(length,height)>chip:raise ValueError('Spiral dimensions exceed chip dimension')
        if interactive and not all(1e-10<=v<=min(length,height)for v in(width,spacing)):raise ValueError('Interactive transformer width/spacing exceed dimensions or are too small')
        internal=float(R(spacing)+R(spacing)+R(width));raw=number('turns',1.5)
        other=raw if interactive else number('secondary_turns',raw)
        if interactive:
            maximum=quantize_turns(((R(min(length,height))+R(internal))/(R(width)+R(internal)))*R(.5),4,keyword=False)
        else:maximum=quantize_turns(R(min(length,height))/((R(width)+R(internal))*R(2))-R(.25),4,keyword=True)
        if min(raw,other)<(1 if interactive else 0)or max(raw,other)>maximum:raise ValueError(f'Transformer windings support at most {float(maximum):g} turns')
        turns=float(quantize_turns(raw,4,keyword=not interactive));secondary_turns=float(quantize_turns(other,4,keyword=not interactive))
        if min(turns,secondary_turns)<=0 or max(turns,secondary_turns)>1000:raise ValueError('Invalid transformer turn count')
        exit_value=p.get('exit_metal',len(tech.metals)-2 if keyword else -1)
        exit_metal=-1 if str(exit_value)=='-1'else tech.metal_index(exit_value)
        p.setdefault('exit_metal',exit_metal)
        if exit_metal==metal:raise ValueError('Exit metal must differ from the winding metal')
        phase=1 if interactive else number('phase',1)
        if keyword:
            if not -(1<<31)<=phase<(1<<31):raise ValueError('Phase exceeds the native integer range')
            phase=int(phase)or 1;p['phase']=phase
        if keyword and'secondary_width'in p:
            warnings.append('Warning:  WS!=WP not currently supported.  Taking WS=WP.');p['secondary_width']=width
        configs=[dict(name=n,length=length,height=height,width=width,spacing=internal,turns=t,angle=radians,metal=metal,exit_metal=exit_metal,phase=phase,x=x,y=y)for n,t in [(primary_name,turns),(secondary_name,secondary_turns)]]
    else:
        second_width=number('secondary_width',width);raw=number('turns',3)
        if interactive:raw=float(math.floor(raw))
        if second_width<=0 or second_width>1e6 or(not keyword and raw<3):raise ValueError('Balun needs at least three total turns and positive winding widths')
        if interactive:
            if not all(1e-10<=v<=min(length,chipx,chipy)for v in(width,spacing)):raise ValueError('Interactive balun width/spacing exceed dimensions or are too small')
            inset=R(width)+R(spacing);secondary_length=float(R(length)-(inset+inset))
            if not 1e-10<=second_width<=min(secondary_length,chipx,chipy):raise ValueError('Interactive secondary width exceeds dimensions or is too small')
            lower=int(tech.chip.get('fftx',128))
            if length<lower:warnings.append(f'Warning:  Dimension less than {lower:5.2f}')
            maximum=quantize_turns(((R(length)+R(spacing))/(R(width)+R(spacing)))*R(.5),4,keyword=False)
            if raw>maximum:raise ValueError(f'Interactive balun supports at most {float(maximum):g} total turns')
            raw=float(quantize_turns(raw,4,keyword=False))
        primary_turns=float(math.floor(((R(raw)+R(1))*R(.5)).value));secondary_turns=float(R(primary_turns)-R(1))
        twice=R(spacing)+R(spacing)
        gap=float(R(width)+R(second_width)+twice)if interactive else float(twice+R(width)+R(second_width))
        primary_space,secondary_space=float(twice+R(second_width)),float(twice+R(width))
        inset=R(width)+R(spacing)
        second_length=float(R(length)-(inset+inset))if interactive else float(R(length)-(((R(spacing)+R(width))+R(spacing))+R(width)))
        if keyword and max(length,gap)>chip:raise ValueError('Spiral dimensions exceed chip dimension')
        maximum=quantize_turns(R(length)/((R(width)+R(primary_space))*R(2))-R(.25),4,keyword=True)
        if not interactive and primary_turns>maximum:raise ValueError(f'Balun primary supports at most {float(maximum):g} turns')
        if max(primary_turns,secondary_turns)>1000:raise ValueError('Invalid balun turn count')
        if not(keyword or interactive):
            second_max=math.floor((R(second_length)/((R(second_width)+R(secondary_space))*R(2))-R(.25)).value)
            if secondary_turns>second_max:raise ValueError(f'Symmetric winding supports 1–{second_max} turns')
        secondary_metal=tech.metal_index(p.get('secondary_metal',len(tech.metals)-2 if keyword else max(0,metal-1)))
        supplied_transition='secondary_metal'in p
        p.setdefault('secondary_metal',secondary_metal)
        if (keyword and supplied_transition or interactive)and secondary_metal==metal:raise ValueError('Illegal transition metal layer')
        phase=0 if interactive else 1
        configs=[dict(name=primary_name,length=length,height=gap,width=width,spacing=primary_space,turns=primary_turns,angle=radians,metal=metal,exit_metal=secondary_metal,phase=phase,x=x,y=y),dict(name=secondary_name,length=second_length,height=gap,width=second_width,spacing=secondary_space,turns=secondary_turns,angle=radians,metal=metal,exit_metal=secondary_metal,phase=phase,x=float(R(x)+R(width)+R(spacing)),y=float(R(y)+R(width)+R(spacing)))]
    shapes=construct(kind,tech,configs,p)
    for shape in shapes:shape.warnings.extend(warnings)
    return shapes

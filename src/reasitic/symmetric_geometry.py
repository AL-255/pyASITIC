"""Direct state-machine ports of symmetric_construction.cpp."""
import copy
from .retained_scalar import Real as R
from .polygon import PI, _trig
from .geometry import _segment, _via_pair

try:
    from _reasitic_numeric import symmetric_geometry as _compiled_geometry
except ImportError:
    _compiled_geometry=None


def _compiled(shape,tech,kind,primary,secondary,dimension,sides,height,width,spacing,turns,angle,phase):
    if _compiled_geometry is None:return False
    from array import array
    config=array('d',[kind,primary,secondary,dimension,sides,height,width,spacing,turns,angle])
    capacity=min(60000,int(turns*(sides+6 if kind else 12))+2)
    output=array('d',[0.])*(capacity*14)
    count=_compiled_geometry(config,output)
    if count<0:raise ValueError('Invalid symmetric geometry configuration')
    for i in range(count):
        row=output[i*14:(i+1)*14];metal=int(row[1])
        if row[0]:_via_pair(shape,tech,metal,primary,width,row[2],row[3],int(row[4]))
        else:
            v=row[2:];shape.segments.append(_segment(tech,metal,width,*[v[j:j+2]for j in range(0,12,2)]))
    if kind==0:shape.rotate(angle)
    if phase<0:
        for segment in shape.segments:segment.reverse()
    return True


def _collapse(s):
    s.start = s.end.copy()
    s.outer_start = s.outer_end.copy()
    s.inner_start = s.inner_end.copy()


def _extend(direction,s,length,inset):
    _collapse(s)
    length,inset=R(length),R(inset)
    if direction>1:
        inset += inset
    sign = 1 if direction in (0,3) else -1
    axis = 1 if direction<2 else 0
    s.outer_end[axis] = float(R(sign)*length+R(s.outer_end[axis]))
    s.inner_end[axis] = float(R(sign)*(length-inset)+R(s.inner_end[axis]))
    s.end[axis] = float(R(sign)*(length-inset*R(.5))+R(s.end[axis]))


def _bridge(direction,s,height,width,spacing):
    _collapse(s)
    sx,sy = {4:(-1,1),5:(1,1),6:(-1,-1),7:(1,-1)}[direction]
    dx,dy=(R(spacing)+R(width))*R(sx),(R(height)-R(0))*R(sy)
    for point in (s.inner_end,s.outer_end,s.end):
        point[0] = float(R(point[0])+dx)
        point[1] = float(R(point[1])+dy)


def _metal(s,index,tech):
    metal = tech.metals[index]
    s.metal,s.thickness = index,metal.thickness
    for point in s.points:
        point[2] = metal.geometry_height


def symmetric_square(shape,tech,primary,secondary,span,height,width,spacing,turns,angle,phase):
    if _compiled(shape,tech,0,primary,secondary,span,4,height,width,spacing,turns,angle,phase):return
    initial_y=float(R(span)*R(.5)+R(height))
    s = _segment(tech,primary,width,(0,0),(float(R(width)*R(.5)),initial_y),
                 (0,0),(0,initial_y),(0,0),(width,initial_y))
    vertical,progress,state,side,bridge_metal = float((R(span)-R(height))*R(.5)),0,0,0,primary
    while R(progress)<=R(turns)-R(.5):
        progress += .25
        side += 1
        selected = primary
        if state>3:
            bridge_metal = secondary if bridge_metal==primary else primary
            selected = bridge_metal
        _metal(s,selected,tech)
        if state==0:
            _extend(0,s,vertical,width)
            state = 3 if side<3 else 5
        elif state==1:
            _extend(1,s,vertical,width)
            state = 2 if side<3 else 6
        elif state==2:
            _extend(2,s,span,width)
            state = 0
        elif state==3:
            _extend(3,s,span,width)
            state = 1
        else:
            direction = state
            first_y = -1 if state==5 else 1
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],first_y)
            _bridge(direction,s,height,width,spacing)
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],-first_y)
            pitch=R(width)+R(spacing)
            span = float(R(span)-(pitch+pitch))
            vertical = float(R(vertical)-pitch)
            state = 0 if direction==5 else 1
            side = 0
        shape.segments.append(copy.deepcopy(s))
    _collapse(s)
    down = state==6
    for _ in range(2):
        for point in (s.outer_end,s.inner_end,s.end):
            center=R(height)*R(.5)
            point[1] = float(R(point[1])-center if down else R(point[1])+center)
        shape.segments.append(copy.deepcopy(s))
        _collapse(s)
    state,side = (1 if down else 0),0
    while progress>0:
        progress -= .25
        side += 1
        selected = primary
        if state>3:
            bridge_metal = secondary if bridge_metal==primary else primary
            selected = bridge_metal
        _metal(s,selected,tech)
        if state==0:
            _extend(0,s,vertical,width)
            state = 3 if side<3 else 4
        elif state==1:
            _extend(1,s,vertical,width)
            state = 2 if side<3 else 7
        elif state==2:
            _extend(2,s,span,width)
            state = 0
        elif state==3:
            _extend(3,s,span,width)
            state = 1
        else:
            direction = state
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],-1)
            _bridge(direction,s,height,width,spacing)
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],1)
            pitch=R(width)+R(spacing)
            span = float((pitch+pitch)+R(span))
            vertical = float(pitch+R(vertical))
            state = 0 if direction==4 else 1
            side = 0
        shape.segments.append(copy.deepcopy(s))
    shape.rotate(angle)
    if phase<0:
        for segment in shape.segments:
            segment.reverse()


def symmetric_polygon(shape,tech,primary,secondary,radius,sides,height,width,spacing,turns,angle,phase):
    if _compiled(shape,tech,1,primary,secondary,radius,sides,height,width,spacing,turns,angle,phase):return
    step = float((R(PI)+R(PI))/R(sides))
    s = _segment(tech,primary,width,*([(0,0)]*6))
    initial_half = R(height)*R(.5)
    half = float(initial_half)
    bridge_metal = 0  # initialized ConsoleGeometryState history.polygon_metal
    def endpoint(outer_angle,offset,initial=False):
        c = R(float(_trig(R(PI)/R(sides),True)))
        cosine,sine=_trig(R(angle),True),_trig(R(angle),False)
        # INNER is the larger radius in the original segment representation.
        s.inner_end[0] = float(_trig(outer_angle,True)*R(radius))
        inner_y=sine*R(radius)
        s.inner_end[1] = float((R(float(inner_y))if initial else inner_y)+offset)
        center=R(radius)-R(width)/(c+c)
        s.end[:2] = [float(cosine*center),float(center*sine+offset)]
        outer=R(radius)-R(width)/c
        s.outer_end[:2] = [float(cosine*outer),float(sine*outer+offset)]
    endpoint(R(angle),initial_half,True)
    limit=float(R(turns)+R(turns))
    for turn in range(1,int(limit)+1):
        for _ in range(sides//2):
            _collapse(s)
            next_angle=R(angle)+R(step)
            angle = float(next_angle)
            endpoint(next_angle,R(half))
            shape.segments.append(copy.deepcopy(s))
        half = -half
        _collapse(s)
        if turn==limit:
            break
        if turn==turns:
            shift=R(half)+R(half)
            for point in (s.inner_end,s.outer_end,s.end):
                point[1] = float(R(point[1])+shift)
        else:
            bridge_metal = secondary if bridge_metal==primary else primary
            _metal(s,bridge_metal,tech)
            radial = (R(width)+R(spacing))/_trig(R(PI)/R(sides),True)
            inward = turn<turns
            radius = float(R(radius)-radial if inward else radial+R(radius))
            negative = half<0
            direction = (7 if negative else 4) if inward else (6 if negative else 5)
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],1 if negative else -1)
            _bridge(direction,s,height,width,spacing)
            _via_pair(shape,tech,bridge_metal,primary,width,s.end[0],s.end[1],1 if direction in (4,5) else -1)
        shape.segments.append(copy.deepcopy(s))
        _metal(s,primary,tech)
    if phase<0:
        for segment in shape.segments:
            segment.reverse()

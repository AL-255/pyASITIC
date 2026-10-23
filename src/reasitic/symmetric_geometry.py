"""Direct state-machine ports of symmetric_construction.cpp."""
import copy
import math
from .geometry import _segment, _via_pair


def _collapse(s):
    s.start = s.end.copy()
    s.outer_start = s.outer_end.copy()
    s.inner_start = s.inner_end.copy()


def _extend(direction,s,length,inset):
    _collapse(s)
    if direction>1:
        inset *= 2
    sign = 1 if direction in (0,3) else -1
    axis = 1 if direction<2 else 0
    s.outer_end[axis] += sign*length
    s.inner_end[axis] += sign*(length-inset)
    s.end[axis] += sign*(length-inset/2)


def _bridge(direction,s,height,width,spacing):
    _collapse(s)
    sx,sy = {4:(-1,1),5:(1,1),6:(-1,-1),7:(1,-1)}[direction]
    for point in (s.inner_end,s.outer_end,s.end):
        point[0] += (spacing+width)*sx
        point[1] += height*sy


def _metal(s,index,tech):
    metal = tech.metals[index]
    s.metal,s.thickness = index,metal.thickness
    for point in s.points:
        point[2] = metal.height


def symmetric_square(shape,tech,primary,secondary,span,height,width,spacing,turns,angle,phase):
    s = _segment(tech,primary,width,(0,0),(width/2,span/2+height),
                 (0,0),(0,span/2+height),(0,0),(width,span/2+height))
    vertical,progress,state,side,bridge_metal = (span-height)/2,0,0,0,primary
    while progress<=turns-.5:
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
            span -= 2*(width+spacing)
            vertical -= width+spacing
            state = 0 if direction==5 else 1
            side = 0
        shape.segments.append(copy.deepcopy(s))
    _collapse(s)
    down = state==6
    for _ in range(2):
        for point in (s.outer_end,s.inner_end,s.end):
            point[1] += -height/2 if down else height/2
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
            span += 2*(width+spacing)
            vertical += width+spacing
            state = 0 if direction==4 else 1
            side = 0
        shape.segments.append(copy.deepcopy(s))
    shape.rotate(angle)
    if phase<0:
        for segment in shape.segments:
            segment.reverse()


def symmetric_polygon(shape,tech,primary,secondary,radius,sides,height,width,spacing,turns,angle,phase):
    step = 2*math.pi/sides
    s = _segment(tech,primary,width,*([(0,0)]*6))
    half = height/2
    bridge_metal = 0  # initialized ConsoleGeometryState history.polygon_metal
    def endpoint():
        c = math.cos(math.pi/sides)
        # Native names are inverted here: INNER is the larger radial edge.
        s.inner_end[:2] = [math.cos(angle)*radius,math.sin(angle)*radius+half]
        s.end[:2] = [math.cos(angle)*(radius-width/(2*c)),math.sin(angle)*(radius-width/(2*c))+half]
        s.outer_end[:2] = [math.cos(angle)*(radius-width/c),math.sin(angle)*(radius-width/c)+half]
    endpoint()
    for turn in range(1,turns*2+1):
        for _ in range(sides//2):
            _collapse(s)
            angle += step
            endpoint()
            shape.segments.append(copy.deepcopy(s))
        half = -half
        _collapse(s)
        if turn==turns*2:
            break
        if turn==turns:
            for point in (s.inner_end,s.outer_end,s.end):
                point[1] += 2*half
        else:
            bridge_metal = secondary if bridge_metal==primary else primary
            _metal(s,bridge_metal,tech)
            radial = (width+spacing)/math.cos(math.pi/sides)
            inward = turn<turns
            radius += -radial if inward else radial
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

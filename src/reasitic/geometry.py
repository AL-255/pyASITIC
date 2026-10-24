"""Direct ports of shape_construction, spiral_construction and winding_construction.

Python uses binary64 arithmetic rather than the reference's x87 intermediates;
the algorithm and ribbon construction are preserved, not bitwise rounding.
"""
import copy
import math
from .model import Shape, Segment
from .technology import Technology

KINDS = ("square", "polygon", "symmetric_square", "symmetric_polygon", "wire", "ring", "via", "capacitor", "multimetal")


def _segment(tech, metal, width, start, end, outer_start, outer_end, inner_start, inner_end):
    m = tech.metals[metal]
    def point(p):
        return [float(p[0]), float(p[1]), m.geometry_height]
    return Segment(*(point(p) for p in (start, end, outer_start, outer_end, inner_start, inner_end)),
                   width, m.thickness, metal)


def _via(tech, index, nx, ny, x=0, y=0):
    v = tech.vias[index]
    length = (nx-1)*v.spacing+v.width*nx
    height = v.width*ny+v.spacing*(ny-1)
    left, right = x-length/2, x+length/2
    top, bottom = y+height/2, y-height/2
    low, high = tech.metals[v.bottom].geometry_height, tech.metals[v.top].geometry_height
    return Segment([left,y,low], [right,y,high], [left,top,low], [right,top,high],
                   [left,bottom,low], [right,bottom,high], height, 0,
                   len(tech.metals)+index, nx, ny)


def _via_pair(shape, tech, a, b, width, x, y, dy=0):
    if a == b or not tech.vias:
        return
    for i, v in enumerate(tech.vias):
        if {v.bottom, v.top} == {a,b}:
            overplot = max(v.overplot1, v.overplot2)
            count = int((width-2*overplot+v.spacing)/(v.spacing+v.width))
            if count <= 0:
                shape.warnings.append("Insufficient space to insert via.")
            else:
                radius = ((count-1)*v.spacing+count*v.width)/2+overplot
                shape.segments.append(_via(tech, i, count, count, x, y+radius*dy))
            return
    shape.warnings.append(f"No via layer connects metal {a} to metal {b}.")


def _square(shape, tech, metal, exit_metal, dx, dy, width, spacing, turns, angle, phase):
    full = int(turns)
    fraction = int(turns*4-full*4)
    pitch, half = width+spacing, width/2
    current = None
    last_raw = None
    direction = 0
    for turn in range(1, full+2):
        direction = 0
        if turn == full+1 and fraction == 0:
            shape.segments[-1].end[1] = shape.segments[-1].inner_end[1]-width
            shape.segments[-1].outer_end[1] = shape.segments[-1].inner_end[1]
            break
        shift = pitch*(turn-1)
        x1, y1 = dx-shift, dy-shift
        ix, iy = x1-width, y1-width
        cx, cy = x1-half, y1-half
        so = 0 if turn == 1 else pitch*(turn-2)
        si = 0 if turn == 1 else so+width
        sp = 0 if turn == 1 else so+half
        lo, lc = shift+width, shift+half
        next_y = dy-pitch*turn
        records = [
            ((sp,cy),(cx,cy),(so,y1),(x1,y1),(si,iy),(ix,iy)),
            ((cx,cy),(cx,lc),(x1,y1),(x1,shift),(ix,iy),(ix,lo)),
            ((cx,lc),(lc,lc),(x1,shift),(shift,shift),(ix,lo),(lo,lo)),
            ((lc,lc),(lc,next_y-half),(shift,shift),(shift,next_y),(lo,lo),(lo,next_y-width)),
        ]
        for side, record in enumerate(records, 1):
            current = _segment(tech, metal, width, *record)
            # The native local record is copied before the final end is trimmed.
            last_raw = copy.deepcopy(current)
            shape.segments.append(current)
            direction = side if side < 4 else 0
            if turn == full+1 and fraction == side:
                axis = 0 if side in (1,3) else 1
                sign = -1 if side == 1 else 1
                current.end[axis] = current.inner_end[axis]+sign*width
                current.outer_end[axis] = current.inner_end[axis]
                break
        if turn == full+1:
            break
    tail = shape.segments[-1]
    if exit_metal >= 0:
        vx = -1 if direction == 1 else 1 if direction == 3 else 0
        vy = -1 if direction == 0 else 1 if direction == 2 else 0
        _via_pair(shape, tech, metal, exit_metal, width,
                  last_raw.end[0]+width*vx, last_raw.end[1]+width*vy)
        outer_start, inner_start, start = tail.outer_end[:2], tail.inner_end[:2], tail.end[:2]
        if direction in (1,3):
            delta = -width if direction == 1 else width
            outer_start[0] += delta
            inner_start[0] += delta
            end = [width+dx if direction == 1 else -width, start[1]]
            outer_end, inner_end = [end[0],outer_start[1]], [end[0],inner_start[1]]
        else:
            delta = -width if direction == 0 else width
            outer_start[1] += delta
            inner_start[1] += delta
            end = [start[0], width+dy if direction == 0 else -width]
            outer_end, inner_end = [outer_start[0],end[1]], [inner_start[0],end[1]]
        # Native exit construction updates heights and metal, retaining the
        # winding thickness in the local segment record.
        s = _segment(tech, exit_metal, width, start, end, outer_start, outer_end, inner_start, inner_end)
        s.thickness = tech.metals[metal].thickness
        shape.segments.append(s)
    else:
        axis = 0 if direction in (1,3) else 1
        delta = width if direction in (0,1) else -width
        tail.inner_end[axis] += delta
        tail.end[axis] = tail.outer_end[axis] = tail.inner_end[axis]
    shape.rotate(angle)
    if phase < 0:
        for s in shape.segments:
            s.reverse()


def _polygon(shape, tech, metal, radius, sides, width, spacing, turns, angle):
    ribbon = width/math.cos(math.pi/sides)
    shrink = ((width+spacing)*turns)/math.cos(math.pi/sides)
    decrement = (radius-(radius-shrink))/(turns*sides)
    for turn in range(1, int(turns+1)+1):
        def vertex(theta, r):
            return ((math.cos(theta)*r,math.sin(theta)*r),
                    (math.cos(theta)*(r-ribbon/2),math.sin(theta)*(r-ribbon/2)),
                    (math.cos(theta)*(r-ribbon),math.sin(theta)*(r-ribbon)))
        outer, center, inner = vertex(angle, radius)
        count = int((turns-math.floor(turns))*sides+1/(sides*2)) if turn == int(turns+1) else sides
        for side in range(1,count+1):
            radius -= decrement
            if radius < 1e-10:
                raise ValueError("Spiral radius exhausted")
            next_outer, next_center, next_inner = vertex(2*math.pi*side/sides+angle, radius)
            shape.segments.append(_segment(tech, metal, width, center, next_center,
                                           outer, next_outer, inner, next_inner))
            outer, center, inner = next_outer, next_center, next_inner
    x0,y0,x1,y1 = shape.bounds
    shape.offset((x1-x0)/2,(y1-y0)/2)


def _ring(shape, tech, metal, radius, sides, width, gap, angle):
    gap = abs(gap)
    step = (2*math.pi-gap)/(sides-1)
    ribbon = width/math.cos(math.pi/sides)
    def vertex(theta):
        return [(math.cos(theta)*r,math.sin(theta)*r)
                for r in (radius,radius-ribbon/2,radius-ribbon)]
    outer,center,inner = vertex(gap/2+angle)
    for i in range(1,sides):
        theta = angle-gap/2 if i == sides-1 else step*i+gap/2+angle
        no,nc,ni = vertex(theta)
        shape.segments.append(_segment(tech, metal, width, center,nc,outer,no,inner,ni))
        outer,center,inner = no,nc,ni
    x0,y0,x1,y1 = shape.bounds
    shape.offset((x1-x0)/2,(y1-y0)/2)


def build(kind="square", *, technology=None, **parameters):
    """Build a shape using micrometre dimensions and degree orientation/gap.

    `length` / `height` are outer square dimensions; `radius` is the native
    polygon vertex radius. Fractional turns are truncated to 1/sides, as ASITIC
    does. Origin is a separate translation and is never folded into segments.
    """
    tech = technology or Technology.default()
    kind = kind.lower()
    if kind not in KINDS:
        raise ValueError(f"Unsupported generator: {kind}")
    p = dict(parameters)
    def num(key, default):
        value = float(p.get(key, default))
        if not math.isfinite(value):
            raise ValueError(f"{key} must be finite")
        return value
    name = str(p.get("name", "L1"))
    if not name or len(name)>79:
        raise ValueError("Name must have 1–79 characters")
    width = num("width", 5)
    length, height = num("length", 100), num("height", p.get("length",100))
    spacing, radius = num("spacing", 2), num("radius", 50)
    sides_value = num("sides", 16)
    sides = int(sides_value)
    if kind in ("polygon","ring","symmetric_polygon") and (sides != sides_value or not 3 <= sides <= 1024):
        raise ValueError("Sides must be an integer from 3 to 1024")
    angle = num("angle",0)
    if abs(angle) > 360:
        raise ValueError("Orientation must be between −360 and 360 degrees")
    if width <= 0 or min(length,height,radius) <= 0 or spacing < 0:
        raise ValueError("Dimensions must be positive and spacing nonnegative")
    if max(width,length,height,radius) > 1e6:
        raise ValueError("Dimensions must not exceed 1,000,000 µm")
    phase = num("phase",1)
    metal = tech.metal_index(p.get("metal", len(tech.metals)-1))
    exit_value = p.get("exit_metal", -1)
    exit_metal = -1 if str(exit_value) in ("-1","none","") else tech.metal_index(exit_value)
    shape = Shape(name,kind,[num("x",0),num("y",0)],p)
    radians = math.radians(angle)
    if kind in ("symmetric_square","symmetric_polygon"):
        from .symmetric_geometry import symmetric_square, symmetric_polygon
        inner_gap = num("inner_gap",width+spacing)
        if inner_gap<=0:
            raise ValueError("Inner transition gap must be positive")
        secondary = tech.metal_index(p.get("secondary_metal",max(0,metal-1)))
        raw_turns = num("turns",2)
        turns = math.floor(raw_turns)
        if kind == "symmetric_polygon":
            if sides%2:
                sides -= 1
                shape.warnings.append(f"Symmetric polygon sides reduced to even count {sides}.")
            if sides<4:
                raise ValueError("Symmetric polygon requires at least four sides")
            maximum = math.floor(radius*math.cos(math.pi/sides)/(width+spacing))
        else:
            maximum = math.floor(length/(2*(width+spacing))-.25)
        if not 1<=raw_turns<=maximum or turns*sides>20000:
            raise ValueError(f"Symmetric winding supports 1–{maximum} turns")
        if raw_turns!=turns:
            shape.warnings.append(f"Turns quantized to {turns} (whole turns for symmetric coils).")
        shape.parameters["turns"] = turns
        hypotenuse = math.hypot(inner_gap,spacing)
        if width>hypotenuse:
            raise ValueError("Need more space for transitions")
        half = (math.pi-math.atan2(inner_gap,spacing)-math.acos(width/hypotenuse))/2
        if 2*width*math.tan(half)>inner_gap-1e-10:
            raise ValueError("Need more space for transitions")
        if kind == "symmetric_square":
            symmetric_square(shape,tech,metal,secondary,length,inner_gap,width,spacing,turns,radians,phase)
        else:
            symmetric_polygon(shape,tech,metal,secondary,radius,sides,inner_gap,width,spacing,turns,radians,phase)
    elif kind in ("square","polygon","multimetal"):
        count = 4 if kind in ("square","multimetal") else sides
        raw_turns = num("turns",2)
        if raw_turns <= 0:
            raise ValueError("Turns must be positive")
        maximum = ((spacing+length)/(spacing+width)+(spacing+height)/(spacing+width))/4 if count==4 and kind!="polygon" else math.cos(math.pi/count)*radius/(spacing+width)
        maximum = math.floor(maximum*count)/count
        if raw_turns > maximum:
            raise ValueError(f"Dimensions support at most {maximum:g} turns")
        turns = math.floor(raw_turns*count)/count
        if turns <= 0 or turns*count > 20000:
            raise ValueError("Turn count must produce 1–20000 segments")
        if turns != raw_turns:
            shape.warnings.append(f"Turns quantized to {turns:g} (1/{count} turn steps).")
        shape.parameters["turns"] = turns
        if kind == "polygon":
            # Native polygon and ring builders do not apply PHASE reversal.
            _polygon(shape,tech,metal,radius,sides,width,spacing,turns,radians)
        else:
            _square(shape,tech,metal,exit_metal if kind=="square" else -1,length,height,width,spacing,turns,radians,phase)
            if kind == "multimetal":
                bottom = tech.metal_index(p.get("bottom_metal",0))
                if bottom >= metal:
                    raise ValueError("Multi-metal coil needs a bottom metal below its top metal")
                alternate = turns%1 in (0,0.5)
                axis = 1 if alternate else 0
                previous = copy.deepcopy(shape)
                for index in range(metal-1,bottom-1,-1):
                    winding = copy.deepcopy(previous)
                    for s in winding.segments:
                        m = tech.metals[index]
                        s.metal,s.thickness = index,m.thickness
                        for point in s.points:
                            point[2] = m.geometry_height
                    winding.reflect(axis)
                    winding.segments.reverse()
                    for s in winding.segments:
                        s.reverse()
                    winding.offset(winding.origin[0]-shape.origin[0],winding.origin[1]-shape.origin[1])
                    shape.segments.extend(copy.deepcopy(winding.segments))
                    previous = winding
                    if alternate:
                        axis = 1-axis
    elif kind in ("wire","capacitor"):
        shape.segments.append(_segment(tech,metal,width,(0,width/2),(length,width/2),
                                       (0,0),(length,0),(0,width),(length,width)))
        shape.rotate(radians)
        if kind == "capacitor":
            bottom = tech.metal_index(p.get("bottom_metal",max(0,metal-1)))
            if bottom == metal:
                raise ValueError("Capacitor plates must use distinct metals")
            second = copy.deepcopy(shape.segments[0])
            m = tech.metals[bottom]
            second.metal,second.thickness = bottom,m.thickness
            for point in second.points:
                point[2] = m.geometry_height
            shape.segments.append(second)
        elif phase < 0:
            shape.segments[0].reverse()
    elif kind == "ring":
        gap = num("gap",20)
        if not 0 <= abs(gap) <= 360:
            raise ValueError("Gap must be between −360 and 360 degrees")
        if width >= radius*math.cos(math.pi/sides):
            raise ValueError("Ring width must leave a positive inner radius")
        _ring(shape,tech,metal,radius,sides,width,math.radians(gap),radians)
    else:
        index = tech.via_index(p.get("via",0))
        nx,ny = num("nx",2),num("ny",2)
        if nx != int(nx) or ny != int(ny) or not 1 <= nx <= 1000 or not 1 <= ny <= 1000:
            raise ValueError("Via counts must be integers from 1 to 1000")
        shape.segments.append(_via(tech,index,int(nx),int(ny)))
        if phase < 0:
            shape.segments[0].reverse()
    return shape

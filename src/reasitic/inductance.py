"""ASITIC's INDUCTANCE / COUPLING estimate, not its full PI2 EM network.

Direct ports of analysis_commands.cpp and the segment mutual case table in
segment.cpp, canonicalize.cpp, parallel.cpp, planar.cpp and spatial.cpp.
Intermediate units are centimetres and the result is nH, as in ASITIC.
"""
import math
from fractions import Fraction
from functools import lru_cache

EPS = 1e-10
SCALE = 1e-4
SELF_CONSTANT = float.fromhex("0x1.004039abf3387p-1")


def _round_extended(value):
    """Round a rational to the x87 64-bit significand (nearest/even).

    Needed for the reference's 5000-unit basis translation: rounding both
    translated endpoints straight to binary64 can change its case selection.
    No platform long-double dependency, so this also works in WebAssembly.
    """
    if not value:
        return value
    sign = -1 if value<0 else 1
    value = abs(value)
    num,den = value.numerator,value.denominator
    exponent = num.bit_length()-den.bit_length()
    if (Fraction(2)**exponent)>value:
        exponent -= 1
    shift = 63-exponent
    if shift>=0:
        num <<= shift
    else:
        den <<= -shift
    integer,remainder = divmod(num,den)
    if remainder*2>den or (remainder*2==den and integer%2):
        integer += 1
    return sign*Fraction(integer,1<<shift) if shift>=0 else sign*Fraction(integer*(1<<-shift))


@lru_cache(maxsize=8192)
def _basis_delta(start,end,z_axis):
    a = _round_extended(Fraction(start)+5000)
    b = _round_extended(Fraction(end)+5000)
    return float(_round_extended(b-(a if z_axis else Fraction(float(a)))))


def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def _sub(a,b):
    return [x-y for x,y in zip(a,b)]


def _cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def _norm(a):
    return math.sqrt(_dot(a,a))


def _unit(a):
    n = _norm(a)
    return [x/n for x in a] if n > EPS else [0,0,0]


def _intersects(p,u,q,v,la,lb):
    xy = v[0]*u[1]-u[0]*v[1]
    xz = v[0]*u[2]-u[0]*v[2]
    yz = v[1]*u[2]-u[1]*v[2]
    if all(abs(d)<EPS for d in (xy,xz,yz)):
        axes = [i for i in range(3) if abs(u[i])>EPS]
        if not axes:
            return False
        ts = [(q[i]-p[i])/u[i] for i in axes]
        if any(abs(t-ts[0])>=EPS for t in ts[1:]) or any(abs(p[i]-q[i])>=EPS for i in range(3) if i not in axes):
            return False
        k = next(i for i in range(3) if u[i]!=0)
        first,last = (q[k]-p[k])/u[k],(lb*v[k]+q[k]-p[k])/u[k]
        return EPS<first and first+EPS<la and EPS<last and last+EPS<lb
    i,j,k,det = (0,1,2,xy) if abs(xy)>EPS else (0,2,1,xz) if abs(xz)>EPS else (1,2,0,yz)
    di,dj,dk = q[i]-p[i],q[j]-p[j],q[k]-p[k]
    t,s = (dj*v[i]-di*v[j])/det,(dj*u[i]-di*u[j])/det
    if abs(t*u[k]-s*v[k]-dk)>EPS:
        return False
    return EPS<t and t+EPS<la and EPS<s and s+EPS<lb


def _canonical(a,b):
    da,db = _sub(a[3:6],a[:3]),_sub(b[3:6],b[:3])
    if abs(_dot(da,db)) < EPS:
        return 5
    na,nb = _norm(da),_norm(db)
    if min(na,nb)<EPS:
        return 6
    u,v = _unit(da),_unit(db)
    if _intersects(a[:3],u,b[:3],v,na,nb):
        return 3
    delta = [_basis_delta(a[i],a[i+3],i==2) for i in range(3)]
    start,end = _sub(b[:3],a[:3]),_sub(b[3:6],a[:3])
    if _norm(delta)<EPS:
        return 4
    e1 = _unit(delta)
    e3 = _cross(e1,_unit(start))
    if _norm(e3)<EPS:
        e3 = _cross(e1,_unit(end))
        if _norm(e3)<EPS:
            return 0
    e3 = _unit(e3)
    e2 = _unit(_cross(e3,e1))
    a[:6] = [0,0,0,_norm(delta),0,0]
    b[:6] = [_dot(start,e1),_dot(start,e2),_dot(start,e3),_dot(end,e1),_dot(end,e2),_dot(end,e3)]
    projection = abs(_dot(_sub(a[:3],a[3:6]),_sub(b[:3],b[3:6])))
    if abs(projection-math.dist(b[:3],b[3:6])*math.dist(a[:3],a[3:6]))<EPS:
        return 0
    return 1 if abs(b[5])<EPS and abs(b[2])<EPS else 2


def _nonparallel(a,b,spatial):
    d0,d1 = math.dist(a[3:6],b[3:6]),math.dist(a[3:6],b[:3])
    d2,d3 = math.dist(a[:3],b[:3]),math.dist(a[:3],b[3:6])
    la,lb = math.dist(a[:3],a[3:6]),math.dist(b[:3],b[3:6])
    p2,q2,r2,s2 = d3*d3,d2*d2,d1*d1,d0*d0
    diff = p2-q2
    delta = diff+r2-s2
    magnitude = abs(delta)
    cosine = magnitude/(2*la*lb)
    # Guard a few ulps from geometric identities in binary64.
    if cosine>1+1e-10:
        raise ValueError("Invalid segment angle")
    angle = math.atan2(math.sqrt(max(0,1-cosine*cosine)),cosine)
    c,s = math.cos(angle),math.sin(angle)
    if not spatial and min(abs(d) for d in (d0,d1,d2,d3))<EPS:
        if abs(d0)<EPS:
            d0=d2
        elif abs(d1)<EPS:
            d0=d3
        elif abs(d2)>=EPS and abs(d3)<EPS:
            d0=d1
        return 2*c*(lb*math.atanh(la/(lb+d0))+la*math.atanh(lb/(la+d0)))
    a2,b2 = la*la,lb*lb
    if delta > EPS:
        w,v = diff-b2,r2-q2-a2
    else:
        v,w = s2-p2-a2,q2-p2-b2
    den = 4*a2*b2-delta*delta
    x = la*(magnitude*w+2*b2*v)/den
    y = lb*(2*a2*w+magnitude*v)/den
    hb0,hb1 = math.atanh(lb/(d0+d1)),math.atanh(lb/(d2+d3))
    ha0 = math.atanh(la/((d0+d3) if delta>EPS else (d1+d2)))
    ha1 = math.atanh(la/((d1+d2) if delta>EPS else (d0+d3)))
    total = (y+lb)*ha0+hb0*(x+la)-hb1*x-ha1*y
    if not spatial:
        return 2*c*total
    h2 = 2*x*y*c+((q2 if delta>EPS else p2)-x*x)-y*y
    h = math.sqrt(max(0,h2))
    n = c*h2
    a0 = math.atan2((x+la)*(y+lb)*s*s+n,h*(d0 if delta>EPS else d1)*s)
    a1 = math.atan2(n+(x+la)*y*s*s,h*(d1 if delta>EPS else d0)*s)
    a2angle = math.atan2(n+x*y*s*s,h*(d2 if delta>EPS else d3)*s)
    a3 = math.atan2(x*(y+lb)*s*s+n,h*(d3 if delta>EPS else d2)*s)
    return (2*total-(a0-a1+a2angle-a3)*h/s)*c


def segment_mutual(a,b,warnings=None):
    """Signed mutual nH between [x0,y0,z0,x1,y1,z1,width,thickness]."""
    orientation = _dot(_sub(a[:3],a[3:6]),_sub(b[:3],b[3:6]))
    if abs(orientation)<=EPS:
        return 0
    sign = 1 if orientation>EPS else -1
    sep = abs(a[2]*SCALE-b[2]*SCALE)
    a,b = [x*SCALE for x in a],[x*SCALE for x in b]
    case = _canonical(a,b)
    if case == 0:
        from .parallel import parallel_segment_mutual
        status,value=parallel_segment_mutual(a,b,sep)
        if status:value=0.0
    elif case in (1,2):
        value = _nonparallel(a,b,case==2)
    else:
        if case==3 and warnings is not None:
            warnings.append("Segments intersect; their mutual contribution is zero, as in ASITIC.")
        value = 0
    return abs(value)*sign


def _record(s,origin=(0,0)):
    return [s.start[0]+origin[0],s.start[1]+origin[1],s.start[2],
            s.end[0]+origin[0],s.end[1]+origin[1],s.end[2],
            s.width if s.primary_width is None else s.primary_width,
            s.thickness if s.primary_thickness is None else s.primary_thickness]


def inductance_estimate(shape,technology):
    """Original INDUCTANCE command result in nH (frequency independent)."""
    if len(shape.segments)>2000:
        raise ValueError("Inductance estimate is limited to 2000 segments")
    total = 0
    count = len(technology.metals)
    records = []
    for segment in shape.segments:
        if segment.metal<count:
            length = segment.length*SCALE
            width,thickness = segment.width*SCALE,technology.metals[segment.metal].thickness*SCALE
            records.append(_record(segment))
        else:
            via = technology.vias[segment.metal-count]
            length = abs(segment.end[2]-segment.start[2])*SCALE
            width,thickness = SCALE*segment.nx*via.width,SCALE*segment.ny*via.spacing
        if length>EPS:
            total += 2*length*(math.log(2*length/(width+thickness))+SELF_CONSTANT+(width+thickness)/(3*length))
    mutual = 0
    for i,a in enumerate(records):
        for b in records[i+1:]:
            mutual += segment_mutual(a,b,shape.warnings)
    return total+2*mutual


def coupling_estimate(first,second,technology):
    """Original COUPLING result: mutual nH and signed dimensionless k."""
    if len(first.segments)*len(second.segments)>1000000:
        raise ValueError("Coupling estimate exceeds one million segment pairs")
    l1,l2 = inductance_estimate(first,technology),inductance_estimate(second,technology)
    count = len(technology.metals)
    mutual = sum(segment_mutual(_record(a,first.origin),_record(b,second.origin))
                 for a in first.segments if a.metal<count
                 for b in second.segments if b.metal<count)
    return mutual,mutual/math.sqrt(l1*l2) if min(l1,l2)>EPS else 0

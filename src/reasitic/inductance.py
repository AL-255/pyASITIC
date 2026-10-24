"""ASITIC's INDUCTANCE / COUPLING estimate, not its full PI2 EM network.

Direct ports of analysis_commands.cpp and the segment mutual case table in
segment.cpp, canonicalize.cpp, parallel.cpp, planar.cpp and spatial.cpp.
Intermediate units are centimetres and the result is nH, as in ASITIC.
"""
import math
from fractions import Fraction
from functools import lru_cache
from .retained_scalar import Real

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
    a = Real(start)+Real(5000.)
    b = Real(end)+Real(5000.)
    return float(b-(a if z_axis else Real(float(a))))


def _intersects(p,u,q,v,la,lb):
    from .mutual_geometry import intersects
    return intersects(p,u,q,v,la,lb)


def _canonical(a,b):
    from .mutual_geometry import canonical
    return canonical(a,b)


def _nonparallel(a,b,spatial):
    from .mutual_geometry import planar,spatial as spatial_mutual
    return spatial_mutual(a,b)if spatial else planar(a,b)


def segment_mutual(a,b,warnings=None):
    """Signed mutual nH between [x0,y0,z0,x1,y1,z1,width,thickness]."""
    from .mutual_kernel import segment_value,WARNING_MESSAGES
    compiled=segment_value(a,b)
    if compiled is not None:
        value,warning=compiled
        if warning and warnings is not None:warnings.append(WARNING_MESSAGES[warning])
        return value
    from .mutual_geometry import dot,planar,spatial
    da=[float(Real(a[i])-a[i+3])for i in range(3)]
    db=[float(Real(b[i])-b[i+3])for i in range(3)]
    orientation = dot(da,db)
    if orientation>EPS:sign=1.
    elif orientation<-EPS:sign=-1.
    else:return 0.
    sep = float(abs(Real(a[2])*Real(SCALE)-Real(b[2])*Real(SCALE)))
    a,b = [float(Real(x)*Real(SCALE))for x in a],[float(Real(x)*Real(SCALE))for x in b]
    case = _canonical(a,b)
    if case == 0:
        from .parallel import parallel_segment_mutual
        status,value=parallel_segment_mutual(a,b,sep)
        if status:value=0.0
    elif case == 1:
        value = planar(a,b)
    elif case == 2:
        value = spatial(a,b)
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
    from .conductor_metrics import retained_estimates
    return float(retained_estimates(shape,technology)[0])


def coupling_estimate(first,second,technology):
    """Original COUPLING result and native centerline translation side effects."""
    from .coupling_metrics import retained_coupling
    mutual,coefficient=retained_coupling(first,second,technology)
    return mutual,float(coefficient)

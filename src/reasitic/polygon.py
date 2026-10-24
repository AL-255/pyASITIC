"""Original polygon-spiral vertices with retained arithmetic and native Pi."""
from array import array
from decimal import Decimal,localcontext
from fractions import Fraction
import math
from .retained_scalar import Real as R

try:
    from _reasitic_numeric import polygon_spiral as _compiled_polygon
except ImportError:
    _compiled_polygon=None

PI=float.fromhex("0x1.921fb54442d18p+1")
TAU=float.fromhex("0x1.921fb54442d18p+2")
NATIVE_PI=Fraction((1<<112)|((0x4000921fb54442d1&0xffffffffffff)<<64)|0x8469800000000000,1<<111)
TRUE_PI=Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068")


def _trig(x,cosine):
    if x.kind:return R(math.nan)
    if abs(x)>=R(2.**63):return R(x)
    if x==0.:return R(1.) if cosine else R(x)
    magnitude=abs(x).value
    quotient=R._result(magnitude/(NATIVE_PI/2)).value
    n,r=divmod(quotient.numerator,quotient.denominator)
    if 2*r>quotient.denominator or (2*r==quotient.denominator and n&1):n+=1
    reduced=magnitude-n*NATIVE_PI/2
    with localcontext() as context:
        context.prec=100
        fraction=reduced/NATIVE_PI
        z=(Decimal(fraction.numerator)/Decimal(fraction.denominator))*TRUE_PI
        evaluate_cosine=not n%2 if cosine else bool(n%2)
        term=Decimal(1) if evaluate_cosine else z;total=term;square=-z*z
        for i in range(1,65):
            term=term*square/((2*i-1)*(2*i) if evaluate_cosine else (2*i)*(2*i+1));total+=term
        negate=(n%4 in (1,2)) if cosine else (n%4 in (2,3))
        if negate != (not cosine and x.negative):total=-total
        return R._result(Fraction(total))


def vertices(radius,sides,width,spacing,turns,angle):
    """Rows contain start/end, outer-start/end and inner-start/end XY stores."""
    values=[radius,sides,width,spacing,turns,angle]
    if not all(math.isfinite(v) for v in values) or sides!=int(sides) or not 3<=sides<=1024 or min(radius,width,turns)<=0 or spacing<0 or turns*sides>20000:
        raise ValueError("Invalid polygon geometry configuration")
    sides=int(sides)
    if _compiled_polygon is not None:
        config=array("d",values);capacity=min(20000,(math.floor(turns)+1)*sides);output=array("d",[0.])*(capacity*12)
        count=_compiled_polygon(config,output)
        if count<0:raise ValueError("Spiral radius exhausted" if count==-2 else "Invalid polygon geometry configuration")
        return [list(output[i*12:(i+1)*12])for i in range(count)]
    n=R(sides);initial=R(radius);sector=R(PI)/n
    ribbon=float(R(width)/_trig(sector,True))
    shrink=float(((R(width)+spacing)*R(turns))/_trig(R(float(sector)),True))
    decrement=float((initial-(initial-R(shrink)))/(R(turns)*n))
    half_ribbon=float(R(ribbon)*R(.5));radius=initial;rows=[]
    def vertex(theta,rad,initial=False):
        c,s=_trig(theta,True),_trig(theta,False)
        center=rad-(R(half_ribbon) if initial else R(ribbon)*R(.5))
        return [float(c*center),float(s*center),float(c*rad),float(s*rad),float(c*(rad-ribbon)),float(s*(rad-ribbon))]
    last=int((R(turns)+R(1.)).value)
    for turn in range(1,last+1):
        first=vertex(R(angle),radius,True)
        count=int(((R(turns)-R(math.floor(turns)))*n+R(1.)/(n+n)).value) if turn==last else sides
        for side in range(1,count+1):
            if len(rows)>=20000:raise ValueError("Invalid polygon geometry configuration")
            radius-=R(decrement)
            if radius<R(1e-10):raise ValueError("Spiral radius exhausted")
            theta=(R(TAU)*R(side))/n+R(angle);next_point=vertex(theta,radius)
            rows.append([v for k in range(3)for pair in (first[2*k:2*k+2],next_point[2*k:2*k+2])for v in pair]);first=next_point
    if not rows:raise ValueError("Invalid polygon geometry configuration")
    offsets=(4,6,8,10,0,2);x0=y0=1e15;x1=y1=-1e15
    for row in rows:
        for k in offsets:
            x,y=row[k:k+2]
            if x<x0:x0=x
            if x1<x:x1=x
            if y<y0:y0=y
            if y1<y:y1=y
    dx,dy=float((R(x1)-x0)*R(.5)),float((R(y1)-y0)*R(.5))
    for row in rows:
        for k in offsets:row[k],row[k+1]=float(R(row[k])+R(dx)),float(R(row[k+1])+R(dy))
    return rows

"""Literal retained symmetric-keyword transition-clearance arithmetic."""
from decimal import Decimal,localcontext
from fractions import Fraction
import math
from .retained_scalar import Real as R
from .precision import _atan2 as decimal_atan2
from .polygon import PI,NATIVE_PI,TRUE_PI


def _decimal(value):return Decimal(value.numerator)/Decimal(value.denominator)


def _atan2(y,x):
    if y.kind==2 or x.kind==2:return R(math.nan)
    if y.kind==1:
        value=TRUE_PI/(4 if x.kind==1 else 2)
        if x.negative:value=TRUE_PI-value
    elif x.kind==1:value=TRUE_PI if x.negative else Decimal(0)
    elif y==0:
        if not x.negative:return R(y)
        value=TRUE_PI
    else:value=decimal_atan2(_decimal(y.value),_decimal(x.value))
    if y.negative and (y.kind or y==0):value=-value
    return R._result(Fraction(value))


def _tan(value):
    if value.kind:return R(math.nan)
    if value==0:return R(value)
    magnitude=abs(value).value;quotient=R._result(magnitude/(NATIVE_PI/2)).value
    n,remainder=divmod(quotient.numerator,quotient.denominator)
    if 2*remainder>quotient.denominator or(2*remainder==quotient.denominator and n&1):n+=1
    reduced=magnitude-n*NATIVE_PI/2
    z=_decimal(reduced/NATIVE_PI)*TRUE_PI;square=-z*z
    sine=st=z;cosine=ct=Decimal(1)
    for i in range(1,65):
        st=st*square/((2*i)*(2*i+1));sine+=st
        ct=ct*square/((2*i-1)*(2*i));cosine+=ct
    answer=-cosine/sine if n&1 else sine/cosine
    if value.negative:answer=-answer
    return R._result(Fraction(answer))


def transition(width,spacing,gap):
    """Original explicit-ILEN rejection and inspectable retained/store boundaries.

    Omitted ILEN bypasses this function. Unordered comparisons do not reject,
    matching the original x87 condition rather than a separate domain guard.
    """
    with localcontext()as context:
        context.prec=100
        w,s,y=R(width),R(spacing),R(gap)
        radius=(s*s+y*y).sqrt();radius64=float(radius)
        angle=_atan2(y/s,R(1.));ratio=w/R(radius64)
        acos=_atan2((R(1.)-ratio*ratio).sqrt(),ratio);acos64=float(acos)
        half=((R(PI)-angle)-R(acos64))*R(.5)
        tangent=_tan(half);tangent64=float(tangent)
        extent=w*R(tangent64);extent=extent+extent;limit=y-R(1e-10)
        return dict(reject=extent>limit,radius=radius,angle=angle,acos=acos,half=half,tangent=tangent,extent=extent,limit=limit,
                    radius64=radius64,acos64=acos64,tangent64=tangent64)

"""Portable retained-precision geometry operations used by native ASITIC.

Binary64 stores remain explicit; arithmetic retains a 64-bit significand.
Decimal guard digits evaluate elementary functions without depending on the
host libm (which differs between CPython and WebAssembly at mesh boundaries).
"""
from decimal import Decimal,localcontext
from fractions import Fraction
from .inductance import _round_extended

PI=Decimal("3.1415926535897932384626433832795028841971693993751")


def _decimal(value):
    value=Fraction(value)
    return Decimal(value.numerator)/Decimal(value.denominator)


def _atan(value):
    negative=value<0
    value=abs(value)
    reciprocal=value>1
    if reciprocal:
        value=1/value
    factor=1
    while value>Decimal("0.1"):
        value=value/(1+(1+value*value).sqrt())
        factor*=2
    power=total=value
    square=value*value
    for i in range(1,100):
        power*=-square
        term=power/(2*i+1)
        total+=term
        if abs(term)<Decimal("1e-42"):
            break
    total*=factor
    if reciprocal:
        total=PI/2-total
    return -total if negative else total


def _atan2(y,x):
    if x==0:
        return PI/2 if y>=0 else -PI/2
    value=_atan(y/x)
    if x<0:
        value+=PI if y>=0 else -PI
    return value


def _trig(value,cosine=False):
    value=_decimal(value)
    period=2*PI
    value%=period
    if value>PI:
        value-=period
    elif value<-PI:
        value+=period
    term=total=Decimal(1) if cosine else value
    square=value*value
    for i in range(1,100):
        denominator=(2*i-1)*(2*i) if cosine else (2*i)*(2*i+1)
        term*=-square/denominator
        total+=term
        if abs(term)<Decimal("1e-42"):
            break
    return _round_extended(Fraction(total))


def native_midpoint(low,high):
    difference=_round_extended(Fraction(high)-Fraction(low))
    return float(_round_extended(Fraction(low)+_round_extended(difference/2)))


def rotate_xy(px,py,cx,cy,angle):
    x=_round_extended(Fraction(px)-Fraction(cx))
    y=_round_extended(Fraction(py)-Fraction(cy))
    with localcontext() as context:
        context.prec=44
        square=_round_extended(_round_extended(x*x)+_round_extended(y*y))
        radius=_round_extended(Fraction(_decimal(square).sqrt()))
        if radius<=1e-10:
            return px,py
        polar=float(_round_extended(Fraction(_atan2(_decimal(y),_decimal(x)))))
        rotated=_round_extended(Fraction(polar)+Fraction(angle))
        # Native X retains the angle; Y reloads its binary64 spill.
        cosine=_trig(rotated,True)
        sine=_trig(Fraction(float(rotated)))
        return (float(_round_extended(_round_extended(cosine*radius)+Fraction(cx))),
                float(_round_extended(_round_extended(sine*radius)+Fraction(cy))))

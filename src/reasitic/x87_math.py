"""Retained exponent reduction used by the original potential kernels.

F2XM1 is evaluated with decimal guard precision before the native 64-bit
significand store. The browser runs the corresponding compiled binary128
calculation. Final stores and the original positive-cosh clipping are explicit.
"""
from decimal import Decimal,localcontext,ROUND_HALF_EVEN,InvalidOperation
from functools import lru_cache
from fractions import Fraction
import math
from .fft import _fft_extended as r,_fft_spill as spill
from .retained_scalar import Real as R

try:
    from _reasitic_numeric import tanh_argument as _native_tanh,cosh_argument as _native_cosh
except ImportError:
    _native_tanh=_native_cosh=None

with localcontext() as c:
    c.prec=2048
    L2E=Decimal(0xb8aa3b295c17f0bc)/Decimal(2)**63


def log_retained(value):
    """FYL2X with the native FLDLN2 constant, before a binary64 store."""
    x=R(value)
    if x.kind==2 or(x.negative and(x.kind or x.value)):return R(math.nan)
    if not x.kind and not x.value:return R(-math.inf)
    if x.kind:return R(x)
    with localcontext()as context:
        context.prec=100
        exact=Decimal(x.value.numerator)/Decimal(x.value.denominator)
        logarithm=exact.ln()/Decimal(2).ln()
        return R._result(Fraction(logarithm)*Fraction(0xb17217f7d1cf79ac,1<<64))


def exp_retained(value):
    """Native FLDL2E/FRNDINT/F2XM1/FSCALE sequence (native/fft.c)."""
    e=R(value)*R(Fraction(0xb8aa3b295c17f0bc,1<<63))
    # The original subtracts the rounded exponent before testing nonfinites;
    # either infinity consequently produces NaN, as does a NaN argument.
    if e.kind:return R(math.nan)
    power=round(e.value)
    if power>16384:return R(math.inf)
    if power<-16446:return R(0.)
    fraction=e-R(power)
    with localcontext()as context:
        context.prec=2048
        argument=Decimal(fraction.value.numerator)/Decimal(fraction.value.denominator)
        result=R(_pow2m1(argument))+R(1.)
    # FSCALE keeps the exponent adjustment live until the last store. Split
    # it at the normal limits so the scale factor itself cannot under/overflow.
    if power<-16382:
        result*=R(Fraction(2)**(power+16382));power=-16382
    if power>16383:
        result*=R(2.);power=16383
    return result*R(Fraction(2)**power)


@lru_cache(maxsize=32768)
def _argument(k,a,b):
    with localcontext() as c:
        c.prec=2048
        c.traps[InvalidOperation]=False
        return r(Decimal.from_float(k)*r(Decimal.from_float(a)-Decimal.from_float(b)))
def _pow2m1(x):
    if not x:return x
    with localcontext() as c:
        c.prec=max(90,90-x.adjusted())
        result=Decimal(2)**x-1
    return r(result)
@lru_cache(maxsize=32768)
def _tanh(x):
    with localcontext() as c:
        c.prec=2048
        if not x.is_finite():return math.nan
        if abs(x)>25:return math.copysign(1,float(x))
        e=r(-abs(r(x+x))*L2E);i=e.to_integral_value(rounding=ROUND_HALF_EVEN)
        whole=Decimal(2)**int(i);part=r(_pow2m1(r(e-i))*whole)
        em1=r(r(whole-1)+part);fraction=r(em1/r(em1+2))
        return spill(r(fraction*(1 if -x>=0 else -1)))
@lru_cache(maxsize=32768)
def _cosh(x,rounded=False):
    with localcontext() as c:
        c.prec=2048
        if x.is_nan():return math.nan
        if x>500:return 1e15
        if rounded:x=Decimal.from_float(float(x))
        if x<-800:return math.inf
        e=r(x*L2E);i=e.to_integral_value(rounding=ROUND_HALF_EVEN)
        ex=r(r(_pow2m1(r(e-i))+1)*Decimal(2)**int(i))
        return spill(r(Decimal('.5')*r(r(1/ex)+ex)))


@lru_cache(maxsize=32768)
def tanh_argument(k,a,b):
    return _native_tanh(k,a,b) if _native_tanh is not None else _tanh(_argument(k,a,b))


@lru_cache(maxsize=32768)
def cosh_argument(k,a,b,rounded=False):
    return _native_cosh(k,a,b,int(rounded)) if _native_cosh is not None else _cosh(_argument(k,a,b),rounded)

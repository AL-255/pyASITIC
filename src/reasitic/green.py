"""Original ASITIC eddy-current Green kernels (green.cpp/legacy_complex.cpp).

Frequency is Hz, layer conductivity is S/m, lengths are metres and wave number
is inverse metres. Binary64 complex records and their native spill boundaries
are retained with Decimal guard precision. These kernels do not enable eddy
matrix stamping; the Fourier integration and solver connection are separate.
"""
from dataclasses import dataclass
from decimal import Decimal,localcontext,InvalidOperation,DivisionByZero,Overflow
from fractions import Fraction
from functools import wraps
import math
from .precision import _trig,_decimal
from .inductance import _round_extended

FACTOR=float.fromhex("0x1.08ef67ae4dd49p-17")
MU0=float.fromhex("0x1.515370f99f6cbp-20")
TWO_PI=float.fromhex("0x1.921fb54442d18p+2")


@dataclass(frozen=True)
class GreenLayers:
    layer1:float
    layer2:float
    depth:float


def _guard(function):
    @wraps(function)
    def call(*args,**kwargs):
        with localcontext() as context:
            context.prec=25
            for signal in (InvalidOperation,DivisionByZero,Overflow):
                context.traps[signal]=False
            return function(*args,**kwargs)
    return call


def _d(value):
    return Decimal.from_float(value) if isinstance(value,float) else Decimal(value)


def _pair(value):
    return _d(value.real),_d(value.imag)


def _spill(real,imag):
    return complex(float(real),float(imag))


class _Retained:
    """Finite x87 arithmetic with an explicit 64-bit binary significand."""
    def __init__(self,value):
        self.value=value.value if isinstance(value,_Retained) else Fraction(value)

    def __float__(self):
        return float(self.value)

    def __neg__(self):
        return _Retained(-self.value)

    def __add__(self,other):
        return _Retained(_round_extended(self.value+_Retained(other).value))

    __radd__=__add__

    def __sub__(self,other):
        return _Retained(_round_extended(self.value-_Retained(other).value))

    def __rsub__(self,other):
        return _Retained(other)-self

    def __mul__(self,other):
        return _Retained(_round_extended(self.value*_Retained(other).value))

    __rmul__=__mul__


def _trigonometric(value,cosine=False):
    if not value.is_finite():
        return Decimal("NaN")
    with localcontext() as context:
        context.prec=44
        result=_trig(_round_extended(Fraction(value)),cosine)
        return _decimal(result)


def _expm1(value):
    if abs(value)>Decimal("0.25"):
        return value.exp()-1
    term=total=value
    for i in range(2,100):
        term*=value/i
        total+=term
        if abs(term)<abs(total)*Decimal("1e-27"):
            break
    return total


def _sinh_real(value):
    q=_expm1(abs(value))
    result=(q+q/(q+1))/2
    return -result if value<0 else result


def _cosh_real(value):
    exponential=value.exp()
    return (exponential+1/exponential)/2


@_guard
def legacy_square_root(value):
    real,imag=_pair(value)
    magnitude=float((real*real+imag*imag).sqrt())
    if magnitude==0:
        return 0j
    if real>0:
        t=((_d(magnitude)+real)/2).sqrt()
        return _spill(t,(imag/t)/2)
    t=((_d(magnitude)-real)/2).sqrt()
    if imag<0:
        t=-t
    return _spill((imag/t)/2,t)


@_guard
def legacy_divide(a,b):
    if all(math.isfinite(v) for v in (a.real,a.imag,b.real,b.imag)) and (b.real or b.imag):
        # The ratio and every arithmetic result retain a 64-bit significand.
        # More guard digits alone can leave a tiny imaginary residue in -z/z
        # where native extended multiplication rounds it exactly to zero.
        r=_round_extended
        ar,ai,br,bi=map(Fraction,(a.real,a.imag,b.real,b.imag))
        if abs(bi)>=abs(br):
            ratio=r(br/bi)
            denominator=r(r(r(ratio*ratio)*bi)+bi)
            return complex(float(r(r(r(ar*ratio)+ai)/denominator)),float(r(r(r(ai*ratio)-ar)/denominator)))
        ratio=r(bi/br)
        denominator=r(r(r(ratio*ratio)*br)+br)
        return complex(float(r(r(r(ai*ratio)+ar)/denominator)),float(r(r(ai-r(ar*ratio))/denominator)))
    ar,ai=_pair(a)
    br,bi=_pair(b)
    if abs(bi)>=abs(br):
        ratio=br/bi
        denominator=ratio*ratio*bi+bi
        return _spill((ar*ratio+ai)/denominator,(ai*ratio-ar)/denominator)
    ratio=bi/br
    denominator=ratio*ratio*br+br
    return _spill((ai*ratio+ar)/denominator,(ai-ar*ratio)/denominator)


@_guard
def legacy_exp(value):
    real,imag=_pair(value)
    exponential=_d(float(real.exp()))
    return _spill(exponential*_trigonometric(imag,True),exponential*_trigonometric(imag))


@_guard
def legacy_sinh(value):
    real,imag=_pair(value)
    sine,cosine=_d(float(_sinh_real(real))),_d(float(_cosh_real(real)))
    return _spill(sine*_trigonometric(imag,True),cosine*_trigonometric(imag))


@_guard
def legacy_cosh(value):
    real,imag=_pair(value)
    cosine,sine=_d(float(_cosh_real(real))),_d(float(_sinh_real(real)))
    return _spill(cosine*_trigonometric(imag,True),sine*_trigonometric(imag))


@_guard
def propagation_constant(k,frequency,layer):
    return legacy_square_root(_spill(_d(k)*_d(k)+0,(_d(FACTOR)*_d(layer))*_d(frequency)))


def complex_tanh(value):
    return legacy_divide(legacy_sinh(value),legacy_cosh(value))


@_guard
def reflection_imag(k,frequency,layer1):
    g=propagation_constant(k,frequency,layer1)
    return legacy_divide(_spill(_d(k)-_d(g.real),-_d(g.imag)),_spill(_d(g.real)+_d(k),_d(g.imag))).imag


@_guard
def oscillating_integrand(k,frequency,layers):
    a,b=propagation_constant(k,frequency,layers.layer1),propagation_constant(k,frequency,layers.layer2)
    if not all(math.isfinite(v) for z in (a,b) for v in (z.real,z.imag)):
        return math.nan
    ar,ai=map(_Retained,(a.real,a.imag))
    br,bi=map(_Retained,(b.real,b.imag))
    sr,si=float(ar*ar-ai*ai),float(ar*ai+ar*ai)
    t=complex_tanh(_spill(_Retained(layers.depth)*ar,_Retained(layers.depth)*ai))
    if not all(math.isfinite(v) for v in (t.real,t.imag)):
        return math.nan
    tr,ti=map(_Retained,(t.real,t.imag))
    difference,negative_imag=_Retained(k)-br,-bi
    base_i=ar*negative_imag+ai*difference
    base_r=float(ar*difference-ai*negative_imag)
    kr,ki=float(_Retained(k)*br),float(_Retained(k)*bi)
    nr,ni=-_Retained(sr)+_Retained(kr),-_Retained(si)+_Retained(ki)
    numerator=_spill((nr*tr-ni*ti)+_Retained(base_r),base_i+(ni*tr+nr*ti))
    total,dr,di=_Retained(k)+br,_Retained(sr)+_Retained(kr),_Retained(si)+_Retained(ki)
    denominator=_spill((ar*total-ai*bi)+(dr*tr-di*ti),(total*ai+ar*bi)+(di*tr+dr*ti))
    return legacy_divide(numerator,denominator).imag


@_guard
def propagation_integrand(frequency,layers):
    omega=float(_d(MU0)*_d(float(_d(TWO_PI)*_d(frequency))))
    a=legacy_square_root(complex(0,float(_d(layers.layer1)*_d(omega))))
    b=legacy_square_root(complex(0,float(_d(layers.layer2)*_d(omega))))
    twice_depth=_d(layers.depth)+_d(layers.depth)
    e=legacy_exp(_spill(twice_depth*_d(a.real),twice_depth*_d(a.imag)))
    f=legacy_exp(_spill(twice_depth*_d(b.real),twice_depth*_d(b.imag)))
    ar,ai=_pair(a);br,bi=_pair(b);er,ei=_pair(e);fr,fi=_pair(f)
    plus=float(er+1)
    minus=er-1
    twice_plus,twice_ei=2*_d(plus),2*ei
    twice_fr,twice_fi=2*fr,2*fi
    base_r=float(twice_plus*ar-twice_ei*ai)
    base_i=twice_plus*ai+twice_ei*ar
    ur,ui=twice_fr*minus-twice_fi*ei,twice_fr*ei+twice_fi*minus
    numerator=_spill((ur*br-ui*bi)+_d(base_r),base_i+(ur*bi+ui*br))
    ir,ii=-ei*_d(layers.layer1),minus*_d(layers.layer1)
    vr,vi=fr*_d(plus)-fi*ei,fr*ei+fi*_d(plus)
    wr,wi=vr*ar-vi*ai,vr*ai+vi*ar
    denominator=_spill(ir*_d(omega)+(wr*br-wi*bi),ii*_d(omega)+(wr*bi+wi*br))
    return legacy_divide(numerator,denominator).imag


@_guard
def oscillating_kernel(k,frequency,layers,height,separation):
    kh=_d(k)*_d(height)
    if kh>=_d(float.fromhex("0x1.fffffep127")).ln():
        return 0.0
    integrand=oscillating_integrand(k,frequency,layers)
    decay=float((-kh).exp())
    return float(((_trigonometric(_d(k)*_d(separation),True)*_d(integrand))*_d(decay))/_d(k))


@_guard
def reflection_kernel(k,height):
    # The original callback discards reflection/cosine and returns only exp.
    kh=_d(k)*_d(height)
    if kh>=_d(float.fromhex("0x1.fffffep127")).ln():
        return 0.0
    return float((-kh).exp())

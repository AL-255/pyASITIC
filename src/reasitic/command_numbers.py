"""Original command_runtime.cpp numerical stores at the external input boundary."""
from fractions import Fraction
import math
from .retained_scalar import Real,_exponent


def binary32(value):
    """Store a retained operand directly to binary32, without a binary64 spill."""
    x=Real(value)
    if x.kind:return float(x)
    if not x.value:return -0. if x.negative else 0.
    magnitude=abs(x.value);exponent=_exponent(magnitude)
    if exponent>127:return -math.inf if x.negative else math.inf
    shift=max(exponent-23,-149)
    scaled=magnitude/Fraction(2)**shift
    q,r=divmod(scaled.numerator,scaled.denominator)
    if 2*r>scaled.denominator or(2*r==scaled.denominator and q&1):q+=1
    if exponent==127 and q>=1<<24:return -math.inf if x.negative else math.inf
    if not q:return -0. if x.negative else 0.
    return math.ldexp(float(-q if x.negative else q),shift)


def frequency_ghz(value):
    """Default GHz command parser: read double, scale retained, then store float."""
    value=float(value)
    if not math.isfinite(value)or value<=1e-10:raise ValueError('Frequency must be finite and greater than 1e-10 GHz')
    result=binary32(Real(value)*Real(1e9))
    if not math.isfinite(result):raise ValueError('Frequency exceeds the native command range')
    return result

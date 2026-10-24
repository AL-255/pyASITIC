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


def length_um(value,*,grid_size=None):
    """Type 7 in micrometres, with an optional native retained grid snap."""
    value=float(value)
    if not math.isfinite(value):raise ValueError('Length must be finite')
    result=binary32((Real(value)*Real(1e-6))*Real(1e6))
    if not math.isfinite(result):raise ValueError('Length exceeds the native command range')
    if grid_size is not None:
        grid=float(grid_size)
        if not math.isfinite(grid)or grid<=0:raise ValueError('Snap grid must be finite and positive')
        steps=float(math.floor(((Real(grid)*Real(.5)+Real(result))/Real(grid)).value))
        result=binary32(Real(steps)*Real(grid))
    return result


def angle_radians(value):
    """Type 10: preserve the native asymmetric negative wrap and both stores."""
    value=float(value)
    if not math.isfinite(value):raise ValueError('Angle must be finite')
    n=Real(value);whole=float(math.floor((n/Real(360.)).value))
    degrees=binary32(n-Real(whole)*Real(360.)if n>0 else Real(whole)*Real(360.)+n if n<0 else Real(0.))
    return binary32(Real(degrees)*Real(float.fromhex('0x1.1df46a2529d39p-6')))

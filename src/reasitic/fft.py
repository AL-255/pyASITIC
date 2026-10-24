"""Original positive-sign FFT with retained 80-bit arithmetic.

The browser uses the compiled SoftFloat implementation when installed. The
portable Python path preserves the same operation order and rounding.
"""
from array import array
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN,InvalidOperation
from fractions import Fraction
from functools import lru_cache
import math
from .inductance import _round_extended
from .fft_constants import TWIDDLES

try:
    from _reasitic_numeric import transform as _compiled_transform
except ImportError:
    _compiled_transform=None

_FFT_EXACT=Context(prec=2048)


def _compiled(values,nx,ny=0,observe_storage=None):
    data=array("d",(part for z in values for part in (z.real,z.imag)))
    if observe_storage is None:_compiled_transform(data,nx,ny)
    else:
        scratch=array('d',[0.])*(4*nx);_compiled_transform(data,nx,ny,scratch)
        observe_storage(tuple(complex(scratch[i],scratch[i+1])for i in range(0,len(scratch),2)))
    values[:]=[complex(data[i],data[i+1]) for i in range(0,len(data),2)]


@lru_cache(maxsize=16)
def _fft_plan(n):
    with localcontext() as context:
        context.prec=25
        def extended(value):
            value=_round_extended(Fraction(value))
            return Decimal(value.numerator)/Decimal(value.denominator)
        def sine(value):
            term=total=value
            square=value*value
            for i in range(1,60):
                term*=-square/((2*i)*(2*i+1))
                total+=term
                if abs(term)<Decimal("1e-27"):
                    return extended(total)
            raise ValueError("FFT sine failed to converge")
        plan=[]
        half=1
        while half<n:
            step=2*half
            if step in TWIDDLES:
                significand,power,wpi=TWIDDLES[step]
                wpr=Fraction(significand)*Fraction(2)**power
                wpi=Fraction(wpi);wr,wi=Fraction(1),Fraction(0);weights=[]
                # Preserve the observed FSIN result and every native 64-bit
                # recurrence operation. Exact Decimal weights avoid a second
                # approximation before the butterfly's retained products.
                with localcontext() as exact:
                    exact.prec=160
                    for m in range(half):
                        weights.append((Decimal(wr.numerator)/Decimal(wr.denominator),Decimal(wi.numerator)/Decimal(wi.denominator)))
                        old_wr=wr
                        wr=_round_extended(_round_extended(_round_extended(wr*wpr)-_round_extended(wi*wpi))+wr)
                        wi=_round_extended(_round_extended(_round_extended(wi*wpr)+_round_extended(old_wr*wpi))+wi)
                plan.append((half,weights));half=step;continue
            angle=Decimal.from_float(float.fromhex("0x1.921fb54442d1cp+2"))/step
            small=sine(angle/2)
            wpr=extended(extended(-2*small)*small)
            wpi=Decimal.from_float(float(sine(angle)))
            wr,wi=Decimal(1),Decimal(0)
            weights=[]
            for m in range(half):
                weights.append((wr,wi))
                old_wr=wr
                wr=extended(extended(extended(wr*wpr)-extended(wi*wpi))+wr)
                wi=extended(extended(extended(wi*wpr)+extended(old_wr*wpi))+wi)
            plan.append((half,weights))
            half=step
        return plan



@lru_cache(maxsize=512)
def _fft_quantum(exponent):
    return _FFT_EXACT.power(Decimal(2),exponent)



@lru_cache(maxsize=512)
def _fft_scaling(exponent):
    return _fft_quantum(exponent),_FFT_EXACT.power(Decimal(2),-exponent)



def _fft_parts(value):
    approximate=float(value)
    if approximate and math.isfinite(approximate):
        mantissa,exponent=math.frexp(abs(approximate))
        # Rounding a value just below a power of two to binary64 can cross
        # its binade. Use the retained value to choose the native quantum.
        if mantissa==.5 and abs(value)<Decimal.from_float(abs(approximate)):exponent-=1
    else:
        ratio=Fraction(abs(value));exponent=ratio.numerator.bit_length()-ratio.denominator.bit_length()
        if ratio<Fraction(2)**exponent:exponent-=1
        exponent+=1
    exponent-=64
    quantum,reciprocal=_fft_scaling(exponent)
    integer=(value*reciprocal).to_integral_value(rounding=ROUND_HALF_EVEN)
    return integer,quantum,exponent



def _fft_extended(value):
    if not value or not value.is_finite():
        return value
    integer,quantum,_=_fft_parts(value)
    # Keep the exact retained value. Rounding this product back to 25 decimal
    # digits can perturb a later binary64 halfway case by one ulp.
    return _FFT_EXACT.multiply(integer,quantum)



def _fft_spill(value):
    if not value or not value.is_finite():return float(value)
    integer,quantum,exponent=_fft_parts(value)
    if -1085<=exponent<=960:
        # Scale after the integer's binary64 rounding while the result is
        # normal. Subnormal/overflow boundaries need the full retained value.
        try:return math.ldexp(float(integer),exponent)
        except OverflowError:return math.copysign(math.inf,float(integer))
    return float(_FFT_EXACT.multiply(integer,quantum))



def _fft(values):
    if _compiled_transform is not None:
        _compiled(values,len(values));return
    n=len(values)
    j=0
    for i in range(n-1):
        if i<j:
            values[j],values[i]=values[i],values[j]
        k=n>>1
        while k>1 and j>=k:
            j-=k
            k>>=1
        j+=k
    # Native twiddles remain extended while each butterfly output is spilled
    # to binary64. Keeping that precision prevents the large reactive channel
    # from contaminating small substrate-loss terms through roundoff.
    with localcontext() as context:
        context.prec=2048
        context.traps[InvalidOperation]=False
        convert=Decimal.from_float
        for half,weights in _fft_plan(n):
            step=2*half
            for m,(wr,wi) in enumerate(weights):
                identity=wr==1 and wi==0
                for i in range(m,n,step):
                    a,b=values[i],values[i+half]
                    ar,ai,br,bi=convert(a.real),convert(a.imag),convert(b.real),convert(b.imag)
                    if identity and b.real and b.imag and math.isfinite(b.real) and math.isfinite(b.imag):
                        # Binary64 inputs are already exactly representable in
                        # the native 64-bit significand. Keep the full path for
                        # zero/nonfinite components to preserve sign/NaN rules.
                        tr,ti=br,bi
                    else:
                        tr=_fft_extended(_fft_extended(wr*br)-_fft_extended(wi*bi))
                        ti=_fft_extended(_fft_extended(wr*bi)+_fft_extended(wi*br))
                    values[i+half]=complex(_fft_spill(ar-tr),_fft_spill(ai-ti))
                    values[i]=complex(_fft_spill(tr+ar),_fft_spill(ti+ai))



def _transform_grid(grid,nx,ny,*,observe_storage=None):
    if _compiled_transform is not None:
        _compiled(grid,nx,ny,observe_storage);return
    stride=ny+1
    for x in range(nx+1):
        scratch=[grid[x*stride+y] for y in range(ny+1)]
        scratch.extend(grid[x*stride+2*ny-y] for y in range(ny+1,2*ny))
        _fft(scratch)
        for y in range(ny+1):
            grid[x*stride+y]=scratch[y]
    for y in range(ny+1):
        scratch=[grid[x*stride+y] for x in range(nx+1)]
        scratch.extend(grid[(2*nx-x)*stride+y] for x in range(nx+1,2*nx))
        _fft(scratch)
        for x in range(nx+1):
            grid[x*stride+y]=scratch[x]
    if observe_storage is not None:observe_storage(tuple(scratch))

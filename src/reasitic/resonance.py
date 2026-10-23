"""Original SELFRES midpoint search and distributed-network binding.

Ports analysis_commands.cpp. The native iteration argument is ignored, the
search does not check endpoint signs, and a reported frequency can be unevaluated.
"""
from fractions import Fraction
import math
from .green import legacy_divide,_guard
from .inductance import _round_extended
from .network import solve_pi2,two_port_impedance


@_guard
def imaginary_impedance(y,differential=False):
    """Native binary64 impedance result with retained x87 product arithmetic."""
    if not differential:
        return legacy_divide(1+0j,y["y22"]).imag
    if not all(math.isfinite(v) for key in ("y22","y11","y21") for v in (y[key].real,y[key].imag)):
        return two_port_impedance(y,differential=True).imag
    r=_round_extended
    ar,ai,br,bi,cr,ci=(Fraction(v) for key in ("y22","y11","y21") for v in (y[key].real,y[key].imag))
    real=r(r(ar*br)-r(ai*bi));imag=r(r(ai*br)+r(ar*bi))
    squared_real=Fraction(float(r(r(cr*cr)-r(ci*ci))))
    product=r(cr*ci)
    determinant=complex(float(r(real-squared_real)),float(r(imag-r(product+product))))
    numerator=complex(float(r(r(ar+br)+r(cr+cr))),float(r(r(ai+bi)+r(ci+ci))))
    return legacy_divide(numerator,determinant).imag


def search_self_resonance(analyze,first,second,step,*,differential=False,fast=False,iteration_limit=10,observer=None):
    """Native search around an analyze(frequency, fast) -> Y-record callback.

    Finite bounds/steps are supported, including the native slow zero-step
    exhaustion case. Fast quantization requires a nonzero step. The production
    binding below applies the command parser's minimum-step default first.
    """
    if not all(math.isfinite(v) for v in (first,second,step)):
        raise ValueError("SELFRES bounds and step must be finite")
    if fast and step==0:
        raise ValueError("Fast SELFRES quantization requires a nonzero step")
    del iteration_limit  # Source ignores this argument and hardcodes 100.
    r=_round_extended
    low,high=sorted((Fraction(float(first)),Fraction(float(second))))
    lower,upper=float(low),float(high)
    midpoint=r(r(r(high-low)*Fraction(1,2))+Fraction(lower))
    step=Fraction(float(step))
    trace=[];frequencies=[]
    def evaluate(point):
        frequency=float(point);frequencies.append(frequency)
        return analyze(frequency,fast)
    y=evaluate(midpoint)
    for iteration in range(1,101):
        imag=imaginary_impedance(y,differential)
        if imag>0:lower=float(midpoint)
        else:upper=float(midpoint)
        point=dict(iteration=iteration,frequency_hz=float(midpoint),lower_hz=lower,upper_hz=upper,imaginary_impedance_ohm=imag)
        trace.append(point)
        if observer is not None:observer(point.copy())
        if abs(imag)<float.fromhex("0x1.47ae147ae147bp-7"):
            next_point=midpoint;reason="impedance_tolerance";break
        next_point=r(r(r(Fraction(upper)-Fraction(lower))*Fraction(1,2))+Fraction(lower))
        if fast:
            half=r(Fraction(1,2)*step)
            reciprocal=r(Fraction(1)/step)
            units=r(r(next_point+half)*reciprocal)
            rounded=float(units.numerator//units.denominator)
            next_point=r(Fraction(rounded)*step)
        if abs(r(next_point-midpoint))<step:
            reason="frequency_step";break
        y=evaluate(next_point);midpoint=next_point
    else:
        return dict(frequency_hz=None,native_result_hz=-1.0,reason="iteration_limit",trace=trace,
                    analysis_frequencies_hz=frequencies,evaluations=len(frequencies),last_evaluated_frequency_hz=frequencies[-1])
    return dict(frequency_hz=float(next_point),native_result_hz=float(next_point),reason=reason,trace=trace,
                analysis_frequencies_hz=frequencies,evaluations=len(frequencies),last_evaluated_frequency_hz=frequencies[-1])


def solve_self_resonance(shape,technology,first_hz,last_hz,step_hz,*,ground=None,differential=False,fast=False,
                         eddy=False,observer=None,**mesh):
    """SELFRES SLOW using the original distributed network at every sample.

    The native command's default reference is the device itself. An explicit
    ground shape is usually easier to interpret. Fast conductor analysis is
    unavailable because the supplied native analytical model faults.
    """
    if not all(math.isfinite(v) for v in (first_hz,last_hz,step_hz)) or min(first_hz,last_hz)<=0:
        raise ValueError("SELFRES frequencies must be positive and all inputs finite")
    if fast:
        raise ValueError("Native fast SELFRES faults on conductor coils; use the distributed SLOW search")
    if step_hz<float.fromhex("0x1.b7cdfd9d7bdbbp-34"):
        step_hz=.1
    models=[];warnings=[]
    reference=shape if ground is None else ground
    def analyze(frequency,unused_fast):
        result=solve_pi2(shape,technology,frequency,ground=reference,eddy=eddy,**mesh)
        models[:]=[result]
        warnings.extend(result["warnings"])
        matrix=result["admittance_matrix"]
        y=dict(y22=complex(*matrix[0][0]),y21=complex(*matrix[0][1]),y12=complex(*matrix[1][0]),y11=complex(*matrix[1][1]))
        if not all(math.isfinite(v) for z in y.values() for v in (z.real,z.imag)):
            raise ValueError("Native SELFRES encountered nonfinite network admittance")
        if not math.isfinite(imaginary_impedance(y,differential)):
            raise ValueError("Native SELFRES input impedance is nonfinite")
        return y
    result=search_self_resonance(analyze,first_hz,last_hz,step_hz,differential=differential,observer=observer)
    if result["reason"]=="frequency_step":
        warnings.append("Stopped at the requested frequency resolution; inspect the trace for a zero crossing. The native search does not verify endpoint signs.")
    elif result["reason"]=="iteration_limit":
        warnings.append("Could not find self resonant frequency in given range.")
    result.update(method="ASITIC SELFRES SLOW",differential=bool(differential),eddy=bool(eddy),
                  first_hz=first_hz,last_hz=last_hz,step_hz=step_hz,model=models[0],warnings=list(dict.fromkeys(warnings)))
    return result

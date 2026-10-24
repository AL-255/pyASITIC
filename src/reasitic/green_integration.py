"""Native eddy Green integration selection, warm-up and physical scaling.

Ports green_integration.cpp using the directly ported DQAGIE/DQAWFE routines.
Partial results and convergence statuses remain visible to the caller.
"""
from dataclasses import dataclass,field
from fractions import Fraction
from array import array
import math
from .green import GreenLayers,oscillating_kernel,reflection_kernel,MU0,_guard,_d
from .inductance import _round_extended
from .quadrature import integrate_infinite
from .oscillatory import integrate_fourier

try:
    from _reasitic_numeric import green_reflection as _compiled_reflection
except ImportError:
    _compiled_reflection=None


@dataclass
class GreenIntegrationState:
    layers:GreenLayers
    kernel:str="oscillating"
    frequency:float=0.0
    separation:float=0.0
    height:float=0.0
    z_offset:float=0.0
    history:list=field(default_factory=lambda:[0.0]*3)


@dataclass
class GreenIntegralResult:
    value:float
    integral:float
    error:float
    status:int
    evaluations:int
    observations:int
    last_point:float
    method:str
    intervals:int=0
    cycles:int=0
    cycle_statuses:list=field(default_factory=list)


@_guard
def green_integral(frequency,separation,height,z_offset,state,*,observer=None):
    """Original selector and -integral * binary64(mu0) * frequency scaling.

    Width/z_offset is stored by the original wrapper but unused by its kernels.
    The reflection callback remains pure decay. The oscillating callback already
    contains cosine and DQAWFE applies its native cosine weight again.
    """
    if state.kernel not in ("oscillating","reflection"):
        raise ValueError("Unknown Green kernel")
    if not all(math.isfinite(v) for v in (frequency,separation,height,z_offset)):
        raise ValueError("Green integration parameters must be finite")
    state.frequency,state.separation,state.height,state.z_offset=frequency,separation,height,z_offset
    if _compiled_reflection is not None and state.kernel=="reflection" and observer is None:
        config=array("d",[frequency,separation,height,z_offset,*state.history,0.])
        output=array("d",[0.])*3032
        status=_compiled_reflection(config,output)
        if status:raise ValueError("Invalid Green integration configuration")
        if not status:
            state.history[:]=output[10:13]
            cycles=int(output[9])
            return GreenIntegralResult(output[0],output[1],output[2],int(output[3]),int(output[4]),int(output[5]),output[7],
                                       "DQAWFE" if cycles else "DQAGIE",int(output[8]),cycles,[int(v) for v in output[2032:2032+cycles]])
    observations=0
    last_point=0.0
    def kernel(k):
        nonlocal observations,last_point
        observations+=1;last_point=k
        if observer is not None:
            observer(k)
        if state.kernel=="reflection":
            return reflection_kernel(k,state.height)
        return oscillating_kernel(k,state.frequency,state.layers,state.height,state.separation)
    if abs(separation)<float.fromhex("0x1.b7cdfd9d7bdbbp-34"):
        sample=0.0
        while True:
            kernel(sample)
            next_point=_d(sample)+_d(float.fromhex("0x1.a36e2eb1c432dp-14"))
            sample=float(next_point)
            if not next_point<_d(float.fromhex("0x1.47ae147ae147bp-7")):
                break
        result=integrate_infinite(kernel,0.0,1,0.0,float.fromhex("0x1.0c6f7a0b5ed8dp-20"),200)
        method="DQAGIE"
        intervals,cycles,cycle_statuses=result.intervals,0,[]
    else:
        result=integrate_fourier(kernel,0.0,separation,1,float.fromhex("0x1.47ae147ae147bp-7"),
                                 limit=500,cycle_limit=1000,moment_rows=50,history=state.history)
        method="DQAWFE"
        intervals,cycles,cycle_statuses=0,result.cycles,result.cycle_statuses
    if math.isfinite(result.integral):
        scaled=_round_extended(-Fraction(result.integral)*Fraction(MU0))
        value=float(_round_extended(scaled*Fraction(frequency)))
    else:
        value=float((-_d(result.integral)*_d(MU0))*_d(frequency))
    return GreenIntegralResult(value,result.integral,result.error,result.status,result.evaluations,observations,last_point,
                               method,intervals,cycles,cycle_statuses)

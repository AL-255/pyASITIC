"""Original filament self impedance and retained frequency weighting."""
from array import array
from decimal import Decimal, localcontext
from fractions import Fraction
import math
from .retained_scalar import Real as R
from .numeric_limits import MATRIX_CAPACITY

try:
    from _reasitic_numeric import impedance_assemble as _compiled_assembly
except ImportError:
    _compiled_assembly=None

TAU=float.fromhex("0x1.921fb54442d18p+2")
NANO=float.fromhex("0x1.12e0be826d695p-30")


def _log(x):
    if x.kind==2 or (x.negative and x.value):return R(math.nan)
    if not x.kind and not x.value:return R(-math.inf)
    if x.kind:return R(x) if not x.negative else R(math.nan)
    with localcontext() as context:
        context.prec=100
        value=Decimal(x.value.numerator)/Decimal(x.value.denominator)
        logarithm=value.ln()/Decimal(2).ln()
        # FLDLN2 supplies this rounded extended constant to FYL2X; the
        # logarithm and multiplication are evaluated before the retained store.
        native_ln2=Fraction(0xb17217f7d1cf79ac,1<<64)
        return R._result(Fraction(logarithm)*native_ln2)


def self_impedance(wire,sheet_resistance,thickness_cells,omega_nh):
    dx,dy,dz=(R(wire[i+3])-wire[i] for i in range(3))
    length=((dx*dx+dy*dy)+dz*dz).sqrt()
    inductance=0.;resistance=R(0.)
    if R(1e-10)<length:
        width,thickness=R(wire[6]),R(wire[7]);total=width+thickness
        inductance=float((length*R(2e-4))*((_log((length+length)/total)+R(float.fromhex("0x1.004039abf3387p-1")))+total/(length*R(3.))))
        resistance=((length/width)*R(sheet_resistance))*R(thickness_cells)
    return complex(float(resistance),float(R(omega_nh)*R(inductance)))


def assemble(wires,metadata,pairs,frequency):
    """Preserve native self and mutual stores; reuse geometry-only pair terms."""
    n=len(wires)
    if n<1 or len(metadata)!=n or len(pairs)!=n*(n-1)//2:
        raise ValueError("Invalid filament assembly dimensions")
    if _compiled_assembly is not None and n<=MATRIX_CAPACITY:
        data=array("d",(v for wire,(sheet,nz) in zip(wires,metadata) for v in (sheet,nz,*wire)))
        values=array("d",pairs);output=array("d",[0.])*(2*n*n)
        if _compiled_assembly(data,values,output,frequency):raise ValueError("Invalid filament assembly configuration")
        return [[complex(output[2*(j*n+i)],output[2*(j*n+i)+1])for j in range(n)]for i in range(n)]
    omega=float(R(NANO)*R(float(R(TAU)*R(frequency))))
    matrix=[[0j]*n for _ in range(n)];pair=0
    for i in range(n):
        matrix[i][i]=self_impedance(wires[i],*metadata[i],omega)
        for j in range(i+1,n):
            value=complex(0.,float(R(omega)*R(pairs[pair])));pair+=1
            matrix[i][j]=matrix[j][i]=value
    return matrix

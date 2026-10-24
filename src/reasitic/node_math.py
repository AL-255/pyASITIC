"""Retained folded-node driver from native/node.cpp."""
from .retained_scalar import Real as R
from .linear import factor_general,solve_general,matrix_vector
from .network_metrics import _divide,_scalar_divide


def _add(a,b):return complex(float(R(a.real)+R(b.real)),float(R(a.imag)+R(b.imag)))
def _subtract(a,b):return complex(float(R(a.real)-R(b.real)),float(R(a.imag)-R(b.imag)))
def _negative(a):return complex(float(-R(a.real)),float(-R(a.imag)))


def folded(capacitance,inductance,*,storage=None):
    n=len(capacitance)
    cap=[row.copy()for row in capacitance]
    for i in range(n):
        acc=0j
        for j in range(n):
            value=cap[i][j];acc=_add(acc,value)
            if i!=j:cap[i][j]=_negative(value)
        cap[i][i]=acc
    difference=[row.copy()for row in inductance]
    for j in range(n-1,0,-1):
        for i in range(n):difference[i][j]=_subtract(difference[i][j],difference[i][j-1])
    for i in range(n-1,0,-1):
        for j in range(n):difference[i][j]=_subtract(difference[i][j],difference[i-1][j])
    lu,pivots=factor_general([[_add(cap[i][j],difference[i][j])for j in range(n)]for i in range(n)])
    # The original product reads row-major records from column-major input.
    # Keeping that transpose matters for asymmetric branch admittances.
    transposed=[list(row)for row in zip(*inductance)]
    def run(drive,bias):
        rhs=matrix_vector(transposed,bias)
        for i in range(n-1,0,-1):rhs[i]=_subtract(rhs[i],rhs[i-1])
        for i in range(n):rhs[i]=_add(rhs[i],drive[i])
        rhs=solve_general(lu,pivots,rhs);first=rhs[0]
        for i in range(n-1):rhs[i]=_subtract(rhs[i],rhs[i+1])
        for i in range(n):rhs[i]=_subtract(rhs[i],bias[i])
        current=matrix_vector(transposed,rhs)
        if storage is not None:storage.update(drive=drive,bias=bias,rhs=rhs,current=current)
        return first,_negative(current[-1])
    a,c=run([1+0j]+[0j]*(n-1),[0j]*n)
    b,d=run([0j]*n,[0j]*(n-1)+[1+0j])
    ar,ai,dr,di,cr,ci,br,bi=(R(v)for z in(a,d,c,b)for v in(z.real,z.imag))
    determinant=complex(float((ar*dr-ai*di)-(cr*br-ci*bi)),float((dr*ai+ar*di)-(br*ci+cr*bi)))
    offdiag=_divide(_negative(b),a)
    if storage is not None:storage.update(lu=lu,pivots=tuple(p+1 for p in pivots))
    return dict(y11=_divide(determinant,a),y12=offdiag,y21=offdiag,y22=_scalar_divide(1.,a)),cap

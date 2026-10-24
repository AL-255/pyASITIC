"""Native general factors, inverses, solves and network matrix-vector products.

Preserves 64-column panels, IZAMAX abs-one pivots, rounded reciprocals followed
by scaling, and BLAS update/spill order. The compiled backend retains 80-bit
intermediates; the portable fallback rounds every operation to the retained
significand. Exception flags are not reproduced.
"""
from .retained_scalar import Real
from array import array
from .green import _guard,legacy_divide

try:
    from _reasitic_numeric import general as _compiled_general
except ImportError:
    _compiled_general=None


def _validate(matrix):
    n=len(matrix)
    if not n or any(len(row)!=n for row in matrix):raise ValueError("General LU requires a nonempty square matrix")
    return n


def _compiled(matrix,n,operation,pivots=None,rhs=None):
    values=array("d",(v for j in range(n) for i in range(n) for v in (matrix[i][j].real,matrix[i][j].imag)))
    values.extend([p+1 for p in pivots] if pivots is not None else [0.0]*n)
    values.extend(v for z in (rhs if rhs is not None else [0j]*n) for v in (z.real,z.imag))
    status=_compiled_general(values,n,operation)
    if status:raise ValueError("Singular general LU matrix" if status>0 else "Invalid general LU configuration")
    if operation>=2:return [complex(values[i],values[i+1]) for i in range(2*n*n+n,len(values),2)]
    result=[[complex(values[2*(j*n+i)],values[2*(j*n+i)+1]) for j in range(n)] for i in range(n)]
    return result,[int(v)-1 for v in values[2*n*n:2*n*n+n]]


def _product(a,b):
    ar,ai,br,bi=map(Real,(a.real,a.imag,b.real,b.imag))
    return ar*br-ai*bi,ai*br+ar*bi


def _scale(a,b):
    real,imag=_product(a,b)
    return complex(float(real),float(imag))


def _update(old,a,b,subtract=False):
    real,imag=_product(a,b)
    r,i=Real(old.real),Real(old.imag)
    return complex(float(r-real if subtract else r+real),float(i-imag if subtract else i+imag))


@_guard
def matrix_vector(matrix,vector):
    """Native network dot products, with an accumulation spill after each term."""
    n=_validate(matrix)
    if len(vector)!=n:raise ValueError("Matrix-vector dimensions must match")
    if _compiled_general is not None and n<=514:return _compiled(matrix,n,3,rhs=vector)
    result=[]
    for row in matrix:
        real=imag=0.0
        for a,b in zip(row,vector):
            ar,ai,br,bi=map(Real,(a.real,a.imag,b.real,b.imag))
            real=float((ar*br-ai*bi)+Real(real))
            imag=float((br*ai+ar*bi)+Real(imag))
        result.append(complex(real,imag))
    return result


@_guard
def factor_general(matrix):
    """Native ZGETRF panel structure; returns binary64 LU and zero-based pivots."""
    n=_validate(matrix)
    if _compiled_general is not None and n<=514:return _compiled(matrix,n,0)
    a=[row.copy() for row in matrix];pivots=[0]*n
    def norm(z):return abs(Real(z.real))+abs(Real(z.imag))
    block=64 if n>64 else n
    for start in range(0,n,block):
        end=min(n,start+block)
        for k in range(start,end):
            pivot=max(range(k,n),key=lambda i:norm(a[i][k]));pivots[k]=pivot
            if a[pivot][k]==0:raise ValueError("Singular general LU matrix")
            if pivot!=k:
                for j in range(start,end):a[k][j],a[pivot][j]=a[pivot][j],a[k][j]
            if k<n-1:
                inv=legacy_divide(1+0j,a[k][k])
                for i in range(k+1,n):a[i][k]=_scale(inv,a[i][k])
            for j in range(k+1,end):
                if a[k][j]==0:continue
                t=-a[k][j]
                for i in range(k+1,n):a[i][j]=_update(a[i][j],a[i][k],t)
        for k in range(start,end):
            pivot=pivots[k]
            if pivot==k:continue
            for j in range(start):a[k][j],a[pivot][j]=a[pivot][j],a[k][j]
            for j in range(end,n):a[k][j],a[pivot][j]=a[pivot][j],a[k][j]
        # Left, lower, unit ZTRSM for U12.
        for j in range(end,n):
            for k in range(start,end):
                if a[k][j]==0:continue
                for i in range(k+1,end):a[i][j]=_update(a[i][j],a[k][j],a[i][k],True)
        # Native ZGEMM NN (-A21 * U12 + A22).
        for j in range(end,n):
            for k in range(start,end):
                if a[k][j]==0:continue
                t=-a[k][j]  # alpha=-1; its native real spill is exact here.
                for i in range(end,n):a[i][j]=_update(a[i][j],t,a[i][k])
    return a,pivots


@_guard
def solve_general(lu,pivots,rhs):
    """Native ZGETRS with row swaps, then column-ordered L/U substitutions."""
    n=_validate(lu);b=rhs.copy()
    if len(b)!=n or len(pivots)!=n:raise ValueError("General solve dimensions must match")
    if any(not isinstance(p,int) or not 0<=p<n for p in pivots):raise ValueError("Invalid general LU pivot")
    if _compiled_general is not None and n<=514:return _compiled(lu,n,2,pivots,b)
    for i,pivot in enumerate(pivots):b[i],b[pivot]=b[pivot],b[i]
    for k in range(n):
        if b[k]==0:continue
        for i in range(k+1,n):b[i]=_update(b[i],b[k],lu[i][k],True)
    for k in range(n-1,-1,-1):
        if b[k]==0:continue
        b[k]=legacy_divide(b[k],lu[k][k])
        for i in range(k):b[i]=_update(b[i],b[k],lu[i][k],True)
    return b


@_guard
def inverse_general(matrix):
    """Native ZGETRF/ZGETRI with the capacitance driver's n-cell workspace."""
    n=_validate(matrix)
    if _compiled_general is not None and n<=514:return _compiled(matrix,n,1)[0]
    a,pivots=factor_general(matrix)
    if any(a[i][i]==0 for i in range(n)):raise ValueError("Singular general LU matrix")
    # ZTRTRI retains its 64-column blocks even though ZGETRI's smaller work
    # allocation selects the latter routine's unblocked lower-triangle step.
    for start in range(0,n,64):
        end=min(start+64,n)
        # ZTRMM left/upper, alpha=1, on the already inverted prefix.
        for j in range(start,end):
            for k in range(start):
                if a[k][j]==0:continue
                t=_scale(1+0j,a[k][j])
                for i in range(k):a[i][j]=_update(a[i][j],t,a[i][k])
                a[k][j]=_scale(t,a[k][k])
        # ZTRSM right/upper, alpha=-1.
        for j in range(start,end):
            for i in range(start):a[i][j]=_scale(-1+0j,a[i][j])
        for j in range(start,end):
            for k in range(start,j):
                if a[k][j]==0:continue
                for i in range(start):a[i][j]=_update(a[i][j],a[k][j],a[i][k],True)
            inv=legacy_divide(1+0j,a[j][j])
            for i in range(start):a[i][j]=_scale(inv,a[i][j])
        # Unblocked inverse of the diagonal block, upper non-unit ZTRTI2.
        for j in range(start,end):
            inv=legacy_divide(1+0j,a[j][j]);a[j][j]=inv
            t=complex(-inv.real,-inv.imag)
            for k in range(start,j):
                if a[k][j]==0:continue
                value=a[k][j]
                for i in range(start,k):a[i][j]=_update(a[i][j],value,a[i][k])
                a[k][j]=_scale(value,a[k][k])
            for i in range(start,j):a[i][j]=_scale(t,a[i][j])
    work=[0j]*n
    for j in range(n-1,-1,-1):
        for i in range(j+1,n):work[i]=a[i][j];a[i][j]=0j
        for k in range(j+1,n):
            if work[k]==0:continue
            t=_scale(-1+0j,work[k])
            for i in range(n):a[i][j]=_update(a[i][j],t,a[i][k])
    for j in range(n-2,-1,-1):
        if pivots[j]!=j:
            for i in range(n):a[i][j],a[i][pivots[j]]=a[i][pivots[j]],a[i][j]
    return a

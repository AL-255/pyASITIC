"""Native general LU and left triangular solves (general.cpp/node_equations.cpp).

Preserves 64-column panels, IZAMAX abs-one pivots, rounded reciprocals followed
by scaling, and BLAS update/spill order. Decimal guard precision retains live
products until binary64 stores; exception flags are not reproduced.
"""
from decimal import Decimal
from .green import _guard,legacy_divide


def _product(a,b):
    ar,ai,br,bi=map(Decimal.from_float,(a.real,a.imag,b.real,b.imag))
    return ar*br-ai*bi,ai*br+ar*bi


def _scale(a,b):
    real,imag=_product(a,b)
    return complex(float(real),float(imag))


def _update(old,a,b,subtract=False):
    real,imag=_product(a,b)
    r,i=Decimal.from_float(old.real),Decimal.from_float(old.imag)
    return complex(float(r-real if subtract else r+real),float(i-imag if subtract else i+imag))


@_guard
def factor_general(matrix):
    """Native ZGETRF panel structure; returns binary64 LU and zero-based pivots."""
    n=len(matrix)
    if not n or any(len(row)!=n for row in matrix):
        raise ValueError("General LU requires a nonempty square matrix")
    a=[row.copy() for row in matrix];pivots=[0]*n
    def norm(z):return abs(Decimal.from_float(z.real))+abs(Decimal.from_float(z.imag))
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
    n=len(lu);b=rhs.copy()
    if len(b)!=n or len(pivots)!=n:raise ValueError("General solve dimensions must match")
    for i,pivot in enumerate(pivots):b[i],b[pivot]=b[pivot],b[i]
    for k in range(n):
        if b[k]==0:continue
        for i in range(k+1,n):b[i]=_update(b[i],b[k],lu[i][k],True)
    for k in range(n-1,-1,-1):
        if b[k]==0:continue
        b[k]=legacy_divide(b[k],lu[k][k])
        for i in range(k):b[i]=_update(b[i],b[k],lu[i][k],True)
    return b

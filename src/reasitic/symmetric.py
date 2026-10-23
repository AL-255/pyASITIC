"""Native upper complex symmetric factor/inverse (symmetric.cpp/complex.cpp).

The original solver supplies n workspace cells, selecting unblocked ZSYTF2
for every size. This ports its one/two-pivot paths, eigen rotations and ZSYTRI.
Binary64 records use Decimal guard precision for retained intermediate values.
"""
from decimal import Decimal
from array import array
import math
from .green import _guard,legacy_divide
from .linear import _product,_scale,_update

try:
    from _reasitic_numeric import symmetric as _compiled_symmetric
except ImportError:
    _compiled_symmetric=None


def _validate(matrix):
    n=len(matrix)
    if not n or any(len(row)!=n for row in matrix):raise ValueError("Symmetric factor requires a nonempty square matrix")
    if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for row in matrix for z in row):raise ValueError("Symmetric matrix must be finite")
    return n


def _compiled(matrix,n,invert):
    # Columns match the original BLAS layout. The final n cells carry pivots.
    values=array("d",(v for j in range(n) for i in range(n) for v in (matrix[i][j].real,matrix[i][j].imag)))
    values.extend([0.0]*n)
    status=_compiled_symmetric(values,n,int(invert))
    if status:raise ValueError("Singular symmetric matrix" if status>0 else "Invalid symmetric matrix dimension")
    result=[[complex(values[2*(j*n+i)],values[2*(j*n+i)+1]) for j in range(n)] for i in range(n)]
    return result,[int(v) for v in values[2*n*n:]]


def _d(value):return Decimal.from_float(value)
def _e(z):return _d(z.real),_d(z.imag)
def _spill(z):return complex(float(z[0]),float(z[1]))
def _mul(a,b):return a[0]*b[0]-a[1]*b[1],a[1]*b[0]+a[0]*b[1]
def _add(a,b):return _spill((_d(a.real)+_d(b.real),_d(a.imag)+_d(b.imag)))
def _sub(a,b):return _spill((_d(a.real)-_d(b.real),_d(a.imag)-_d(b.imag)))
def _norm(z):return abs(_d(z.real))+abs(_d(z.imag))


def _magnitude(z):
    x,y=abs(_d(z.real)),abs(_d(z.imag))
    if x<y:x,y=y,x
    if x+y==x:return x
    r=y/x
    return (1+r*r).sqrt()*x


def _sqrt(z):
    real,imag=_e(z);m=_magnitude(z)
    if m==0:return 0j
    if not real>0:
        t=((m-real)/2).sqrt();im=float(-t if imag<0 else t)
        return complex(float((imag/_d(im))/2),im)
    t=((real+m)/2).sqrt()
    return _spill((t,(imag/t)/2))


def _square(z):return _spill((_d(z.real)*_d(z.real)-_d(z.imag)*_d(z.imag),(_d(z.real)+_d(z.real))*_d(z.imag)))


def _eigen2(a,b,c):
    if _magnitude(b)==0:
        if _magnitude(c)<=_d(float(_magnitude(a))):return a,c,0j,1+0j,0j
        return c,a,0j,0j,1+0j
    s=_spill(((_d(a.real)+_d(c.real))/2,(_d(a.imag)+_d(c.imag))/2))
    diff=_sub(a,c);t=_spill((_d(diff.real)/2,_d(diff.imag)/2))
    bn=float(_magnitude(b));z=_magnitude(t)
    if z<=_d(bn):z=_d(bn)
    zd=float(z)
    if z>0:
        st=_spill((_d(t.real)/z,_d(t.imag)/z));sb=_spill((_d(b.real)/_d(zd),_d(b.imag)/_d(zd)))
        root=_sqrt(_add(_square(st),_square(sb)))
        t=_spill((_d(zd)*_d(root.real),_d(zd)*_d(root.imag)))
    rt1,rt2=_add(s,t),_sub(s,t)
    if _d(float(_magnitude(rt1)))<_magnitude(rt2):rt1,rt2=rt2,rt1
    sn=legacy_divide(_sub(rt1,a),b);n=_magnitude(sn);nd=float(n)
    if n>1:
        scaled=_spill((_d(sn.real)/n,_d(sn.imag)/n));sq=_square(scaled);inv=1/n
        root=_sqrt(_spill((inv*inv+_d(sq.real),_d(sq.imag))))
        t=_spill((_d(nd)*_d(root.real),_d(nd)*_d(root.imag)))
    else:
        re=_d(sn.real)*_d(sn.real)-_d(sn.imag)*_d(sn.imag)
        im=float(_d(sn.real)*_d(sn.imag)+_d(sn.real)*_d(sn.imag))
        t=_sqrt(_spill((re+1,_d(im)+0)))
    if _magnitude(t)>=_d(float.fromhex("0x1.999999999999ap-4")):
        ev=legacy_divide(1+0j,t)
        return rt1,rt2,ev,ev,_scale(sn,ev)
    return rt1,rt2,0j,0j,sn


def _exchange_upper(a,k,kp,step):
    for i in range(kp):a[i][k],a[i][kp]=a[i][kp],a[i][k]
    for i in range(kp+1,k):a[i][k],a[kp][i]=a[kp][i],a[i][k]
    a[k][k],a[kp][kp]=a[kp][kp],a[k][k]
    if step==2:a[k][k+1],a[kp][k+1]=a[kp][k+1],a[k][k+1]


def _rank1(a,n,alpha,x):
    if not alpha:return
    for j in range(n):
        if not x[j]:continue
        t=_scale(alpha,x[j])
        for i in range(j+1):a[i][j]=_update(a[i][j],x[i],t)


def _rotate(x,y,c,s):
    result_x=[];result_y=[]
    for a,b in zip(x,y):
        cx,sy,cy,sx=_product(c,a),_product(s,b),_product(c,b),_product(s,a)
        result_x.append(_spill((cx[0]+sy[0],cx[1]+sy[1])))
        result_y.append(_spill((cy[0]-sx[0],cy[1]-sx[1])))
    return result_x,result_y


@_guard
def factor_symmetric_upper(matrix):
    n=_validate(matrix)
    if _compiled_symmetric is not None and n<=256:return _compiled(matrix,n,False)
    a=[row.copy() for row in matrix];pivots=[0]*n;k=n-1
    alpha=_d(float.fromhex("0x1.47e0f66afed07p-1"))
    while k>=0:
        step=1;kp=k;absakk=float(_norm(a[k][k]));imax=max(range(k),key=lambda i:_norm(a[i][k])) if k else 0
        colmax=float(_norm(a[imax][k])) if k else 0
        if absakk==0 and colmax==0:raise ValueError("Singular symmetric matrix")
        if _d(absakk)<alpha*_d(colmax):
            jmax=max(range(imax+1,k+1),key=lambda j:_norm(a[imax][j]));rowmax=float(_norm(a[imax][jmax]))
            if imax:
                j=max(range(imax),key=lambda i:_norm(a[i][imax]));v=_norm(a[j][imax]);rowmax=float(max(_d(rowmax),v))
            if _d(absakk)<(alpha*_d(colmax))*(_d(colmax)/_d(rowmax)):
                kp=imax
                if _norm(a[imax][imax])<alpha*_d(rowmax):step=2
        kk=k-step+1
        if kp!=kk:_exchange_upper(a,kk,kp,step)
        if step==1:
            inv=legacy_divide(1+0j,a[k][k]);x=[a[i][k] for i in range(k)]
            _rank1(a,k,-inv,x)
            for i in range(k):a[i][k]=_scale(inv,x[i])
        else:
            r1,r2,ev,c,s=_eigen2(a[k-1][k-1],a[k-1][k],a[k][k])
            if _norm(ev)!=0:
                r1,r2=legacy_divide(1+0j,r1),legacy_divide(1+0j,r2)
                x,y=_rotate([a[i][k-1] for i in range(k-1)],[a[i][k] for i in range(k-1)],c,s)
                _rank1(a,k-1,-r1,x);_rank1(a,k-1,-r2,y)
                x,y=_rotate([_scale(r1,z) for z in x],[_scale(r2,z) for z in y],c,-s)
                for i in range(k-1):a[i][k-1],a[i][k]=x[i],y[i]
            else:
                inv=legacy_divide(1+0j,a[k-1][k]);d11raw=_product(a[k][k],inv);d22raw=_product(a[k-1][k-1],inv)
                d11,d22=_spill(d11raw),_spill(d22raw);p=_mul(d11raw,d22raw)
                d=legacy_divide(-inv,_spill((1-p[0],-p[1])))
                for j in range(k-2,-1,-1):
                    t=_product(d11,a[j][k-1]);w1=_spill(_mul(_e(d),(t[0]-_d(a[j][k].real),t[1]-_d(a[j][k].imag))))
                    t=_product(d22,a[j][k]);w2=_spill(_mul(_e(d),(t[0]-_d(a[j][k-1].real),t[1]-_d(a[j][k-1].imag))))
                    for i in range(j+1):a[i][j]=_update(a[i][j],-w1,a[i][k-1]);a[i][j]=_update(a[i][j],-w2,a[i][k])
                    a[j][k-1],a[j][k]=w1,w2
        pivots[k]=kp+1 if step==1 else -(kp+1)
        if step==2:pivots[k-1]=-(kp+1)
        k-=step
    return a,pivots


def _dot(x,y):
    real=imag=Decimal(0)
    for a,b in zip(x,y):
        pr,pi=_product(a,b);real+=pr;imag+=pi
    return _spill((real,imag))


def _multiply_upper(a,n,x):
    y=[0j]*n
    for j in range(n):
        t1=-x[j];t2=0j
        for i in range(j):
            y[i]=_update(y[i],t1,a[i][j]);t2=_update(t2,a[i][j],x[i])
        pr,pi=_product(t1,a[j][j]);qr,qi=_product(-1+0j,t2)
        y[j]=_spill(((pr+_d(y[j].real))+qr,(pi+_d(y[j].imag))+qi))
    return y


@_guard
def inverse_symmetric(matrix):
    """Native ZSYTRF(n-cell workspace) + ZSYTRI, with full symmetric output."""
    n=_validate(matrix)
    if _compiled_symmetric is not None and n<=256:return _compiled(matrix,n,True)[0]
    a,pivots=factor_symmetric_upper(matrix);n=len(a);k=0
    while k<n:
        step=1
        if pivots[k]>0:
            a[k][k]=legacy_divide(1+0j,a[k][k])
            if k:
                scratch=[a[i][k] for i in range(k)];column=_multiply_upper(a,k,scratch)
                for i in range(k):a[i][k]=column[i]
                a[k][k]=_sub(a[k][k],_dot(scratch,column))
        else:
            t=a[k][k+1];ak=legacy_divide(a[k][k],t);akp1=legacy_divide(a[k+1][k+1],t);akkp1=legacy_divide(t,t)
            pr,pi=_product(ak,akp1);d=_spill(_mul(_e(t),(pr-1,pi+0)))
            a[k][k],a[k+1][k+1],a[k][k+1]=legacy_divide(akp1,d),legacy_divide(ak,d),legacy_divide(-akkp1,d)
            if k:
                scratch=[a[i][k] for i in range(k)];column=_multiply_upper(a,k,scratch)
                for i in range(k):a[i][k]=column[i]
                a[k][k]=_sub(a[k][k],_dot(scratch,column))
                a[k][k+1]=_sub(a[k][k+1],_dot(column,[a[i][k+1] for i in range(k)]))
                scratch=[a[i][k+1] for i in range(k)];column=_multiply_upper(a,k,scratch)
                for i in range(k):a[i][k+1]=column[i]
                a[k+1][k+1]=_sub(a[k+1][k+1],_dot(scratch,column))
            step=2
        kp=abs(pivots[k])-1
        if kp!=k:_exchange_upper(a,k,kp,step)
        k+=step
    for i in range(n):
        for j in range(i):a[i][j]=a[j][i]
    return a

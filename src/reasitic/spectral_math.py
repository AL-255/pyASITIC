"""Retained transfer/regional/table arithmetic from native/spectral.cpp."""
from functools import lru_cache
from .retained_scalar import Real as R
from .network_metrics import _divide
from .contact_math import pair,spill,scale
from .x87_math import tanh_argument,cosh_argument
from .fft import _fft,_transform_grid

PI=float.fromhex('0x1.921fb54442d18p+1')


def coefficient(values,index):
    # The original coefficient view has explicit zero records on both sides.
    return values[index]if 0<=index<len(values)else 0j


def transfer(down,first,last,k,coefficients,depths,interfaces=None):
    initial=tanh_argument(k,depths[last+1],depths[last])if down else tanh_argument(k,depths[0],depths[1])
    u,v=(1+0j,complex(initial,0.))if down else (complex(initial,0.),1+0j)
    for i in (range(last-1,first-1,-1)if down else range(1,last+1)):
        t=R(tanh_argument(k,depths[i+1],depths[i])if down else tanh_argument(k,depths[i],depths[i+1]))
        other=i+1 if down else i-1
        q=interfaces(i,other)if interfaces is not None else _divide(coefficient(coefficients,i),coefficient(coefficients,other))
        qr,qi=pair(q);ur,ui=pair(u);vr,vi=pair(v)
        pr,pi=qr*vr-qi*vi,qr*vi+qi*vr
        u,v=spill((ur+(qr*t*vr-qi*t*vi),qi*t*vr+qr*t*vi+ui)),spill((t*ur+pr,t*ui+pi))
    return u,v


def source_value(down,source,last,k,height,coefficients,depths,interfaces=None):
    index=source if down else source+1;saved=depths[index]
    depths[index]=float(height)
    try:return transfer(down,source if down else 0,last if down else source,k,coefficients,depths,interfaces)[0]
    finally:depths[index]=saved


def combine(s,ratio,upper,lower,top,bottom,ta,tb,tc,down):
    rr,ri=pair(ratio);ur,ui=pair(upper);dr,di=pair(lower);tr,ti=pair(top);br,bi=pair(bottom)
    s,a,b,c=map(R,(s,ta,tb,tc))
    pr=R(float(R(float(ur*br))-ui*bi));pi=ui*br+R(float(ur*bi))
    qr,qi=dr*tr-di*ti,dr*ti+di*tr;cr,ci=br*tr-bi*ti,ti*br+bi*tr
    sr=R(float(R(float(s*rr))-R(0.)*ri));si=R(float(s*ri+rr*R(0.)))
    up_weight,down_weight=(b,a)if down else (a,b)
    real_sum=((pr*up_weight+qr*down_weight)+R(float(cr*b))*a)+(dr*ur-di*ui)
    imag_sum=((pi*up_weight+qi*down_weight)+(ci*b)*a)+(di*ur+R(float(dr*ui)))
    numerator=spill((R(float(sr*real_sum))-si*imag_sum,imag_sum*sr+real_sum*si))
    denominator=spill((((qr-pr)+cr*c)-((c*dr)*ur-(c*di)*ui),
                       ((qi-R(float(pi)))+R(float(ci))*c)-((c*di)*ur+(c*dr)*ui)))
    return _divide(numerator,denominator)


def spectral(down,source,target,last,k,source_height,target_height,coefficients,depths,interfaces=None):
    z,c=depths,coefficients
    def interface(i,j):
        return interfaces(i,j)if interfaces is not None else _divide(coefficient(c,i),coefficient(c,j))
    ta=tanh_argument(k,z[target if down else target+1],target_height)
    tb=tanh_argument(k,z[target+1 if down else target],source_height)
    tc=tanh_argument(k,z[target+1],z[target]);weight=1.
    for i in range(target if down else source,(source if down else target)+1):
        a,b,d=cosh_argument(k,z[0],z[i+1]),cosh_argument(k,z[0],z[i]),cosh_argument(k,z[i+1],z[i],True)
        weight=float((R(a)/(R(b)*R(d)))*R(weight))
    top,bottom,lower=0j,0j,1+0j
    if target==last:top=interface(target,target-1)
    else:
        if target!=0:top=interface(target,target-1)
        bottom=interface(target,target+1)
        u,v=transfer(True,target+1,last,k,c,z,interface);lower=_divide(u,v)
    u,v=transfer(False,0,target-1,k,c,z,interface);upper=_divide(u,v)
    ratio=_divide(source_value(down,source,last,k,source_height,c,z,interface),source_value(down,target,last,k,source_height,c,z,interface))
    value=combine(weight,ratio,upper,lower,top,bottom,ta,tb,tc,down)
    first=cosh_argument(k,z[target if down else source],target_height if down else source_height)
    value=spill(scale(pair(value),R(first)))
    second=cosh_argument(k,z[0],z[target if down else source]);third=cosh_argument(k,z[0],z[(source if down else target)+1])
    value=spill(scale(pair(value),R(second)/R(third)))
    final=cosh_argument(k,z[(source if down else target)+1],source_height if down else target_height)
    vr,vi=pair(value);real=vr*R(final)-vi*R(0.);imag=R(0.)*vr+vi*R(final)
    cr,ci=pair(c[target]);weighted=spill((real*cr-imag*ci,ci*R(float(real))+cr*imag))
    return _divide(weighted,complex(k,0.))


def tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records,*,include_storage=False):
    depths=list(depth_records)
    @lru_cache(maxsize=None)
    def interface(i,j):return _divide(coefficient(coefficients,i),coefficient(coefficients,j))
    @lru_cache(maxsize=None)
    def sample(k,y_axis):
        sl,sh,st=metal_records[source];tl,th,tt=metal_records[target];down=sh<th
        if source!=target:
            if down!=y_axis:sh=float(R(sh)+R(.5)*R(st));th=float(R(th)-R(.5)*R(tt))
            else:sh=float(R(sh)-R(.5)*R(st));th=float(R(th)+R(.5)*R(tt))
        return spectral(down,sl,tl,len(coefficients)-1,k,sh,th,coefficients,depths,interface)
    cells=max((nx+1)*(ny+1),nx*(nx+1)+ny+1);xy=[0j]*cells
    # The native producer strides by nx+1; the FFT consumes ny+1. On
    # rectangular grids even boundary zero stores can overwrite earlier
    # samples, so preserve every write in its original order.
    for x in range(nx+1):
        for y in range(ny+1):
            if x==0 or y==0 or x==nx or y==ny:
                xy[x*(nx+1)+y]=0j
                continue
            kx,ky=(R(x)*R(PI))/R(width),(R(y)*R(PI))/R(height)
            value=sample(float((kx*kx+ky*ky).sqrt()),False)
            for divisor in (x,x,y,y):value=_divide(value,complex(divisor,0.))
            xy[x*(nx+1)+y]=value
    workspace=[]
    _transform_grid(xy,nx,ny,observe_storage=workspace.extend if include_storage else None);tx=[0j]*(2*nx);ty=[0j]*(2*ny)
    for i in range(1,nx):
        value=sample(float((R(i)*R(PI))/R(width)),False);divisor=complex(i,0.)
        tx[i]=_divide(_divide(value,divisor),divisor)
    for i in range(1,ny):
        value=sample(float((R(i)*R(PI))/R(height)),True);divisor=complex(i,0.)
        ty[i]=_divide(_divide(value,divisor),divisor)
    for i in range(nx,2*nx):tx[i]=tx[2*nx-i]
    for i in range(ny,2*ny):ty[i]=ty[2*ny-i]
    _fft(tx);_fft(ty)
    return (tx,ty,xy,tuple(workspace))if include_storage else(tx,ty,xy)

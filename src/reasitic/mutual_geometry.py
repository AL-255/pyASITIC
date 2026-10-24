"""Retained canonical basis and coplanar mutual formula from mutual.cpp."""
from decimal import Decimal,localcontext
from fractions import Fraction
from .retained_scalar import Real as R
from .impedance import _log

EPS=1e-10

def dot(a,b):return (R(a[0])*b[0]+R(a[1])*b[1])+R(a[2])*b[2]
def distance(a,b):
    d=[R(y)-x for x,y in zip(a,b)]
    return ((d[0]*d[0]+d[1]*d[1])+d[2]*d[2]).sqrt()
def norm(a):return dot(a,a).sqrt()
def cross(a,b):return [float(R(a[1])*b[2]-R(a[2])*b[1]),float(R(a[2])*b[0]-R(a[0])*b[2]),float(R(a[0])*b[1]-R(a[1])*b[0])]
def unit(a):
    n=norm(a)
    return [float(R(v)/n)for v in a]if n>EPS else [0.,0.,0.]

def canonical(a,b):
    from .inductance import _intersects,_basis_delta
    da=[float(R(a[i+3])-a[i])for i in range(3)];db=[float(R(b[i+3])-b[i])for i in range(3)]
    if abs(dot(da,db))<EPS:return 5
    na,nb=norm(da),norm(db)
    if na<EPS or nb<EPS:return 6
    u,v=unit(da),unit(db)
    def length(s,d):
        for i in range(3):
            delta=R(s[i+3])-s[i]
            if abs(delta)>EPS and abs(d[i])>EPS:return float(delta/R(d[i]))
        return 0.
    la,lb=length(a,u),length(b,v)
    if la==0. or lb==0.:return 4
    if _intersects(a[:3],u,b[:3],v,la,lb):return 3
    delta=[_basis_delta(a[i],a[i+3],i==2)for i in range(3)]
    start=[float(R(b[i])-a[i])for i in range(3)];end=[float(R(b[i+3])-a[i])for i in range(3)]
    if norm(delta)<EPS:return 4
    e1=unit(delta);e3=cross(e1,unit(start))
    if norm(e3)<EPS:
        e3=cross(e1,unit(end))
        if norm(e3)<EPS:return 0
    e3=unit(e3);e2=unit(cross(e3,e1))
    a[:6]=[0.,0.,0.,float(norm(delta)),0.,0.]
    last_z=dot(end,e3)
    b[:6]=[float(dot(start,e1)),float(dot(start,e2)),float(dot(start,e3)),float(dot(end,e1)),float(dot(end,e2)),float(last_z)]
    projection=abs(((R(a[0])-a[3])*(R(b[0])-b[3])+(R(a[1])-a[4])*(R(b[1])-b[4]))+(R(a[2])-a[5])*(R(b[2])-last_z))
    if abs(projection-distance(b[:3],b[3:6])*R(float(distance(a[:3],a[3:6]))))<EPS:return 0
    return 1 if abs(b[5])<EPS and abs(b[2])<EPS else 2

def atanh(x):
    a=abs(x);u=-(a+a)/(a+R(1.))
    if abs(u)>=R._result(Fraction(0x95f619980c4336f8,1<<65)):logarithm=_log(R(1.)+u)
    else:
        with localcontext() as context:
            context.prec=100
            value=Decimal(u.value.numerator)/Decimal(u.value.denominator)
            result=(Decimal(1)+value).ln()/Decimal(2).ln()
            logarithm=R._result(Fraction(result)*Fraction(0xb17217f7d1cf79ac,1<<64))
    return (R(-.5)*logarithm)*(R(1.)if x>=0. else R(-1.))

def planar(a,b):
    from .precision import _atan2,_decimal,_trig
    d0=float(distance(a[3:6],b[3:6]));d1=float(distance(a[3:6],b[:3]));d2=float(distance(a[:3],b[:3]));d3=float(distance(a[:3],b[3:6]))
    la=float(distance(a[:3],a[3:6]));raw_lb=distance(b[:3],b[3:6]);lb=float(raw_lb)
    p2=float(R(d3)*d3);q2=float(R(d2)*d2);diff=float(R(p2)-R(d2)*d2)
    r2,s2=R(d1)*d1,R(d0)*d0;delta=(R(diff)+r2)-s2;delta64=float(delta);magnitude=abs(delta)
    a2,b2=R(la)*la,raw_lb*raw_lb;cosine=magnitude/((R(la)+la)*lb)
    with localcontext() as context:
        context.prec=44
        angle=float(R._result(Fraction(_atan2(_decimal((R(1.)-cosine*cosine).sqrt().value),_decimal(cosine.value)))))
        cosangle=float(R._result(_trig(Fraction(angle),True)))
    if min(abs(v)for v in (d0,d1,d2,d3))<EPS:
        if abs(d0)<EPS:d0=d2
        elif abs(d1)<EPS:d0=d3
        elif not abs(d2)<EPS and abs(d3)<EPS:d0=d1
        hb=float(atanh(R(lb)/(R(la)+d0)));ha=float(atanh(R(la)/(R(lb)+d0)))
        total=R(lb)*ha+R(hb)*la
    else:
        if delta64>EPS:w=R(diff)-b2;v=(R(float(r2))-q2)-a2
        else:v=(s2-p2)-a2;w=(R(q2)-p2)-b2
        numerator=R(la)*((b2+b2)*v+magnitude*w);denominator=a2*R(4.)*b2-R(delta64)*delta64
        x=numerator/denominator;y=(R(lb)*(magnitude*v+w*(a2+a2)))/denominator
        hb0=float(atanh(R(lb)/(R(d0)+d1)));hb1=float(atanh(R(lb)/(R(d2)+d3)))
        ha0=float(atanh(R(la)/(R(d0)+d3 if delta64>EPS else R(d1)+d2)))
        ha1=float(atanh(R(la)/(R(d1)+d2 if delta64>EPS else R(d0)+d3)))
        total=((y+lb)*ha0+(R(hb0)*(x+la)-R(hb1)*x))-R(ha1)*y
    return float((R(cosangle)+cosangle)*total)

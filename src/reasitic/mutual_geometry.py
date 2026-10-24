"""Retained canonical basis, intersections and planar/spatial mutual formulas."""
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
    return [float(R(v)/n)for v in a]

def intersects(p,u,q,v,la,lb):
    xy=float(R(float(R(v[0])*u[1]))-R(u[0])*v[1])
    xz=float(R(float(R(v[0])*u[2]))-R(u[0])*v[2])
    yz=float(R(v[1])*u[2]-R(u[1])*v[2])
    if all(abs(value)<EPS for value in (xy,xz,yz)):
        x,y,z=(abs(value)>EPS for value in u)
        tx=(R(q[0])-p[0])/R(u[0])if x else R(0.)
        ty=(R(q[1])-p[1])/R(u[1])if y else R(0.)
        tz=float((R(q[2])-p[2])/R(u[2]))if z else 0.
        if x and y and z:collinear=abs(tx-ty)<EPS and abs(tx-tz)<EPS
        elif x and y:collinear=abs(tx-ty)<EPS
        elif x and z:collinear=abs(tx-tz)<EPS
        elif y and z:collinear=abs(ty-tz)<EPS
        elif x:collinear=abs(R(p[1])-q[1])<EPS and abs(R(p[2])-q[2])<EPS
        elif y:collinear=abs(R(p[0])-q[0])<EPS and abs(R(p[2])-q[2])<EPS
        elif z:collinear=abs(R(p[0])-q[0])<EPS and abs(R(p[1])-q[1])<EPS
        else:collinear=False
        if not collinear:return False
        k=0 if u[0]!=0. else 1 if u[1]!=0. else 2
        delta=R(q[k])-p[k];first=delta/R(u[k]);last=(R(lb)*v[k]+delta)/R(u[k])
        return EPS<first and first+EPS<la and EPS<last and last+EPS<lb
    axes=None;det=xy
    if abs(xy)>EPS:axes=(0,1,2)
    elif abs(xz)>EPS:axes=(0,2,1);det=xz
    elif abs(yz)>EPS:axes=(1,2,0);det=yz
    # The segment entry point starts with zeroed projection history. Retain
    # those slots if no strict comparison selected a projection.
    if axes is None:pu=pv=delta=[0.,0.,0.]
    else:
        pu=[u[i]for i in axes];pv=[v[i]for i in axes]
        delta=[float(R(q[i])-p[i])for i in axes]
    di,dj,dk=delta
    t=(R(dj)*pv[0]-R(di)*pv[1])/R(det)
    s=(R(dj)*pu[0]-R(di)*pu[1])/R(det)
    if abs((t*pu[2]-s*pv[2])-dk)>EPS:return False
    return EPS<t and t+EPS<la and EPS<s and s+EPS<lb

def canonical(a,b):
    from .inductance import _basis_delta
    da=[float(R(a[i+3])-a[i])for i in range(3)];db=[float(R(b[i+3])-b[i])for i in range(3)]
    if abs(dot(da,db))<EPS:return 5
    na,nb=norm(da),norm(db)
    if na<EPS or nb<EPS:return 6
    u=[float(R(value)/na)for value in da]if na>EPS else da.copy()
    v=[float(R(value)/nb)for value in db]if nb>EPS else db.copy()
    def length(s,d):
        for i in range(3):
            delta=R(s[i+3])-s[i]
            if abs(delta)>EPS and abs(d[i])>EPS:return float(delta/R(d[i]))
        return 0.
    la,lb=length(a,u),length(b,v)
    if la==0. or lb==0.:return 4
    if intersects(a[:3],u,b[:3],v,la,lb):return 3
    delta=[_basis_delta(a[i],a[i+3],i==2)for i in range(3)]
    start=[float(R(b[i])-a[i])for i in range(3)];end=[float(R(b[i+3])-a[i])for i in range(3)]
    if norm(delta)<EPS:return 4
    first=unit(start)if norm(start)>EPS else [0.,0.,0.]
    last=unit(end)if norm(end)>EPS else [0.,0.,0.]
    e1=unit(delta);e3=cross(e1,first)
    if norm(e3)<EPS:
        e3=cross(e1,last)
        if norm(e3)<EPS:return 0
    e3=unit(e3);e2=unit(cross(e3,e1))
    a[:6]=[0.,0.,0.,float(norm(delta)),0.,0.]
    last_z=dot(end,e3)
    b[:6]=[float(dot(start,e1)),float(dot(start,e2)),float(dot(start,e3)),float(dot(end,e1)),float(dot(end,e2)),float(last_z)]
    projection=abs(((R(a[0])-a[3])*(R(b[0])-b[3])+(R(a[1])-a[4])*(R(b[1])-b[4]))+(R(a[2])-a[5])*(R(b[2])-last_z))
    if abs(projection-distance(b[:3],b[3:6])*R(float(distance(a[:3],a[3:6]))))<EPS:return 0
    return 1 if abs(b[5])<EPS and abs(b[2])<EPS else 2

def atanh(x):
    if x.kind:return R(float('nan'))
    a=abs(x);u=-(a+a)/(a+R(1.))
    if abs(u)>=R._result(Fraction(0x95f619980c4336f8,1<<65)):logarithm=_log(R(1.)+u)
    else:
        with localcontext() as context:
            context.prec=100
            value=Decimal(u.value.numerator)/Decimal(u.value.denominator)
            z=value/(Decimal(2)+value);square=z*z;power=total=z
            for i in range(1,65):power*=square;total+=power/(2*i+1)
            result=(2*total)/Decimal(2).ln()
            logarithm=R._result(Fraction(result)*Fraction(0xb17217f7d1cf79ac,1<<64),negative=u.negative)
    return (R(-.5)*logarithm)*(R(1.)if x>=0. else R(-1.))

def angle(y,x):
    from .precision import _atan2,_decimal,PI
    if y.kind==2 or x.kind==2:return R(float('nan'))
    with localcontext() as context:
        context.prec=80
        if not y.kind and not y.value:result=PI if x.negative else Decimal(0)
        elif not x.kind and not x.value:result=PI/2
        elif y.kind and x.kind:result=3*PI/4 if x.negative else PI/4
        elif y.kind:result=PI/2
        elif x.kind:result=PI if x.negative else Decimal(0)
        else:return R._result(Fraction(_atan2(_decimal(y.value),_decimal(x.value))))
        return R._result(Fraction(-result if y.negative else result),negative=y.negative)

def trig(value,cosine):
    from .polygon import _trig
    return float(_trig(R(value),cosine))

def planar(a,b):
    d0=float(distance(a[3:6],b[3:6]));d1=float(distance(a[3:6],b[:3]));d2=float(distance(a[:3],b[:3]));d3=float(distance(a[:3],b[3:6]))
    la=float(distance(a[:3],a[3:6]));raw_lb=distance(b[:3],b[3:6]);lb=float(raw_lb)
    p2=float(R(d3)*d3);q2=float(R(d2)*d2);diff=float(R(p2)-R(d2)*d2)
    r2,s2=R(d1)*d1,R(d0)*d0;delta=(R(diff)+r2)-s2;delta64=float(delta);magnitude=abs(delta)
    a2,b2=R(la)*la,raw_lb*raw_lb;cosine=magnitude/((R(la)+la)*lb)
    theta=float(angle((R(1.)-cosine*cosine).sqrt(),cosine))
    cosangle=trig(theta,True)
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

def spatial(a,b):
    d0=float(distance(a[3:6],b[3:6]));d1=float(distance(a[3:6],b[:3]));d2=float(distance(a[:3],b[:3]));d3=float(distance(a[:3],b[3:6]))
    la=float(distance(a[:3],a[3:6]));lb=float(distance(b[:3],b[3:6]))
    p2=float(R(d3)*d3);q2=float(R(d2)*d2);diff=float(R(p2)-R(d2)*d2)
    r2,s2=R(d1)*d1,R(d0)*d0;delta=(R(diff)+r2)-s2;delta64=float(delta);magnitude=abs(delta)
    cosine=magnitude/((R(la)+la)*lb)
    theta=float(angle((R(1.)-cosine*cosine).sqrt(),cosine));c,s=trig(theta,True),trig(theta,False)
    a2,b2=R(la)*la,R(lb)*lb
    if delta64>EPS:w=R(diff)-b2;v=(R(float(r2))-q2)-a2
    else:v=(s2-p2)-a2;w=(R(q2)-p2)-b2
    den=a2*R(4.)*b2-R(delta64)*delta64
    x=(R(la)*(magnitude*w+(b2+b2)*v))/den
    y=(R(lb)*(w*(a2+a2)+magnitude*v))/R(float(den))
    h2=(x+x)*y*c+(((R(q2)if delta64>EPS else R(p2))-x*x)-y*y)
    h=float(h2.sqrt());n=R(c)*h2;xp=x+la;yp=float(y+lb)
    a0=float(angle(xp*(y+lb)*s*s+n,R(h)*(d0 if delta64>EPS else d1)*s))
    a1=float(angle(n+xp*y*s*s,R(h)*(d1 if delta64>EPS else d0)*s))
    a2angle=float(angle(n+x*y*s*s,R(h)*(d2 if delta64>EPS else d3)*s))
    a3=float(angle(x*yp*s*s+n,R(h)*(d3 if delta64>EPS else d2)*s))
    angular=((R(a0)-a1)+a2angle)-a3
    hb0=float(atanh(R(lb)/(R(d0)+d1)));hb1=float(atanh(R(lb)/(R(d2)+d3)))
    ha0=float(atanh(R(la)/(R(d1)+d2 if delta64>EPS else R(d0)+d3)))
    ha1=float(atanh(R(la)/(R(d0)+d3 if delta64>EPS else R(d1)+d2)))
    total=R(ha1)*yp+((R(hb0)*xp-R(hb1)*x)-y*ha0)
    return float(((total+total)-(angular*h)/R(s))*R(c))

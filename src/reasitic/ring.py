"""Retained ring vertices from winding_construction.cpp / original 0x0805b450."""
import math
from .polygon import PI,TAU,_trig
from .retained_scalar import Real as R


def vertices(radius,sides,width,gap,angle):
    """Center/outer/inner XY stores; gap and orientation are binary64 radians."""
    if not all(math.isfinite(v)for v in(radius,sides,width,gap,angle))or sides!=int(sides)or not 3<=sides<=1024 or min(radius,width)<=0:
        raise ValueError('Invalid ring geometry configuration')
    sides=int(sides);last=sides-1;gap=abs(R(gap));radius=R(radius)
    cosine=float(_trig(R(PI)/R(sides),True))
    ribbon=float(R(width)/R(cosine))
    step=(R(TAU)-gap)/R(last)
    if step<0:raise ValueError('Native ring gap exceeds a full turn after command parsing')
    theta=gap*R(.5)+R(angle)
    center=radius-R(ribbon)*R(.5);inner=radius-R(ribbon)
    def vertex(t,final=False):
        c,s=_trig(t,True),_trig(t,False)
        # Only the final center-X cosine spills before multiplying its radius.
        cx=R(float(c))if final else c
        return [float(cx*center),float(s*center),float(c*radius),float(s*radius),float(c*inner),float(s*inner)]
    previous=vertex(theta);rows=[]
    for i in range(1,last+1):
        final=i==last
        t=R(angle)-gap*R(.5)if final else step*R(i)+theta
        point=vertex(t,final)
        rows.append([v for k in range(3)for pair in(previous[2*k:2*k+2],point[2*k:2*k+2])for v in pair]);previous=point
    offsets=(4,6,8,10,0,2);x0=y0=1e15;x1=y1=-1e15
    for row in rows:
        for k in offsets:
            x,y=row[k:k+2]
            if x<x0:x0=x
            if x1<x:x1=x
            if y<y0:y0=y
            if y1<y:y1=y
    dx,dy=(R(x1)-R(x0))*R(.5),(R(y1)-R(y0))*R(.5)
    for row in rows:
        for k in offsets:row[k],row[k+1]=float(R(row[k])+dx),float(R(row[k+1])+dy)
    return rows

"""Retained contact-potential arithmetic from native/contact.cpp.

Table entries and complex stores are binary64. Each intervening scalar
operation rounds to the original extended significand. The zero term depends
on the ordered metal pair and can be reused within one matrix assembly.
"""
from .retained_scalar import Real as R
from .network_metrics import _divide

FACTOR=float.fromhex('0x1.3bd3cc9be45dep+4')


def pair(z):return R(z.real),R(z.imag)
def spill(z):return complex(float(z[0]),float(z[1]))
def difference(a,b):
    ar,ai=pair(a);br,bi=pair(b)
    return ar-br,ai-bi
def add(a,b):
    ar,ai=pair(a);br,bi=pair(b)
    return spill((ar+br,ai+bi))
def scale(z,n):return z[0]*R(n)-z[1]*R(0.),z[1]*R(n)+z[0]*R(0.)
def divide(z,*denominators):
    for denominator in denominators:z=_divide(z,complex(denominator,0.))
    return z


def transfer(layer,coefficients,depths):
    slope,offset=1+0j,complex(depths[0],0.)
    for k in range(1,layer+1):
        ratio=_divide(coefficients[k],coefficients[k-1]);rr,ri=pair(ratio)
        sr,si=pair(slope);orr,oi=pair(offset)
        real=(rr-R(1.))*R(depths[k]);imag=ri*R(depths[k])
        next_slope=spill((rr*sr-ri*si,ri*sr+rr*si))
        offset=spill(((real*sr-imag*si)+orr,(real*si+imag*sr)+oi))
        slope=next_slope
    return slope,offset


def slope_to(layer,coefficients):
    result=1+0j
    for k in range(1,layer+1):
        rr,ri=pair(_divide(coefficients[k],coefficients[k-1]));sr,si=pair(result)
        result=spill((rr*sr-ri*si,si*rr+ri*sr))
    return result


def zero_potential(source,target,height,target_height,coefficients,depths,down):
    if down:
        slope,offset=transfer(target,coefficients,depths)
        denominator=slope;height=target_height
    else:
        slope,offset=transfer(source,coefficients,depths)
        denominator=slope_to(target,coefficients)
    sr,si=pair(slope);orr,oi=pair(offset);cr,ci=pair(coefficients[target])
    real=orr-R(height)*sr;imag=oi-R(height)*si
    return _divide(spill((real*cr-imag*ci,imag*cr+ci*real)),denominator)


def base(source,target,width,height,records,coefficients,depths):
    sl,sh,st=records[source];tl,th,tt=records[target]
    source_half=R(0.)if source==target else R(st)*R(.5)
    target_half=R(0.)if source==target else R(tt)*R(.5)
    down=sh<th
    source_height=float(R(sh)+source_half)if down else float(R(sh)-source_half)
    target_height=float(R(th)-target_half)
    term=zero_potential(sl,tl,source_height,target_height,coefficients,depths,down)
    return add(0j,divide(term,width,height))


def i32(n):return (n+(1<<31))%(1<<32)-(1<<31)
def indices(a0,a1,b0,b1,limit):
    def distance(a,b):
        delta=i32(a-b)
        return delta if delta>0 else i32(-delta)
    def folded(a,b):
        total=i32(a+b)
        return total if total<limit else i32(i32(limit+limit)-total)
    return (distance(a0,b0),distance(a0,b1),distance(a1,b0),distance(a1,b1),
            folded(a0,b0),folded(a0,b1),folded(a1,b0),folded(a1,b1))


def axis_sum(table,index):
    d00,d01,d10,d11,s00,s01,s10,s11=index
    first=difference(table[d11],table[s11]);second=difference(table[d00],table[s00])
    third=difference(table[s10],table[d10]);fourth=difference(table[s01],table[d01])
    return tuple(((second[k]+R(float(first[k])))+third[k])+fourth[k]for k in range(2))


def potential(a,b,nx,ny,width,height,metal_records,coefficients,depths,tables,zero_terms=None):
    x=indices(a.x0,a.x1,b.x0,b.x1,nx);y=indices(a.y0,a.y1,b.y0,b.y1,ny)
    ordered_pair=a.metal,b.metal
    if zero_terms is not None and ordered_pair in zero_terms:total=zero_terms[ordered_pair]
    else:
        total=base(*ordered_pair,width,height,metal_records,coefficients,depths)
        if zero_terms is not None:zero_terms[ordered_pair]=total
    area_x=i32(i32(b.x1-b.x0)*i32(a.x1-a.x0));area_y=i32(i32(b.y1-b.y0)*i32(a.y1-a.y0))
    tx,ty,txy=tables;nx2,ny2=i32(nx*nx),i32(ny*ny)
    term=spill(scale(axis_sum(tx,x),nx2))
    total=add(total,divide(term,width,height,FACTOR,area_x))
    term=spill(scale(axis_sum(ty,y),ny2))
    total=add(total,divide(term,width,height,FACTOR,area_y))
    xd00,xd01,xd10,xd11,xs00,xs01,xs10,xs11=x
    yd00,yd01,yd10,yd11,ys00,ys01,ys10,ys11=y
    rows=(xd11,xd00,xs10,xs01,xs11,xs00,xd10,xd01)
    positive=(yd00,yd11,ys10,ys01);negative=(ys00,ys11,yd10,yd01)
    combined=R(0.),R(0.)
    for row,index in enumerate(rows):
        for column in range(4):
            j=1-column if column<2 else column;offset=i32(index*i32(nx+1))
            delta=difference(txy[i32(offset+positive[j])],txy[i32(offset+negative[j])])
            if row==0 and column==0:combined=tuple(R(float(v))for v in delta)
            elif row<4:combined=tuple(a+b for a,b in zip(combined,delta))
            else:combined=tuple(a-b for a,b in zip(combined,delta))
    term=spill(scale(scale(combined,nx2),ny2))
    return add(total,divide(term,area_x,area_y,width,height,FACTOR,FACTOR))

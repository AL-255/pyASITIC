"""Layered-substrate contact-potential capacitance solver.

Ports potential_tables.cpp, potential.cpp, contacts.cpp and potential_solver.cpp.
Geometry uses micrometres, substrate resistivity ohm-cm, frequency Hz. The FFT
uses the original positive-sign, unnormalized twiddle recurrence. Tables are
generated on demand for the same packed metal pairs used by the native solver.
"""
from dataclasses import dataclass
from functools import lru_cache
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
import copy
import math
from .solver import inverse
from .inductance import _round_extended

EPSILON0=float.fromhex("0x1.8ebfab864ade4p-44")
FACTOR=float.fromhex("0x1.3bd3cc9be45dep+4")


def _divide(a,b):
    # The legacy complex division retains its ratio and denominator extended.
    with localcontext() as context:
        context.prec=25
        ar,ai,br,bi=(Decimal.from_float(float(v)) for v in (a.real,a.imag,b.real,b.imag))
        if abs(bi)>=abs(br):
            ratio=br/bi
            denominator=ratio*ratio*bi+bi
            return complex(float((ar*ratio+ai)/denominator),float((ai*ratio-ar)/denominator))
        ratio=bi/br
        denominator=ratio*ratio*br+br
        return complex(float((ai*ratio+ar)/denominator),float((ai-ar*ratio)/denominator))


def _spectral_combine(scale,ratio,upper,lower,top,bottom,ta,tb,tc,down):
    with localcontext() as context:
        context.prec=25
        dec=Decimal.from_float
        def spill(value):
            return dec(float(value))
        rr,ri,ur,ui,dr,di,tr,ti,br,bi=(dec(v) for z in (ratio,upper,lower,top,bottom) for v in (z.real,z.imag))
        s,a,b,c=map(dec,(scale,ta,tb,tc))
        pr=spill(spill(ur*br)-ui*bi)
        pi=ui*br+spill(ur*bi)
        qr,qi=dr*tr-di*ti,dr*ti+di*tr
        cr,ci=br*tr-bi*ti,ti*br+bi*tr
        sr,si=spill(spill(s*rr)),spill(s*ri)
        up_weight,down_weight=(b,a) if down else (a,b)
        real_sum=((pr*up_weight+qr*down_weight)+spill(cr*b)*a)+(dr*ur-di*ui)
        imag_sum=((pi*up_weight+qi*down_weight)+(ci*b)*a)+(di*ur+spill(dr*ui))
        numerator=complex(float(spill(sr*real_sum)-si*imag_sum),float(imag_sum*sr+real_sum*si))
        denominator=complex(float(((qr-pr)+cr*c)-((c*dr)*ur-(c*di)*ui)),
                            float(((qi-spill(pi))+spill(ci)*c)-((c*di)*ur+(c*dr)*ui)))
        return _divide(numerator,denominator)


@lru_cache(maxsize=16)
def _fft_plan(n):
    with localcontext() as context:
        context.prec=25
        def extended(value):
            value=_round_extended(Fraction(value))
            return Decimal(value.numerator)/Decimal(value.denominator)
        def sine(value):
            term=total=value
            square=value*value
            for i in range(1,60):
                term*=-square/((2*i)*(2*i+1))
                total+=term
                if abs(term)<Decimal("1e-27"):
                    return extended(total)
            raise ValueError("FFT sine failed to converge")
        plan=[]
        half=1
        while half<n:
            step=2*half
            angle=Decimal.from_float(float.fromhex("0x1.921fb54442d1cp+2"))/step
            small=sine(angle/2)
            wpr=extended(extended(-2*small)*small)
            wpi=Decimal.from_float(float(sine(angle)))
            wr,wi=Decimal(1),Decimal(0)
            weights=[]
            for m in range(half):
                weights.append((wr,wi))
                old_wr=wr
                wr=extended(extended(extended(wr*wpr)-extended(wi*wpi))+wr)
                wi=extended(extended(extended(wi*wpr)+extended(old_wr*wpi))+wi)
            plan.append((half,weights))
            half=step
        return plan


@lru_cache(maxsize=512)
def _fft_quantum(exponent):
    with localcontext() as context:
        context.prec=256
        return Decimal(2)**exponent


def _fft_extended(value):
    if not value:
        return value
    exponent=math.frexp(float(value))[1]-64
    quantum=_fft_quantum(exponent)
    return (value/quantum).to_integral_value(rounding=ROUND_HALF_EVEN)*quantum


def _fft(values):
    n=len(values)
    j=0
    for i in range(n-1):
        if i<j:
            values[j],values[i]=values[i],values[j]
        k=n>>1
        while k>1 and j>=k:
            j-=k
            k>>=1
        j+=k
    # Native twiddles remain extended while each butterfly output is spilled
    # to binary64. Keeping that precision prevents the large reactive channel
    # from contaminating small substrate-loss terms through roundoff.
    with localcontext() as context:
        context.prec=25
        convert=Decimal.from_float
        for half,weights in _fft_plan(n):
            step=2*half
            for m,(wr,wi) in enumerate(weights):
                for i in range(m,n,step):
                    a,b=values[i],values[i+half]
                    ar,ai,br,bi=convert(a.real),convert(a.imag),convert(b.real),convert(b.imag)
                    tr=_fft_extended(_fft_extended(wr*br)-_fft_extended(wi*bi))
                    ti=_fft_extended(_fft_extended(wr*bi)+_fft_extended(wi*br))
                    values[i+half]=complex(float(_fft_extended(ar-tr)),float(_fft_extended(ai-ti)))
                    values[i]=complex(float(_fft_extended(tr+ar)),float(_fft_extended(ti+ai)))


def _transform_grid(grid,nx,ny):
    stride=ny+1
    for x in range(nx+1):
        scratch=[grid[x*stride+y] for y in range(ny+1)]
        scratch.extend(grid[x*stride+2*ny-y] for y in range(ny+1,2*ny))
        _fft(scratch)
        for y in range(ny+1):
            grid[x*stride+y]=scratch[y]
    for y in range(ny+1):
        scratch=[grid[x*stride+y] for x in range(nx+1)]
        scratch.extend(grid[(2*nx-x)*stride+y] for x in range(nx+1,2*nx))
        _fft(scratch)
        for x in range(nx+1):
            grid[x*stride+y]=scratch[x]


def _transfer(down,first,last,k,coefficients,depths):
    initial=math.tanh(k*(depths[last+1]-depths[last] if down else depths[0]-depths[1]))
    u,v=(1+0j,complex(initial)) if down else (complex(initial),1+0j)
    for i in (range(last-1,first-1,-1) if down else range(1,last+1)):
        argument=k*(depths[i+1]-depths[i] if down else depths[i]-depths[i+1])
        q=_divide(coefficients[i],coefficients[i+1 if down else i-1])
        t=math.tanh(argument)
        with localcontext() as context:
            context.prec=25
            qr,qi,ur,ui,vr,vi=(Decimal.from_float(value) for z in (q,u,v) for value in (z.real,z.imag))
            dt=Decimal.from_float(t)
            pr,pi=qr*vr-qi*vi,qr*vi+qi*vr
            u,v=complex(float(ur+(qr*dt*vr-qi*dt*vi)),float(qi*dt*vr+qr*dt*vi+ui)),complex(float(dt*ur+pr),float(dt*ui+pi))
    return u,v


def _source(down,source,last,k,height,coefficients,depths):
    index=source if down else source+1
    saved=depths[index]
    depths[index]=height
    try:
        return _transfer(down,source if down else 0,last if down else source,k,coefficients,depths)[0]
    finally:
        depths[index]=saved


def _cosh(x):
    if x>500:
        return 1e15
    e=math.exp(x)
    return .5*(1/e+e)


def _spectral(down,source,target,last,k,source_height,target_height,coefficients,depths):
    z,c=depths,coefficients
    ta=math.tanh(k*(z[target if down else target+1]-target_height))
    tb=math.tanh(k*(z[target+1 if down else target]-source_height))
    tc=math.tanh(k*(z[target+1]-z[target]))
    scale=1.0
    for i in range(target if down else source,(source if down else target)+1):
        a=_cosh(k*(z[0]-z[i+1]))
        b=_cosh(k*(z[0]-z[i]))
        d=_cosh(k*(z[i+1]-z[i]))
        scale=a/(b*d)*scale
    top,bottom,lower=0j,0j,1+0j
    if target==last:
        top=_divide(c[target],c[target-1])
    else:
        if target!=0:
            top=_divide(c[target],c[target-1])
        bottom=_divide(c[target],c[target+1])
        u,v=_transfer(True,target+1,last,k,c,z)
        lower=_divide(u,v)
    u,v=_transfer(False,0,target-1,k,c,z)
    upper=_divide(u,v)
    ratio=_divide(_source(down,source,last,k,source_height,c,z),_source(down,target,last,k,source_height,c,z))
    value=_spectral_combine(scale,ratio,upper,lower,top,bottom,ta,tb,tc,down)
    first=_cosh(k*(z[target]-target_height if down else z[source]-source_height))
    value*=first
    second=_cosh(k*(z[0]-z[target if down else source]))
    third=_cosh(k*(z[0]-z[(source if down else target)+1]))
    with localcontext() as context:
        context.prec=25
        weight=Decimal.from_float(second)/Decimal.from_float(third)
        value=complex(float(Decimal.from_float(value.real)*weight),float(Decimal.from_float(value.imag)*weight))
    final=_cosh(k*(z[(source if down else target)+1]-(source_height if down else target_height)))
    with localcontext() as context:
        context.prec=25
        dec=Decimal.from_float
        real,imag=dec(value.real)*dec(final),dec(value.imag)*dec(final)
        weighted=complex(float(real*dec(c[target].real)-imag*dec(c[target].imag)),
                         float(dec(c[target].imag)*dec(float(real))+dec(c[target].real)*imag))
    return _divide(weighted,complex(k))


@lru_cache(maxsize=16)
def _tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records):
    depths=list(depth_records)
    def sample(k,y_axis):
        sl,sh,st=metal_records[source]
        tl,th,tt=metal_records[target]
        down=sh<th
        if source!=target:
            if down!=y_axis:
                sh+=st/2
                th-=tt/2
            else:
                sh-=st/2
                th+=tt/2
        return _spectral(down,sl,tl,len(coefficients)-1,k,sh,th,coefficients,depths)
    # Native generation and lookup use nx+1 stride, while the transform uses
    # ny+1. Keep both index rules and initialize all backing cells explicitly.
    cells=max((nx+1)*(ny+1),nx*(nx+1)+ny+1)
    xy=[0j]*cells
    for x in range(1,nx):
        for y in range(1,ny):
            kx,ky=x*math.pi/width,y*math.pi/height
            value=sample(math.hypot(kx,ky),False)
            xy[x*(nx+1)+y]=value/x/x/y/y
    _transform_grid(xy,nx,ny)
    tx=[0j]*(2*nx)
    ty=[0j]*(2*ny)
    for x in range(1,nx):
        tx[x]=sample(x*math.pi/width,False)/x/x
    for y in range(1,ny):
        ty[y]=sample(y*math.pi/height,True)/y/y
    for x in range(nx,2*nx):
        tx[x]=tx[2*nx-x]
    for y in range(ny,2*ny):
        ty[y]=ty[2*ny-y]
    _fft(tx)
    _fft(ty)
    return tx,ty,xy


def _zero_transfer(layer,coefficients,depths):
    slope,offset=1+0j,complex(depths[0])
    for k in range(1,layer+1):
        ratio=_divide(coefficients[k],coefficients[k-1])
        with localcontext() as context:
            context.prec=25
            rr,ri,sr,si,orr,oi=(Decimal.from_float(value) for z in (ratio,slope,offset) for value in (z.real,z.imag))
            depth=Decimal.from_float(depths[k])
            real,imag=(rr-1)*depth,ri*depth
            offset=complex(float(real*sr-imag*si+orr),float(real*si+imag*sr+oi))
            slope=complex(float(rr*sr-ri*si),float(ri*sr+rr*si))
    return slope,offset


def _zero_potential(source,target,height,target_height,coefficients,depths,down):
    if down:
        slope,offset=_zero_transfer(target,coefficients,depths)
        denominator=slope
        height=target_height
    else:
        slope,offset=_zero_transfer(source,coefficients,depths)
        denominator,_=_zero_transfer(target,coefficients,depths)
    with localcontext() as context:
        context.prec=25
        sr,si,orr,oi,cr,ci=(Decimal.from_float(value) for z in (slope,offset,coefficients[target]) for value in (z.real,z.imag))
        h=Decimal.from_float(height)
        real,imag=orr-h*sr,oi-h*si
        numerator=complex(float(real*cr-imag*ci),float(imag*cr+ci*real))
    return _divide(numerator,denominator)


@dataclass(frozen=True)
class Contact:
    x0:int
    x1:int
    y0:int
    y1:int
    metal:int


def _contacts(shape,technology,nx,ny,width,height,length_step,width_step,max_contacts=256):
    groups=[]
    contact_count=0
    pitch=max(width,height)/min(nx,ny)
    for s in shape.segments:
        if s.metal>=len(technology.metals):
            continue
        ox,oy=shape.origin
        x0,y0,x1,y1=s.start[0]+ox,s.start[1]+oy,s.end[0]+ox,s.end[1]+oy
        if not (0<=min(x0,x1) and max(x0,x1)<=width and 0<=min(y0,y1) and max(y0,y1)<=height):
            raise ValueError("Contact coordinates lie outside the technology chip")
        segment_length_step,segment_width_step=length_step,width_step
        if s.nx==s.ny==-1:
            segment_length_step=segment_width_step=max(width*10/nx,height*10/ny)
        along=max(1,int(s.length/segment_length_step+.5))
        across=max(1,int(s.width/segment_width_step+.5))
        # Jump to the native decrement loop's neighborhood rather than taking
        # billions of steps for a tiny requested cell. The final comparisons
        # retain its strict inequality and minimum-one behavior.
        across=min(across,max(1,int(s.width/pitch)+1))
        along=min(along,max(1,int(s.length/pitch)+1))
        while across>0 and s.width/across<pitch:
            across-=1
        while along>0 and s.length/along<pitch:
            along-=1
        across,along=max(across,1),max(along,1)
        contact_count+=across*along
        if contact_count>max_contacts:
            raise ValueError("Capacitance mesh exceeds the contact limit; increase contact cell sizes")
        dx,dy=x1-x0,y1-y0
        length=math.hypot(dx,dy)
        if not length:
            raise ValueError("The native potential-contact construction requires nonzero planar segment length")
        front_width=s.width if s.primary_width is None else s.primary_width
        offset_x,offset_y=(front_width/2*dy)/length,(front_width/2*dx)/length
        step_x,step_y=2*offset_x/across,2*offset_y/across
        cell_width,cell_length=front_width/across,length/along
        along_x,along_y=dx/along,dy/along
        angle=math.atan2(dy,dx)
        horizontal=abs(angle)<math.pi/4 or 3*math.pi/4<abs(angle)
        half_x=(cell_length if horizontal else cell_width)/2
        half_y=(cell_width if horizontal else cell_length)/2
        group=[]
        for i in range(across):
            for j in range(along):
                bx=x0-offset_x+i*step_x+step_x/2
                by=y0+offset_y-i*step_y-step_y/2
                ax,ay=bx+j*along_x,by+j*along_y
                ex,ey=bx+(j+1)*along_x,by+(j+1)*along_y
                cx,cy=min(ax,ex)+abs(ax-ex)/2,min(ay,ey)+abs(ay-ey)/2
                a,b=int((cx-half_x)*nx/width),int((cx+half_x)*nx/width)
                c,d=int((cy-half_y)*ny/height),int((cy+half_y)*ny/height)
                if not (0<=a<b<=nx and 0<=c<d<=ny):
                    raise ValueError("A contact collapses or exceeds the FFT grid; increase FFT resolution or move the layout inside the chip")
                group.insert(0,Contact(a,b,c,d,s.metal))
        groups.append(group)
    return groups


def _indices(a0,a1,b0,b1,limit):
    def folded(a,b):
        total=a+b
        return total if total<limit else 2*limit-total
    return (abs(a0-b0),abs(a0-b1),abs(a1-b0),abs(a1-b1),
            folded(a0,b0),folded(a0,b1),folded(a1,b0),folded(a1,b1))


def _axis_sum(table,index):
    d00,d01,d10,d11,s00,s01,s10,s11=index
    return (table[d00]-table[s00])+(table[d11]-table[s11])+(table[s10]-table[d10])+(table[s01]-table[d01])


def _contact_potential(a,b,nx,ny,width,height,metal_records,coefficients,depths,tables):
    x=_indices(a.x0,a.x1,b.x0,b.x1,nx)
    y=_indices(a.y0,a.y1,b.y0,b.y1,ny)
    sl,sh,st=metal_records[a.metal]
    tl,th,tt=metal_records[b.metal]
    source_half,target_half=(0,0) if a.metal==b.metal else (st/2,tt/2)
    term=_zero_potential(sl,tl,sh+source_half if sh<th else sh-source_half,th-target_half,coefficients,depths,sh<th)
    total=term/width/height
    area_x,area_y=(b.x1-b.x0)*(a.x1-a.x0),(b.y1-b.y0)*(a.y1-a.y0)
    tx,ty,txy=tables
    total+=_axis_sum(tx,x)*(nx*nx)/width/height/FACTOR/area_x
    total+=_axis_sum(ty,y)*(ny*ny)/width/height/FACTOR/area_y
    xd00,xd01,xd10,xd11,xs00,xs01,xs10,xs11=x
    yd00,yd01,yd10,yd11,ys00,ys01,ys10,ys11=y
    rows=(xd11,xd00,xs10,xs01,xs11,xs00,xd10,xd01)
    positive=(yd00,yd11,ys10,ys01)
    negative=(ys00,ys11,yd10,yd01)
    combined=0j
    for row,index in enumerate(rows):
        for column in range(4):
            j=1-column if column<2 else column
            offset=index*(nx+1)
            delta=txy[offset+positive[j]]-txy[offset+negative[j]]
            combined+=delta if row<4 else -delta
    return total+combined*(nx*nx)*(ny*ny)/area_x/area_y/width/height/FACTOR/FACTOR


def solve_capacitance(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,
                      fft_x=None,fft_y=None,unfolded=False,max_contacts=256,include_potential=False):
    """Original contact-potential matrix inversion and folded/unfolded reduction.

    Returned matrix is a complex admittance in siemens. `unfolded` preserves
    native node admittances; the default returns the folded branch convention.
    """
    nx=int(technology.chip.get("fftx",128) if fft_x is None else fft_x)
    ny=int(technology.chip.get("ffty",128) if fft_y is None else fft_y)
    if any(n<2 or n>256 or n&(n-1) for n in (nx,ny)):
        raise ValueError("FFT dimensions must be powers of two from 2 to 256")
    width,height=technology.chip.get("chipx",1000),technology.chip.get("chipy",1000)
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,width,height,length_cell,width_cell)):
        raise ValueError("Frequency, chip dimensions and contact cells must be finite and positive")
    ground=shape if ground is None else ground
    groups=_contacts(shape,technology,nx,ny,width,height,length_cell,width_cell,max_contacts)
    device_groups=len(groups)
    second_count=0
    if shape.name!=ground.name:
        # Explicit ground arguments have native parser type 8, which marks all
        # their segment mesh counts -1 before the capacitance driver runs.
        ground=copy.deepcopy(ground)
        for segment in ground.segments:
            segment.nx=segment.ny=-1
        remaining=max_contacts-sum(len(group) for group in groups)
        groups.extend(_contacts(ground,technology,nx,ny,width,height,length_cell,width_cell,remaining))
        second_count=len(ground.segments)
    contacts=[contact for group in groups for contact in group]
    if not 1<=len(contacts)<=max_contacts:
        raise ValueError(f"Capacitance mesh needs 1–{max_contacts} contacts")
    depths=[0.0]*(len(technology.substrate)+1)
    coefficients=[]
    weight=frequency_hz*2*math.pi*EPSILON0*1e-4
    for i in range(len(technology.substrate)-1,-1,-1):
        depths[i]=depths[i+1]+technology.substrate[i]["t"]
    for layer in technology.substrate:
        # The native .tek reader converts rho from ohm-cm to ohm-µm.
        coefficients.append(1/complex(1/(layer["rho"]*10000),weight*layer["eps"]))
    coefficients=tuple(coefficients)
    records=tuple((m.layer,depths[m.layer]-m.height,m.thickness) for m in technology.metals)
    packed={}
    full=[]
    for a in contacts:
        row=[]
        for b in contacts:
            pair=min(a.metal,b.metal),max(a.metal,b.metal)
            if pair not in packed:
                packed[pair]=_tables(*pair,nx,ny,width,height,records,coefficients,tuple(depths))
            row.append(_contact_potential(a,b,nx,ny,width,height,records,coefficients,depths,packed[pair]))
        full.append(row)
    admittance=inverse(full)
    total=sum(sum(row[:len(contacts)-second_count]) for row in admittance[:len(contacts)-second_count])
    impedance=1/total
    total_c=-1/(2*math.pi*frequency_hz*impedance.imag)
    indices=[]
    offset=0
    for group in groups:
        indices.append(list(range(offset,offset+len(group))))
        offset+=len(group)
    reduced=[[sum(admittance[i][j] for i in rows for j in columns) for columns in indices] for rows in indices]
    if unfolded:
        result=[row[:len(groups)-second_count] for row in reduced[:len(groups)-second_count]]
    else:
        result=[[sum(reduced[i]) if i==j else -reduced[i][j] for j in range(len(groups))] for i in range(len(groups))]
        if shape.name!=ground.name:
            for row in range(len(groups)-1):
                for k in range(1,second_count+1):
                    result[row][row]+=result[row][len(groups)-k]
        result=[row[:len(groups)-second_count] for row in result[:len(groups)-second_count]]
    data=dict(matrix=[[[z.real,z.imag] for z in row] for row in result],total_capacitance_f=total_c,
              total_resistance_ohm=impedance.real,frequency_hz=frequency_hz,contacts=len(contacts),segments=device_groups,
              fft_x=nx,fft_y=ny,unfolded=unfolded)
    if include_potential:
        data["potential_matrix"]=[[[z.real,z.imag] for z in row] for row in full]
    return data

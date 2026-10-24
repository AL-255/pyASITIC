"""Retained contact groups and integer grid bounds from contacts.cpp."""
from .retained_scalar import Real as R
from .mutual_geometry import angle as _angle


def _integer(value):
    # Native FISTPL under round-toward-zero returns INT_MIN on overflow.
    value=R(value)
    if value.kind:return -(1<<31)
    result=int(value.value)
    return result if -(1<<31)<=result<(1<<31)else -(1<<31)


def groups(shape,technology,nx,ny,width,height,length_step,width_step,max_contacts,contact,*,observe=None):
    result=[];contact_count=0;pitch=R(max(width,height))/R(min(nx,ny))
    for s in shape.segments:
        if s.metal>=len(technology.metals):continue
        ox,oy=shape.origin
        x0=float(R(s.start[0])+R(ox));x1=float(R(ox)+R(s.end[0]))
        raw_y0=R(s.start[1])+R(oy);y0=float(raw_y0);y1=float(R(oy)+R(s.end[1]))
        if not(0<=x0<=width and 0<=x1<=width and R(0)<=raw_y0<=R(height)and 0<=y1<=height):
            raise ValueError('Contact coordinates lie outside the technology chip')
        segment_length_step,segment_width_step=length_step,width_step
        if s.nx==s.ny==-1:
            x,y=R(width)*R(10)/R(nx),R(height)*R(10)/R(ny)
            segment_length_step=segment_width_step=float(x if y<x else y)
        delta=[R(s.end[k])-R(s.start[k])for k in range(3)]
        length=((delta[0]*delta[0]+delta[1]*delta[1])+delta[2]*delta[2]).sqrt()
        along=max(1,_integer(length/R(segment_length_step)+R(.5)))
        across=max(1,_integer(R(s.width)/R(segment_width_step)+R(.5)))
        # Jump to the neighborhood of the original decrement loop, retaining
        # its rounded divisions, strict comparisons and minimum-one behavior.
        across=min(across,max(1,int((R(s.width)/pitch).value)+1))
        along=min(along,max(1,int((length/pitch).value)+1))
        while across>0 and R(s.width)/R(across)<pitch:across-=1
        while along>0 and length/R(along)<pitch:along-=1
        across,along=max(across,1),max(along,1)
        contact_count+=across*along
        if contact_count>max_contacts:raise ValueError('Capacitance mesh exceeds the contact limit; increase contact cell sizes')
        dx,dy=R(x1)-R(x0),R(y1)-R(y0);length=(dx*dx+dy*dy).sqrt()
        if length==0:raise ValueError('The native potential-contact construction requires nonzero planar segment length')
        front_width=s.width if s.primary_width is None else s.primary_width
        half=R(front_width)*R(.5)
        offset_x=(half*dy)/length;offset_y=float((half*dx)/length)
        step_x=float(R(float(offset_x+offset_x))/R(across))
        step_y=float((R(offset_y)+R(offset_y))/R(across))
        cell_width=float(R(front_width)/R(across));cell_length=float(length/R(along))
        along_x,along_y=float(dx/R(along)),float(dy/R(along))
        angle=abs(float(_angle(dy,dx)))
        horizontal=angle<float.fromhex('0x1.921fb54442d18p-1')or float.fromhex('0x1.2d97c7f3321d2p+1')<angle
        half_x=R(cell_length if horizontal else cell_width)*R(.5)
        half_y=R(cell_width if horizontal else cell_length)*R(.5);group=[]
        for i in range(across):
            for j in range(along):
                base_x=(R(float(R(x0)-R(float(offset_x))))+R(i)*R(step_x))+R(float(R(step_x)*R(.5)))
                base_y=((R(y0)+R(offset_y))-R(float(R(i)*R(step_y))))-R(float(R(step_y)*R(.5)))
                ax,ay=base_x+R(j)*R(along_x),base_y+R(j)*R(along_y)
                bx=base_x+R(j+1)*R(along_x);by=float(base_y+R(j+1)*R(along_y))
                center_x=abs(ax-bx)*R(.5)+(ax if ax<bx else bx)
                center_y=(ay if ay<R(by)else R(by))+abs(ay-R(by))*R(.5)
                low_x=-half_x+center_x if horizontal else center_x-half_x
                high_x=half_x+center_x
                low_y=center_y-half_y if horizontal else -half_y+center_y
                high_y=center_y+half_y
                a,b=_integer((low_x*R(nx))/R(width)),_integer((high_x*R(nx))/R(width))
                c,d=_integer((low_y*R(ny))/R(height)),_integer((high_y*R(ny))/R(height))
                if observe is not None:observe((float(low_x),float(high_x),float(low_y),float(high_y)))
                if not(0<=a<b<=nx and 0<=c<d<=ny):
                    raise ValueError('A contact collapses or exceeds the FFT grid; increase FFT resolution or move the layout inside the chip')
                group.insert(0,contact(a,b,c,d,s.metal))
        result.append(group)
    return result

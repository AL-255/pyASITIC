"""Layered-substrate contact-potential capacitance solver.

Ports potential_tables.cpp, potential.cpp, contacts.cpp and potential_solver.cpp.
Geometry uses micrometres, substrate resistivity ohm-cm, frequency Hz. The FFT
uses the original positive-sign, unnormalized twiddle recurrence. Tables are
generated on demand for the same packed metal pairs used by the native solver.
"""
from dataclasses import dataclass
from array import array
from functools import lru_cache
import copy
import math
from .retained_scalar import Real
from .solver import inverse,_sum_complex
from .fft import _fft,_transform_grid,_fft_extended,_fft_spill
from .contact_kernel import contact_matrix
from .table_kernel import configuration,generate_tables,layer_coefficients
from .network_metrics import _divide
from .spectral_math import (transfer as _transfer,source_value as _source,
                            spectral as _spectral,combine as _spectral_combine,tables as _retained_tables)
from .contact_math import (potential as _contact_potential,indices as _indices,
                           transfer as _zero_transfer,zero_potential as _zero_potential)

def _tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records):
    # Tuple equality merges +0 and -0. Keep every input store in the cache
    # key, including signed zeros and the original nonfinite coefficient bits.
    return _cached_tables(configuration(source,target,nx,ny,width,height,metal_records,coefficients,depth_records).tobytes())


@lru_cache(maxsize=16)
def _cached_tables(key):
    config=array('d');config.frombytes(key)
    _,nx,ny,nm,nl,source,target,width,height=config[:9]
    nx,ny,nm,nl,source,target=map(int,(nx,ny,nm,nl,source,target))
    offset=9
    metal_records=tuple((int(config[i]),config[i+1],config[i+2])for i in range(offset,offset+3*nm,3));offset+=3*nm
    coefficients=tuple(complex(config[i],config[i+1])for i in range(offset,offset+2*nl,2));offset+=2*nl
    depth_records=tuple(config[offset:])
    compiled=generate_tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records)
    if compiled is not None:return compiled
    return _retained_tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records)


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


def solve_capacitance(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,
                      fft_x=None,fft_y=None,unfolded=False,max_contacts=256,include_potential=False,force_ground_mesh=True):
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
        if force_ground_mesh:
            for segment in ground.segments:
                segment.nx=segment.ny=-1
        remaining=max_contacts-sum(len(group) for group in groups)
        groups.extend(_contacts(ground,technology,nx,ny,width,height,length_cell,width_cell,remaining))
        second_count=len(ground.segments)
    contacts=[contact for group in groups for contact in group]
    if not 1<=len(contacts)<=max_contacts:
        raise ValueError(f"Capacitance mesh needs 1–{max_contacts} contacts")
    depths=[0.0]*(len(technology.substrate)+1)
    for i in range(len(technology.substrate)-1,-1,-1):
        depths[i]=float(Real(depths[i+1])+technology.substrate[i]["t"])
    coefficients=layer_coefficients(technology.substrate,frequency_hz)
    records=tuple((m.layer,float(Real(depths[m.layer])-m.height),m.thickness) for m in technology.metals)
    packed={}
    def get_table(low,high):
        pair=low,high
        if pair not in packed:packed[pair]=_tables(*pair,nx,ny,width,height,records,coefficients,tuple(depths))
        return packed[pair]
    full=contact_matrix(contacts,nx,ny,width,height,records,coefficients,depths,get_table)
    if full is None:
        full=[];zero_terms={}
        for a in contacts:
            row=[]
            for b in contacts:
                pair=min(a.metal,b.metal),max(a.metal,b.metal)
                row.append(_contact_potential(a,b,nx,ny,width,height,records,coefficients,depths,get_table(*pair),zero_terms))
            full.append(row)
    admittance=inverse(full)
    total=_sum_complex(z for row in admittance[:len(contacts)-second_count] for z in row[:len(contacts)-second_count])
    impedance=1/total
    total_c=-1/(2*math.pi*frequency_hz*impedance.imag)
    indices=[]
    offset=0
    for group in groups:
        indices.append(list(range(offset,offset+len(group))))
        offset+=len(group)
    reduced=[[_sum_complex(admittance[i][j] for i in rows for j in columns) for columns in indices] for rows in indices]
    if unfolded:
        result=[row[:len(groups)-second_count] for row in reduced[:len(groups)-second_count]]
    else:
        result=[[_sum_complex(reduced[i]) if i==j else -reduced[i][j] for j in range(len(groups))] for i in range(len(groups))]
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

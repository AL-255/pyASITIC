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
import struct
from types import SimpleNamespace
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
from .contact_geometry import groups as _contact_groups

def _tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records,*,include_storage=False):
    # Tuple equality merges +0 and -0. Keep every input store in the cache
    # key, including signed zeros and the original nonfinite coefficient bits.
    return _cached_tables(configuration(source,target,nx,ny,width,height,metal_records,coefficients,depth_records).tobytes(),include_storage)


@lru_cache(maxsize=16)
def _cached_tables(key,include_storage=False):
    config=array('d');config.frombytes(key)
    _,nx,ny,nm,nl,source,target,width,height=config[:9]
    nx,ny,nm,nl,source,target=map(int,(nx,ny,nm,nl,source,target))
    offset=9
    metal_records=tuple((int(config[i]),config[i+1],config[i+2])for i in range(offset,offset+3*nm,3));offset+=3*nm
    coefficients=tuple(complex(config[i],config[i+1])for i in range(offset,offset+2*nl,2));offset+=2*nl
    depth_records=tuple(config[offset:])
    compiled=generate_tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records,include_storage=include_storage)
    if compiled is not None:return compiled
    return _retained_tables(source,target,nx,ny,width,height,metal_records,coefficients,depth_records,include_storage=include_storage)


@dataclass(frozen=True)
class Contact:
    x0:int
    x1:int
    y0:int
    y1:int
    metal:int


def _contacts(shape,technology,nx,ny,width,height,length_step,width_step,max_contacts=256):
    # Byte keys distinguish every binary64 input, including signed zero.
    # Frequency/process coefficients do not participate in contact geometry.
    metal_count=len(technology.metals)
    segments=tuple((s.metal,s.nx,s.ny,struct.pack('=8d',*s.start,*s.end,s.width,s.width if s.primary_width is None else s.primary_width))for s in shape.segments if s.metal<metal_count)
    config=((nx,ny,metal_count,max_contacts),struct.pack('=6d',width,height,length_step,width_step,*shape.origin[:2]),segments)
    return [list(group)for group in _cached_contact_groups(config)]


@lru_cache(maxsize=16)
def _cached_contact_groups(config):
    (nx,ny,metal_count,maximum),raw,segments=config
    width,height,length_step,width_step,ox,oy=struct.unpack('=6d',raw)
    records=[]
    for metal,snx,sny,values in segments:
        values=struct.unpack('=8d',values)
        records.append(SimpleNamespace(start=values[:3],end=values[3:6],width=values[6],primary_width=values[7],metal=metal,nx=snx,ny=sny))
    shape=SimpleNamespace(origin=(ox,oy),segments=records);technology=SimpleNamespace(metals=range(metal_count))
    result=_contact_groups(shape,technology,nx,ny,width,height,length_step,width_step,maximum,Contact)
    # Contacts are frozen; fresh list containers above isolate each caller.
    return tuple(tuple(group)for group in result)


def solve_capacitance(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,
                      fft_x=None,fft_y=None,unfolded=False,max_contacts=256,include_potential=False,force_ground_mesh=True,
                      observe_storage=None):
    """Original contact-potential matrix inversion and folded/unfolded reduction.

    Returned matrix is a complex admittance in siemens. `unfolded` preserves
    native node admittances; the default returns the folded branch convention.
    `observe_storage` receives immutable final buffer values before cleanup,
    for the shared-memory port; no captured value enters the calculation.
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
    def observe(name,matrix):
        if observe_storage is not None:observe_storage(name,tuple(tuple(row)for row in matrix))
    observe('cap.full',admittance)
    total=_sum_complex(z for row in admittance[:len(contacts)-second_count] for z in row[:len(contacts)-second_count])
    if total==0:
        raise ValueError('Original CAP reduction is nonfinite (zero total admittance); review the reference geometry and contact mesh')
    impedance=1/total
    total_c=-1/(2*math.pi*frequency_hz*impedance.imag)
    indices=[]
    offset=0
    for group in groups:
        indices.append(list(range(offset,offset+len(group))))
        offset+=len(group)
    reduced=[[_sum_complex(admittance[i][j] for i in rows for j in columns) for columns in indices] for rows in indices]
    observe('cap.reduced',reduced)
    if unfolded:
        result=[row[:len(groups)-second_count] for row in reduced[:len(groups)-second_count]]
    else:
        result=[[_sum_complex(reduced[i]) if i==j else -reduced[i][j] for j in range(len(groups))] for i in range(len(groups))]
        if shape.name!=ground.name:
            for row in range(len(groups)-1):
                for k in range(1,second_count+1):
                    result[row][row]+=result[row][len(groups)-k]
        observe('cap.folded',result)
        result=[row[:len(groups)-second_count] for row in result[:len(groups)-second_count]]
    observe('cap.output',result)
    data=dict(matrix=[[[z.real,z.imag] for z in row] for row in result],total_capacitance_f=total_c,
              total_resistance_ohm=impedance.real,frequency_hz=frequency_hz,contacts=len(contacts),segments=device_groups,
              fft_x=nx,fft_y=ny,unfolded=unfolded)
    if include_potential:
        data["potential_matrix"]=[[[z.real,z.imag] for z in row] for row in full]
    return data

"""ASITIC filament impedance assembly, reduction and native eddy correction.

Ports geometry.cpp discretization, filaments.cpp, impedance.cpp, vias.cpp and
solver.cpp. LMAT uses the original upper symmetric factor/inverse and retained
parallel kernels. CAP uses the original general LU and inverse path.
"""
import copy
import math
import struct
from decimal import Decimal,localcontext
from functools import lru_cache
from .inductance import segment_mutual, SELF_CONSTANT
from .symmetric import inverse_symmetric
from .linear import inverse_general
from .filament import record as _filament_record,filament_records


@lru_cache(maxsize=32768)
def _filament_mutual(record):
    # Geometry-only kernel. Ordered binary records retain every input bit,
    # including signed zeros; warnings must be replayed on cached calls too.
    values=struct.unpack("=16d",record)
    warnings=[]
    value=segment_mutual(values[:8],values[8:],warnings)
    return value,tuple(warnings)


def _sum_complex(values):
    # Native real/imaginary accumulators spill after every term. Python 3.14's
    # builtin complex sum uses a different accumulation algorithm.
    real=imag=0.0
    for z in values:real+=z.real;imag+=z.imag
    return complex(real,imag)


def _filament_self_impedance(wire,sheet_resistance,thickness_cells,omega_nh):
    """Native retained length/log arithmetic and binary64 L/R stores."""
    with localcontext() as context:
        context.prec=25
        d=Decimal.from_float
        dx,dy,dz=(d(wire[i+3])-d(wire[i]) for i in range(3))
        length=((dx*dx+dy*dy)+dz*dz).sqrt()
        if length<=d(float.fromhex("0x1.b7cdfd9d7bdbbp-34")):return 0j
        width,thickness=d(wire[6]),d(wire[7]);total=width+thickness
        inductance=float((length*d(2e-4))*((((length+length)/total).ln()+d(SELF_CONSTANT))+total/(length*3)))
        resistance=float(((length/width)*d(sheet_resistance))*thickness_cells)
        return complex(resistance,float(d(omega_nh)*d(inductance)))


def inverse(matrix):
    """Invert a dense complex matrix through the native general LU path."""
    return inverse_general(matrix)


def discretize(shape,length_step,half_width):
    """Native longitudinal subdivision; each edge retains its own slope."""
    result = copy.deepcopy(shape)
    result.segments = []
    for source in shape.segments:
        count = math.ceil(source.length/half_width) if min(length_step,half_width)<source.length else 1
        if len(result.segments)+count>2000:
            raise ValueError("Longitudinal mesh exceeds 2000 segments")
        for index in range(count):
            segment = copy.deepcopy(source)
            for start,end in ((segment.start,segment.end),(segment.inner_start,segment.inner_end),(segment.outer_start,segment.outer_end)):
                a,b = start.copy(),end.copy()
                for axis in range(3):
                    start[axis] = a[axis]+(b[axis]-a[axis])*index/count
                    end[axis] = a[axis]+(b[axis]-a[axis])*(index+1)/count
            result.segments.append(segment)
    return result


def filament(segment,origin,yi,zi,ny,nz,edge_cell,max_width_cells,technology):
    return _checked_filament(filament_records([_filament_record(segment,origin,yi,zi,ny,nz,edge_cell,max_width_cells,technology)])[0])


def _checked_filament(row):
    if not all(math.isfinite(v) for v in row[:8]):
        raise ValueError("Native edge mesh has an invalid sqrt(dot) geometry; increase the width cell size")
    return row[:8]


def filament_counts(segment,width_cell,thickness_cell,max_width_cells=9):
    if segment.nx==-1 and segment.ny==-1:return 3,3
    return min(max_width_cells,max(1,int(segment.width/width_cell+.5))),max(1,int(segment.thickness/thickness_cell+.5))


def solve_impedance(shape,technology,frequency_hz,*,length_cell=1000,width_cell=1000,
                    thickness_cell=1000,max_width_cells=9,capacitance_length_cell=None,max_filaments=256,
                    admittance=False,discretized=False,eddy=False,include_diagonal=False):
    """Return the reduced segment impedance matrix, total L/R/Q and mesh size.

    Cells are in micrometres; frequency is in Hz. Returns ohms and henries.
    Includes the reference's via correction. Eddy mode 1 follows native EDDY ON:
    packed square stamping or segment folding for other shape types.
    `admittance=True` returns the branch matrix in siemens instead of ohms;
    scalar L/R/Q still describe total series impedance. `discretized=True`
    accepts the already cloned geometry used by the combined PI2 driver.
    """
    values = (frequency_hz,length_cell,width_cell,thickness_cell)
    if not all(math.isfinite(v) and v>0 for v in values):
        raise ValueError("Frequency and mesh cell sizes must be finite and positive")
    if not isinstance(max_width_cells,int) or not 1<=max_width_cells<=99:
        raise ValueError("Maximum width cells must be an integer from 1 to 99")
    if not isinstance(eddy,(bool,int)) or not 0<=eddy<=255:
        raise ValueError("Eddy mode must be 0 (off), 1 (native on), or an enabled segment-folding mode")
    if capacitance_length_cell is None:
        capacitance_length_cell = length_cell
    if not math.isfinite(capacitance_length_cell) or capacitance_length_cell<=0:
        raise ValueError("Capacitance length cell must be finite and positive")
    # GeometryDiscretization is {half_width, length_step}: the native clone
    # tests the smaller limit, but its ceiling count divides by the inductive
    # length cell (half_width), even when the capacitance cell is different.
    meshed = shape if discretized else discretize(shape,capacitance_length_cell,length_cell)
    metal_count = len(technology.metals)
    conductors = [s for s in meshed.segments if s.metal<metal_count]
    if not conductors:
        raise ValueError("LMAT requires at least one metal segment")
    filament_inputs,metadata,groups = [],[],[]
    for segment in conductors:
        ny,nz=filament_counts(segment,width_cell,thickness_cell,max_width_cells)
        if len(filament_inputs)+ny*nz>max_filaments:
            raise ValueError(f"Mesh exceeds {max_filaments} filaments; increase cell sizes")
        indices = []
        for yi in range(ny):
            for zi in range(nz):
                indices.append(len(filament_inputs))
                filament_inputs.append(_filament_record(segment,shape.origin,yi,zi,ny,nz,width_cell,max_width_cells,technology))
                metadata.append((segment.metal,nz))
        groups.append(indices)
    filaments=[(_checked_filament(row),metal,nz) for row,(metal,nz) in zip(filament_records(filament_inputs),metadata)]
    omega = 2*math.pi*frequency_hz
    omega_nh=omega*1e-9
    n = len(filaments)
    full = [[0j]*n for _ in range(n)]
    warnings = []
    for row,(a,metal,nz) in enumerate(filaments):
        full[row][row]=_filament_self_impedance(a,technology.metals[metal].resistance,nz,omega_nh)
        for col in range(row+1,n):
            mutual,notices = _filament_mutual(struct.pack("=16d",*a,*filaments[col][0]))
            warnings.extend(notices)
            full[row][col] = full[col][row] = complex(0,omega*1e-9*mutual)
    full_y = inverse_symmetric(full)
    reduced_y = [[_sum_complex(full_y[r][c] for r in rows for c in columns)
                  for columns in groups] for rows in groups]
    reduced_z = inverse_symmetric(reduced_y)
    eddy_details=None
    if eddy:
        from .eddy import add_eddy
        eddy_details=add_eddy(reduced_z,meshed,technology,frequency_hz,int(eddy),warnings)
    group = 0
    for s in meshed.segments:
        if s.metal<metal_count:
            group += 1
            continue
        via = technology.vias[s.metal-metal_count]
        height = s.end[2]-s.start[2]
        if height<=1e-10:
            continue
        if group>=len(groups):
            raise ValueError("Native LMAT cannot stamp a trailing via without a following metal segment")
        perimeter = via.width*(s.nx+s.ny)
        inductance = height*2e-4*(math.log(2*height/perimeter)+SELF_CONSTANT+perimeter/(height*3))
        reduced_z[group][group] += complex(via.resistance/(s.nx*s.ny),omega*1e-9*inductance)
    total = _sum_complex(z for row in reduced_z for z in row)
    if eddy and total.real<0:
        warnings.append("The native eddy calculation produced negative total conductor resistance for this geometry/process")
    # PI2 requests admittance directly. The native driver only reinverts the
    # reduced matrix when eddy or via corrections require an impedance stamp.
    if admittance:
        result = inverse_symmetric(reduced_z) if eddy or any(s.metal>=metal_count for s in meshed.segments) else reduced_y
    else:
        result = reduced_z
    data = dict(matrix=[[[z.real,z.imag] for z in row] for row in result],
                resistance_ohm=total.real,inductance_h=total.imag/omega,
                series_q=total.imag/total.real if total.real else None,
                frequency_hz=frequency_hz,filaments=n,segments=len(conductors),
                warnings=list(dict.fromkeys(warnings)),eddy=bool(eddy))
    if eddy_details is not None:
        data["eddy_details"]=eddy_details
    if include_diagonal:
        data["filament_impedance_diagonal"]=[[full[i][i].real,full[i][i].imag] for i in range(n)]
    return data

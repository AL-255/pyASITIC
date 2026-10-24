"""ASITIC filament impedance assembly, reduction and native eddy correction.

Ports geometry.cpp discretization, filaments.cpp, impedance.cpp, vias.cpp and
solver.cpp. LMAT uses the original upper symmetric factor/inverse and retained
parallel kernels. CAP uses the original general LU and inverse path.
"""
import copy
import math
import struct
from functools import lru_cache
from .inductance import segment_mutual
from .symmetric import inverse_symmetric
from .linear import inverse_general
from .filament import record as _filament_record,filament_records
from .mutual_kernel import mesh_mutual,WARNING_MESSAGES
from .vias import stamp as stamp_vias,active_height as active_via_height
from .impedance import assemble as assemble_impedance,self_impedance as _filament_self_impedance
from .mesh_counts import counts as _native_counts,maximum_width_cells
from .retained_scalar import Real
from .reduction import sum_complex as _sum_complex


@lru_cache(maxsize=32768)
def _filament_mutual(record):
    # Geometry-only kernel. Ordered binary records retain every input bit,
    # including signed zeros; warnings must be replayed on cached calls too.
    values=struct.unpack("=16d",record)
    warnings=[]
    value=segment_mutual(values[:8],values[8:],warnings)
    return value,tuple(warnings)


def inverse(matrix):
    """Invert a dense complex matrix through the native general LU path."""
    return inverse_general(matrix)


@lru_cache(maxsize=32)
def _subdivision(record):
    # Frequency sweeps reuse geometry. Cache immutable coordinates, including
    # every input bit, while each returned segment remains a fresh object.
    values=struct.unpack("=20d",record)
    length_step,half_width=values[:2];coordinates=values[2:]
    def length(a,b):
        dx,dy,dz=(Real(b[k])-a[k]for k in range(3))
        return ((dx*dx+dy*dy)+dz*dz).sqrt()
    maximum=float(length(coordinates[:3],coordinates[3:6]))
    if not min(length_step,half_width)<maximum:return None
    count=math.ceil((Real(maximum)/Real(half_width)).value)
    if count>2000:raise ValueError("Longitudinal mesh exceeds 2000 segments")
    rows=[[]for _ in range(count)]
    for offset in (0,6,12):
        a,b=coordinates[offset:offset+3],coordinates[offset+3:offset+6]
        delta=[float(Real(b[k])-a[k])for k in range(3)]
        norm=((Real(delta[0])*delta[0]+Real(delta[1])*delta[1])+Real(delta[2])*delta[2]).sqrt()
        direction=[float(Real(v)/norm)for v in delta]
        edge_length=length(a,b)
        for index,row in enumerate(rows):
            first=(edge_length*Real(index))/Real(count);last=(edge_length*Real(index+1))/Real(count)
            for distance in (first,last):
                row.extend(float(distance*Real(direction[axis])+Real(a[axis])) if axis<2 else float(Real(a[axis])+distance*Real(direction[axis])) for axis in range(3))
    return tuple(tuple(row)for row in rows)


def discretize(shape,length_step,half_width):
    """Native longitudinal subdivision; each edge retains its own slope."""
    result = copy.deepcopy(shape)
    result.segments = []
    for source in shape.segments:
        fields=(source.start,source.end,source.inner_start,source.inner_end,source.outer_start,source.outer_end)
        rows=_subdivision(struct.pack("=20d",length_step,half_width,*(v for field in fields for v in field)))
        if rows is None:
            if len(result.segments)>=2000:raise ValueError("Longitudinal mesh exceeds 2000 segments")
            result.segments.append(copy.deepcopy(source))
            continue
        if len(result.segments)+len(rows)>2000:
            raise ValueError("Longitudinal mesh exceeds 2000 segments")
        for row in rows:
            segment = copy.deepcopy(source)
            for i,field in enumerate((segment.start,segment.end,segment.inner_start,segment.inner_end,segment.outer_start,segment.outer_end)):
                field[:]=row[3*i:3*i+3]
            result.segments.append(segment)
    return result


def filament(segment,origin,yi,zi,ny,nz,edge_cell,max_width_cells,technology):
    return _checked_filament(filament_records([_filament_record(segment,origin,yi,zi,ny,nz,edge_cell,max_width_cells,technology)])[0])


def _checked_filament(row):
    if not all(math.isfinite(v) for v in row[:8]):
        raise ValueError("Native edge mesh has an invalid sqrt(dot) geometry; increase the width cell size")
    return row[:8]


def filament_counts(segment,width_cell,thickness_cell,max_width_cells=500):
    return _native_counts(segment.width,segment.thickness,width_cell,thickness_cell,max_width_cells,segment.nx,segment.ny)


def solve_impedance(shape,technology,frequency_hz,*,length_cell=1000,width_cell=1000,
                    thickness_cell=1000,max_width_cells=500,capacitance_length_cell=None,max_filaments=256,
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
    max_width_cells=maximum_width_cells(max_width_cells)
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
    n = len(filaments)
    warnings = []
    native=mesh_mutual(b"".join(struct.pack("=8d",*wire) for wire,_,_ in filaments));pair=0;pairs=[]
    for row,(a,metal,nz) in enumerate(filaments):
        for col in range(row+1,n):
            if native is not None and native[3*pair]==0:
                mutual=native[3*pair+1];warning=int(native[3*pair+2])
                notices=(WARNING_MESSAGES[warning],) if warning else ()
            else:mutual,notices = _filament_mutual(struct.pack("=16d",*a,*filaments[col][0]))
            pair+=1
            warnings.extend(notices)
            pairs.append(mutual)
    full=assemble_impedance([wire for wire,_,_ in filaments],[(technology.metals[metal].resistance,nz)for _,metal,nz in filaments],pairs,frequency_hz)
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
        if not active_via_height(s.start[2],s.end[2]):
            continue
        if group>=len(groups):
            # The original writes (n,n) outside the reduced matrix. Actual
            # UNJOIN sessions show this aliasing a CAP cell in the native heap.
            # Ignoring the stamp or applying it to the last conductor changes
            # finite original models. Keep the unsupported alias explicit.
            raise ValueError('Native trailing-via stamp aliases memory outside the inductance matrix; this heap interaction is not yet reproduced')
        value=reduced_z[group][group]
        reduced_z[group][group]=stamp_vias([[frequency_hz,s.start[2],s.end[2],via.width,via.resistance,
                                           s.nx,s.ny,value.real,value.imag]])[0]
        if not all(math.isfinite(v) for v in (reduced_z[group][group].real,reduced_z[group][group].imag)):
            raise ValueError("Native via correction produced a nonfinite inductive kernel; review the reference mesh and via cell counts")
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

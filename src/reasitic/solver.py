"""ASITIC filament impedance assembly, reduction and native eddy correction.

Ports geometry.cpp discretization, filaments.cpp, impedance.cpp, vias.cpp and
solver.cpp. LMAT uses the original upper symmetric factor/inverse and retained
parallel kernels. The general inverse helper used by CAP remains binary64
elimination; bitwise equality is not expected.
"""
import copy
import math
from decimal import Decimal,localcontext
from .inductance import segment_mutual, SELF_CONSTANT
from .symmetric import inverse_symmetric


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
    """Invert a dense complex matrix using partial pivoting."""
    n = len(matrix)
    a = [list(row)+[complex(i==j) for j in range(n)] for i,row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col,n),key=lambda row:abs(a[row][col]))
        if abs(a[pivot][col])<1e-30:
            raise ValueError("Singular filament impedance matrix")
        a[col],a[pivot] = a[pivot],a[col]
        scale = a[col][col]
        a[col] = [value/scale for value in a[col]]
        for row in range(n):
            if row==col:
                continue
            factor = a[row][col]
            if factor:
                a[row] = [x-factor*y for x,y in zip(a[row],a[col])]
    return [row[n:] for row in a]


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
    a,b = segment.inner_start.copy(),segment.inner_end.copy()
    c,d = segment.outer_start.copy(),segment.outer_end.copy()
    count = ny
    width = segment.width/ny
    if segment.width/edge_cell>max_width_cells:
        edges = int(.4*ny)
        middle = max_width_cells-2*edges
        if edges<1 or middle<1:
            raise ValueError("Edge mesh requires at least three maximum width cells")
        def blend(start,end):
            # The reference helper is sqrt(dot), not Euclidean distance.
            product = sum(x*y for x,y in zip(start,end))
            if product<=0:
                raise ValueError("Native edge mesh has an invalid sqrt(dot) geometry; increase the width cell size")
            ratio = edges*edge_cell/math.sqrt(product)
            return [(1-ratio)*start[i]+ratio*end[i] for i in range(3)]
        if yi<edges:
            c,d = blend(a,c),blend(b,d)
            width,count = edge_cell,edges
        elif yi>max_width_cells-edges-1:
            a,b = blend(c,a),blend(d,b)
            yi -= edges+middle
            width,count = edge_cell,edges
        else:
            ca,cb,cc,cd = a.copy(),b.copy(),c.copy(),d.copy()
            a,b,c,d = blend(ca,cc),blend(cb,cd),blend(cc,ca),blend(cd,cb)
            yi -= edges
            width,count = (segment.width-2*edge_cell*edges)/edges,middle
    v = (yi+.5)/count
    start = [(1-v)*a[i]+v*c[i]+origin[i] for i in range(2)]
    end = [(1-v)*b[i]+v*d[i]+origin[i] for i in range(2)]
    z = technology.metals[segment.metal].thickness/2+a[2]-(zi+1)/(nz+1)
    return start+[z]+end+[z]+[width,segment.thickness/nz]


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
    filaments,groups = [],[]
    for segment in conductors:
        ny = min(max_width_cells,max(1,int(segment.width/width_cell+.5)))
        nz = max(1,int(segment.thickness/thickness_cell+.5))
        if segment.nx==-1 and segment.ny==-1:
            ny=nz=3
        if len(filaments)+ny*nz>max_filaments:
            raise ValueError(f"Mesh exceeds {max_filaments} filaments; increase cell sizes")
        indices = []
        for yi in range(ny):
            for zi in range(nz):
                indices.append(len(filaments))
                filaments.append((filament(segment,shape.origin,yi,zi,ny,nz,width_cell,max_width_cells,technology),segment.metal,nz))
        groups.append(indices)
    omega = 2*math.pi*frequency_hz
    omega_nh=omega*1e-9
    n = len(filaments)
    full = [[0j]*n for _ in range(n)]
    warnings = []
    for row,(a,metal,nz) in enumerate(filaments):
        full[row][row]=_filament_self_impedance(a,technology.metals[metal].resistance,nz,omega_nh)
        for col in range(row+1,n):
            mutual = segment_mutual(a,filaments[col][0],warnings)
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

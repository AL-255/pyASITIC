"""ASITIC filament impedance assembly and reduction, with eddy currents disabled.

Ports geometry.cpp discretization, filaments.cpp, impedance.cpp, vias.cpp and
solver.cpp. Complex linear systems use pivoted binary64 elimination rather than
the i386 LAPACK symmetric factorization; bitwise equality is not expected.
"""
import copy
import math
from .inductance import segment_mutual, SELF_CONSTANT


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
                    thickness_cell=1000,max_width_cells=9,capacitance_length_cell=None,max_filaments=256):
    """Return the reduced segment impedance matrix, total L/R/Q and mesh size.

    Cells are in micrometres; frequency is in Hz. Returns ohms and henries.
    Includes the reference's via correction. Substrate eddy stamping is separate
    work and is deliberately absent from this explicitly no-eddy API.
    """
    values = (frequency_hz,length_cell,width_cell,thickness_cell)
    if not all(math.isfinite(v) and v>0 for v in values):
        raise ValueError("Frequency and mesh cell sizes must be finite and positive")
    if not isinstance(max_width_cells,int) or not 1<=max_width_cells<=99:
        raise ValueError("Maximum width cells must be an integer from 1 to 99")
    if capacitance_length_cell is None:
        capacitance_length_cell = length_cell
    if not math.isfinite(capacitance_length_cell) or capacitance_length_cell<=0:
        raise ValueError("Capacitance length cell must be finite and positive")
    # GeometryDiscretization is {half_width, length_step}: the native clone
    # tests the smaller limit, but its ceiling count divides by the inductive
    # length cell (half_width), even when the capacitance cell is different.
    meshed = discretize(shape,capacitance_length_cell,length_cell)
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
    n = len(filaments)
    full = [[0j]*n for _ in range(n)]
    warnings = []
    for row,(a,metal,nz) in enumerate(filaments):
        length = math.dist(a[:3],a[3:6])
        if length>1e-10:
            total_width = a[6]+a[7]
            inductance = length*2e-4*(math.log(2*length/total_width)+SELF_CONSTANT+total_width/(3*length))
            resistance = length/a[6]*technology.metals[metal].resistance*nz
            full[row][row] = complex(resistance,omega*1e-9*inductance)
        for col in range(row+1,n):
            mutual = segment_mutual(a,filaments[col][0],warnings)
            full[row][col] = full[col][row] = complex(0,omega*1e-9*mutual)
    admittance = inverse(full)
    reduced_y = [[sum(admittance[r][c] for r in rows for c in columns)
                  for columns in groups] for rows in groups]
    reduced_z = inverse(reduced_y)
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
    total = sum(sum(row) for row in reduced_z)
    return dict(matrix=[[[z.real,z.imag] for z in row] for row in reduced_z],
                resistance_ohm=total.real,inductance_h=total.imag/omega,
                series_q=total.imag/total.real if total.real else None,
                frequency_hz=frequency_hz,filaments=n,segments=len(conductors),
                warnings=list(dict.fromkeys(warnings)),eddy=False)

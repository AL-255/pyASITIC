"""Native PI2 node equations and narrowband two-port metrics.

Ports combined_network.cpp, node_equations.cpp and network.cpp. Matrix solves
use the native general LU path. Public Y matrices follow the native output port
order (y22 first).
"""
from decimal import Decimal,localcontext
from array import array
import copy
import math
from .solver import discretize,solve_impedance,_sum_complex
from .potential import solve_capacitance,_divide
from .linear import factor_general,solve_general,matrix_vector
from .network_metrics import impedance as _metric_impedance,extract as _metric_extract,scattering as _metric_scattering

try:
    from _reasitic_numeric import folded_node as _compiled_node
except ImportError:
    _compiled_node=None


def _complex_matrix(values):
    return [[complex(*z) for z in row] for row in values]


def _pairs(matrix):
    return [[[z.real,z.imag] for z in row] for row in matrix]


def _matvec(matrix,vector):
    return matrix_vector(matrix,vector)


def _factor(matrix):
    return factor_general(matrix)


def _solve(factor,pivots,rhs):
    return solve_general(factor,pivots,rhs)


def solve_node_equations(capacitance,inductance):
    """Folded CAP and branch admittance matrices to native y11/y12/y21/y22."""
    n=len(capacitance)
    if not n or len(inductance)!=n or any(len(row)!=n for row in capacitance+inductance):
        raise ValueError("Pi2 requires matching nonempty square CAP and inductance matrices")
    if _compiled_node is not None and n<=256:
        data=array("d",(v for matrix in (capacitance,inductance) for j in range(n) for i in range(n)
                        for v in (matrix[i][j].real,matrix[i][j].imag)))
        output=array("d",[0.])*(2*n*n+8)
        status=_compiled_node(data,output,n)
        if status:raise ValueError("Singular general LU matrix" if status>0 else "Invalid folded node configuration")
        cap=[[complex(output[2*(j*n+i)],output[2*(j*n+i)+1]) for j in range(n)] for i in range(n)]
        ports={key:complex(output[2*n*n+2*i],output[2*n*n+2*i+1]) for i,key in enumerate(("y11","y12","y21","y22"))}
        return ports,cap
    cap=[[_sum_complex(row) if i==j else -value for j,value in enumerate(row)] for i,row in enumerate(capacitance)]
    difference=[[inductance[i][j]-(inductance[i][j-1] if j else 0j) for j in range(n)] for i in range(n)]
    difference=[[difference[i][j]-(difference[i-1][j] if i else 0j) for j in range(n)] for i in range(n)]
    factor,pivots=_factor([[cap[i][j]+difference[i][j] for j in range(n)] for i in range(n)])
    def run(drive,bias):
        rhs=_matvec(inductance,bias)
        rhs=[rhs[i]-(rhs[i-1] if i else 0j)+drive[i] for i in range(n)]
        rhs=_solve(factor,pivots,rhs)
        first=rhs[0]
        voltage=[rhs[i]-(rhs[i+1] if i+1<n else 0j)-bias[i] for i in range(n)]
        return first,-_matvec(inductance,voltage)[-1]
    a,c=run([1+0j]+[0j]*(n-1),[0j]*n)
    b,d=run([0j]*n,[0j]*(n-1)+[1+0j])
    with localcontext() as context:
        context.prec=25
        ar,ai,dr,di,cr,ci,br,bi=(Decimal.from_float(v) for z in (a,d,c,b) for v in (z.real,z.imag))
        determinant=complex(float((ar*dr-ai*di)-(cr*br-ci*bi)),float((dr*ai+ar*di)-(br*ci+cr*bi)))
    offdiag=_divide(-b,a)
    return dict(y11=_divide(determinant,a),y12=offdiag,y21=offdiag,y22=_divide(1+0j,a)),cap


def two_port_impedance(y,*,differential=False,port=1):
    """Original ZIN, including native diagonal order and reciprocal differential."""
    return _metric_impedance(y,differential,port)


def extract_pi_equivalent(y,frequency_hz):
    """Original retained Pi metrics, with native SI stores and public nulls."""
    return _metric_extract(y,frequency_hz)


def convert_scattering(y):
    """Original 50-ohm conversion, including the historical first diagonal."""
    return _metric_scattering(y)


def solve_pi2(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,thickness_cell=1000,
              capacitance_length_cell=1000,capacitance_width_cell=1000,max_filaments=256,max_contacts=256,include_matrices=False,eddy=False,_force_ground_mesh=True):
    """Original distributed Pi2 combination with substrate capacitance and loss."""
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,length_cell,width_cell,thickness_cell,capacitance_length_cell,capacitance_width_cell)):
        raise ValueError("Pi2 frequency and mesh sizes must be finite and positive")
    meshed=discretize(shape,capacitance_length_cell,length_cell)
    cap=solve_capacitance(meshed,technology,frequency_hz,ground=ground,length_cell=capacitance_length_cell,
                          width_cell=capacitance_width_cell,max_contacts=max_contacts,force_ground_mesh=_force_ground_mesh)
    ind=solve_impedance(meshed,technology,frequency_hz,width_cell=width_cell,thickness_cell=thickness_cell,
                        max_filaments=max_filaments,admittance=True,discretized=True,eddy=eddy)
    y,nodal=solve_node_equations(_complex_matrix(cap["matrix"]),_complex_matrix(ind["matrix"]))
    z1,z2,zd=(two_port_impedance(y,port=1),two_port_impedance(y,port=2),two_port_impedance(y,differential=True))
    data=dict(frequency_hz=frequency_hz,method="ASITIC PI2, native eddy on" if eddy else "ASITIC PI2, eddy off",eddy=bool(eddy),
              admittance_matrix=_pairs([[y["y22"],y["y21"]],[y["y12"],y["y11"]]]),
              scattering_matrix=_pairs(convert_scattering(y)),reference_impedance_ohm=50,
              pi=extract_pi_equivalent(y,frequency_hz),input_impedance_first_ohm=[z1.real,z1.imag],
              input_impedance_second_ohm=[z2.real,z2.imag],differential_impedance_ohm=[zd.real,zd.imag],
              contacts=cap["contacts"],filaments=ind["filaments"],segments=ind["segments"],warnings=ind["warnings"])
    if include_matrices:
        data.update(capacitance_matrix=cap["matrix"],inductive_admittance_matrix=ind["matrix"],nodal_capacitance_matrix=_pairs(nodal))
    if "eddy_details" in ind:
        data["eddy_details"]=ind["eddy_details"]
    return data


def solve_pi3(shape,technology,frequency_hz,*,ground,**mesh):
    """PI3 uses the combined solver and a type-0 reference, without type-8 marking."""
    if ground is None:
        raise ValueError("Pi3 requires an explicit ground shape")
    result=solve_pi2(shape,technology,frequency_hz,ground=ground,_force_ground_mesh=False,**mesh)
    result["method"]="ASITIC PI3, native eddy on" if result["eddy"] else "ASITIC PI3, eddy off"
    return result


def _join_for_pads(target,source):
    """Native copied segment concatenation, including wire/spiral origin history."""
    result=copy.deepcopy(target)
    other=copy.deepcopy(source)
    with localcontext() as context:
        context.prec=25
        for segment in other.segments:
            for point in segment.points:
                for axis in range(2):
                    delta=Decimal.from_float(float(source.origin[axis]))-Decimal.from_float(float(target.origin[axis]))
                    point[axis]=float(delta+Decimal.from_float(float(point[axis])))
    result.segments.extend(other.segments)
    if target.kind=="wire" and source.kind in ("square","polygon"):
        result.origin=source.origin.copy()
        result.parameters=copy.deepcopy(source.parameters)
    result.kind="joined"
    return result


def solve_pi4(shape,technology,frequency_hz,*,first_pad,second_pad,ground=None,**mesh):
    """Native PI4: device plus pads, then subtract folded pad capacitance."""
    length_cell=mesh.get("length_cell",1000)
    capacitance_length_cell=mesh.get("capacitance_length_cell",1000)
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,length_cell,capacitance_length_cell)):
        raise ValueError("Pi4 frequency and mesh sizes must be finite and positive")
    reference=shape if ground is None else ground
    pads=[copy.deepcopy(first_pad),copy.deepcopy(second_pad)]
    # Native command arguments of parser type 8 mark pad mesh counts -1/-1.
    for pad in pads:
        for segment in pad.segments:
            segment.nx=segment.ny=-1
    winding=discretize(shape,capacitance_length_cell,length_cell)
    with_pads=_join_for_pads(_join_for_pads(pads[0],winding),pads[1])
    with_pads.name=first_pad.name+"_"
    pad_shape=_join_for_pads(pads[0],pads[1])
    pad_shape.name=first_pad.name+"_pads"
    result=solve_pi2(with_pads,technology,frequency_hz,ground=reference,**mesh)
    pad_cap=solve_capacitance(pad_shape,technology,frequency_hz,ground=reference,
                              length_cell=capacitance_length_cell,width_cell=mesh.get("capacitance_width_cell",1000))
    cap=_complex_matrix(pad_cap["matrix"])
    if len(cap)<2:
        raise ValueError("Pi4 needs at least two pad conductor groups")
    saved=_complex_matrix(result["admittance_matrix"])
    first,second,cross=cap[0][0]+cap[1][0],cap[1][1]+cap[1][0],-cap[1][0]
    y=dict(y22=saved[0][0]-first,y11=saved[1][1]-second,y21=saved[0][1]-cross,y12=saved[1][0]-cross)
    z1,z2,zd=two_port_impedance(y,port=1),two_port_impedance(y,port=2),two_port_impedance(y,differential=True)
    result.update(method="ASITIC PI4, native eddy on" if result["eddy"] else "ASITIC PI4, eddy off",admittance_matrix=_pairs([[y["y22"],y["y21"]],[y["y12"],y["y11"]]]),
                  scattering_matrix=_pairs(convert_scattering(y)),pi=extract_pi_equivalent(y,frequency_hz),
                  input_impedance_first_ohm=[z1.real,z1.imag],input_impedance_second_ohm=[z2.real,z2.imag],
                  differential_impedance_ohm=[zd.real,zd.imag],pad_admittance_matrix=pad_cap["matrix"],pad_contacts=pad_cap["contacts"])
    return result

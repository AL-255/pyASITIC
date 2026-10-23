"""Native PI2 node equations and narrowband two-port metrics.

Ports combined_network.cpp, node_equations.cpp and network.cpp. Matrix solves
use the native general LU path. Public Y matrices follow the native output port
order (y22 first).
"""
from decimal import Decimal,localcontext
import copy
import math
from .solver import discretize,solve_impedance,_sum_complex
from .potential import solve_capacitance,_divide
from .linear import factor_general,solve_general,matrix_vector


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


def _ratio(a,b):
    if b:
        return a/b
    return math.nan if not a else math.copysign(math.inf,a)


def two_port_impedance(y,*,differential=False,port=1):
    """Native ZIN: single-ended port 1 uses 1/y22; differential assumes reciprocity."""
    if not differential:
        return _divide(1+0j,y["y22" if port==1 else "y11"])
    with localcontext() as context:
        context.prec=25
        ar,ai,br,bi,cr,ci=(Decimal.from_float(v) for z in (y["y22"],y["y11"],y["y21"]) for v in (z.real,z.imag))
        determinant=complex(float((ar*br-ai*bi)-Decimal.from_float(float(cr*cr-ci*ci))),float((ar*bi+ai*br)-(cr*ci+cr*ci)))
        numerator=complex(float((ar+br)+(cr+cr)),float((ai+bi)+(ci+ci)))
    return _divide(numerator,determinant)


def extract_pi_equivalent(y,frequency_hz):
    """Native series L/R, two series RC shunts, Q, shunt R and resonance."""
    first,second=y["y11"]+y["y12"],y["y21"]+y["y22"]
    series=-y["y21"]
    omega=2*math.pi*frequency_hz
    z=_divide(1+0j,series)
    inductance,resistance=z.imag/omega,z.real
    def shunt(value):
        if abs(value)<=float.fromhex("0x1.b7cdfd9d7bdbbp-34"):
            return 0.0,1e15
        impedance=_divide(1+0j,value)
        return _ratio(-1,omega*impedance.imag),impedance.real
    c1,r1=shunt(second)
    c2,r2=shunt(first)
    zd=two_port_impedance(y,differential=True)
    def shunt_resistance(differential):
        capacitance=_ratio(c1*c2,c1+c2) if differential else c1
        ground_resistance=r1+r2 if differential else r1
        a=_ratio(omega*inductance,resistance)**2
        b=_ratio(1,omega*capacitance*ground_resistance)**2
        series_r=(a+1)*resistance
        shunt_r=(1+b)*ground_resistance
        return _ratio(series_r*shunt_r,series_r+shunt_r)
    ratio=_ratio(c1,inductance)
    correction=_ratio(1-resistance*resistance*ratio,1-r1*r1*ratio)
    resonance=_ratio(1,inductance*c1)
    if correction>0:
        resonance*=correction
    resonance=math.sqrt(resonance)/(2*math.pi) if resonance>=0 else math.nan
    values=dict(inductance_h=inductance,resistance_ohm=resistance,capacitance_first_f=c1,capacitance_second_f=c2,
                resistance_first_ohm=r1,resistance_second_ohm=r2,
                q_first=_ratio(-(second.imag+series.imag),second.real+series.real),
                q_second=_ratio(-(series.imag+first.imag),series.real+first.real),q_differential=_ratio(zd.imag,zd.real),
                shunt_single_ohm=shunt_resistance(False),shunt_differential_ohm=shunt_resistance(True),
                resonant_frequency_hz=resonance)
    return {key:value if math.isfinite(value) else None for key,value in values.items()}


def convert_scattering(y):
    """Native 50-ohm S conversion, including its repeated y22 factor in s11."""
    with localcontext() as context:
        context.prec=25
        def pair(value):
            return Decimal.from_float(value.real),Decimal.from_float(value.imag)
        def multiply(a,b):
            ar,ai=a;br,bi=b
            return ar*br-ai*bi,ar*bi+ai*br
        def add(a,b):
            return a[0]+b[0],a[1]+b[1]
        def spill(a):
            return complex(float(a[0]),float(a[1]))
        reference=Decimal.from_float(.02)
        a,b,c,d=map(pair,(y["y11"],y["y12"],y["y21"],y["y22"]))
        positive_a,negative_a=(a[0]+reference,a[1]),(reference-a[0],-a[1])
        positive_d,negative_d=(d[0]+reference,d[1]),(reference-d[0],-d[1])
        cross=multiply(c,b)
        base=multiply(positive_d,positive_a)
        denominator=spill((base[0]-cross[0],base[1]-cross[1]))
        s11=_divide(spill(add(multiply(negative_d,positive_d),cross)),denominator)
        s22=_divide(spill(add(multiply(positive_d,negative_a),cross)),denominator)
        s21=_divide(spill((-2*c[0]*reference,-2*c[1]*reference)),denominator)
        s12=_divide(spill((-2*b[0]*reference,-2*b[1]*reference)),denominator)
    return [[s11,s12],[s21,s22]]


def solve_pi2(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,thickness_cell=1000,
              capacitance_length_cell=1000,capacitance_width_cell=1000,max_filaments=256,max_contacts=256,include_matrices=False,eddy=False):
    """Original distributed Pi2 combination with substrate capacitance and loss."""
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,length_cell,width_cell,thickness_cell,capacitance_length_cell,capacitance_width_cell)):
        raise ValueError("Pi2 frequency and mesh sizes must be finite and positive")
    meshed=discretize(shape,capacitance_length_cell,length_cell)
    cap=solve_capacitance(meshed,technology,frequency_hz,ground=ground,length_cell=capacitance_length_cell,
                          width_cell=capacitance_width_cell,max_contacts=max_contacts)
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
    """Native PI3 dispatch uses the same combined solver with explicit ground."""
    if ground is None:
        raise ValueError("Pi3 requires an explicit ground shape")
    result=solve_pi2(shape,technology,frequency_hz,ground=ground,**mesh)
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

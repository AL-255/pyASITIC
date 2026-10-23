"""Native PiX unfolded-capacitance / impedance node equations.

Ports extended_node.cpp and extended_twoport.cpp. General dense solves retain
the native LU panels, pivot ranking and triangular update order.
"""
from fractions import Fraction
import math
from .inductance import _round_extended
from .solver import discretize,solve_impedance
from .potential import solve_capacitance
from .network import _pairs,_complex_matrix,extract_pi_equivalent,convert_scattering,two_port_impedance
from .linear import factor_general,solve_general


def stamp_extended_node_columns(matrix):
    """Native negative half-sum of adjacent columns, including both ends."""
    n=len(matrix)
    if not n or any(len(row)!=n for row in matrix):
        raise ValueError("Extended node stamping requires a nonempty square matrix")
    if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for row in matrix for z in row):
        raise ValueError("Extended node matrix values must be finite")
    def half(a,b=None):
        if b is None:return complex(-.5*a.real,-.5*a.imag)
        real=_round_extended(Fraction(a.real)+Fraction(b.real))
        imag=_round_extended(Fraction(a.imag)+Fraction(b.imag))
        # Exact cancellation creates +0 before the negative half; adding two
        # negative zeros instead creates -0. Keep those native IEEE signs.
        re=float(-real/2) if real else -.5*(a.real+b.real)
        im=float(-imag/2) if imag else -.5*(a.imag+b.imag)
        return complex(re,im)
    return [[half(row[0])]+[half(row[j-1],row[j]) for j in range(1,n)]+[half(row[-1])] for row in matrix]


def solve_extended_node_equations(capacitance,impedance):
    """Unfolded C admittance + branch Z to all four native port admittances.

    Also returns the unfactored system and both voltage/current solutions for
    reference snapshots. First solution drives public port 1, second port 2.
    """
    n=len(capacitance)
    if len(impedance)!=n:
        raise ValueError("Extended CAP and impedance dimensions must match")
    a,b=stamp_extended_node_columns(capacitance),stamp_extended_node_columns(impedance)
    width=n+1;size=2*width
    system=[[0j]*size for _ in range(size)]
    for i in range(n):
        system[i][:width]=a[i];system[i+n][width:]=b[i]
        system[i][width+i]=system[i+n][i]=1+0j
        system[i][width+i+1]=system[i+n][i+1]=-1+0j
    system[2*n][0]=system[2*n+1][n]=1+0j
    try:
        factor,pivots=factor_general(system)
        solutions=[]
        for drive in (2*n,2*n+1):
            rhs=[0j]*size;rhs[drive]=1+0j
            solutions.append(solve_general(factor,pivots,rhs))
    except ValueError as error:
        raise ValueError("Singular extended two-port node equations") from error
    first,second=solutions
    y=dict(y22=first[width],y12=-first[-1],y21=second[width],y11=-second[-1])
    return y,dict(system=system,solutions=solutions)


def solve_pix(shape,technology,frequency_hz,*,ground=None,length_cell=1000,width_cell=1000,thickness_cell=1000,
              capacitance_length_cell=1000,capacitance_width_cell=1000,max_filaments=256,max_contacts=256,
              include_matrices=False,eddy=False):
    """Native PIX command: unfolded CAP, impedance LMAT and extended nodes.

    The optional native reference defaults to the original device itself.
    Unlike the 2PORTX wrapper, PIX calls this backend for every structure type.
    """
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,length_cell,width_cell,thickness_cell,capacitance_length_cell,capacitance_width_cell)):
        raise ValueError("PiX frequency and mesh sizes must be finite and positive")
    reference=shape if ground is None else ground
    meshed=discretize(shape,capacitance_length_cell,length_cell)
    cap=solve_capacitance(meshed,technology,frequency_hz,ground=reference,length_cell=capacitance_length_cell,
                          width_cell=capacitance_width_cell,max_contacts=max_contacts,unfolded=True)
    ind=solve_impedance(meshed,technology,frequency_hz,width_cell=width_cell,thickness_cell=thickness_cell,
                        max_filaments=max_filaments,discretized=True,eddy=eddy,include_diagonal=include_matrices)
    y,state=solve_extended_node_equations(_complex_matrix(cap["matrix"]),_complex_matrix(ind["matrix"]))
    z1,z2,zd=two_port_impedance(y),two_port_impedance(y,port=2),two_port_impedance(y,differential=True)
    result=dict(method="ASITIC PIX, native eddy on" if eddy else "ASITIC PIX, eddy off",frequency_hz=frequency_hz,eddy=bool(eddy),
                admittance_matrix=_pairs([[y["y22"],y["y21"]],[y["y12"],y["y11"]]]),
                scattering_matrix=_pairs(convert_scattering(y)),reference_impedance_ohm=50,
                pi=extract_pi_equivalent(y,frequency_hz),input_impedance_first_ohm=[z1.real,z1.imag],
                input_impedance_second_ohm=[z2.real,z2.imag],differential_impedance_ohm=[zd.real,zd.imag],
                contacts=cap["contacts"],filaments=ind["filaments"],segments=ind["segments"],warnings=ind["warnings"])
    if "eddy_details" in ind:result["eddy_details"]=ind["eddy_details"]
    if include_matrices:
        result.update(capacitance_matrix=cap["matrix"],inductive_impedance_matrix=ind["matrix"],
                      filament_impedance_diagonal=ind["filament_impedance_diagonal"],
                      node_system=_pairs(state["system"]),voltages_first=_pairs([[z] for z in state["solutions"][0][:len(cap["matrix"])+1]]),
                      currents_first=_pairs([[z] for z in state["solutions"][0][len(cap["matrix"])+1:]]))
    return result

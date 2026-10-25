"""Native CALCTRANS coupled-winding construction and narrowband extraction.

Ports later_analysis.cpp. The original port labels and sign of mutual
inductance are retained; they differ from a conventional two-port inverse.
"""
import math
import copy
from array import array
from decimal import Decimal
from .green import _guard,_Retained,legacy_divide,TWO_PI
from .network import _join_for_pads,_complex_matrix,_pairs,solve_node_equations,convert_scattering
from .solver import discretize,solve_impedance
from .potential import solve_capacitance

try:
    from _reasitic_numeric import transformer_model as _compiled_transformer
except ImportError:
    _compiled_transformer=None

MODEL_KEYS=("first_inductance_h","second_inductance_h","first_resistance_ohm","second_resistance_ohm","ground_resistance_ohm","mutual_h","coupling")


def _compiled(y,frequency,operation):
    data=array("d",[frequency,*[v for key in ("y11","y12","y21","y22") for v in (y[key].real,y[key].imag)],*([0.]*15)])
    if _compiled_transformer(data,operation):raise ValueError("Invalid transformer extraction operation")
    z={key:complex(data[9+2*i],data[10+2*i]) for i,key in enumerate(("z11","z12","z21","z22"))}
    return dict(zip(MODEL_KEYS,data[17:])),z


def _store(value):
    try:return float(value)
    except OverflowError:return -math.inf if value.value<0 else math.inf


@_guard
def invert_transformer_admittance(y):
    """Native reciprocal Y→Z conversion, ignoring y12 and retaining labels."""
    if _compiled_transformer is not None:return _compiled(y,0.,0)[1]
    values=[v for key in ("y11","y22","y21") for v in (y[key].real,y[key].imag)]
    constructor=_Retained if all(math.isfinite(v) for v in values) else Decimal.from_float
    ar,ai,br,bi,cr,ci=map(constructor,values)
    real=(br*ar-bi*ai)-(cr*cr-ci*ci)
    imag=(ar*bi+br*ai)-(cr*ci+cr*ci)
    determinant=complex(_store(real),_store(imag))
    cross=legacy_divide(-y["y21"],determinant)
    return dict(z11=legacy_divide(y["y11"],determinant),z22=legacy_divide(y["y22"],determinant),z12=cross,z21=cross)


@_guard
def extract_transformer_equivalent(y,frequency_hz):
    """Return native SI model values and the updated native Z scratch record."""
    if _compiled_transformer is not None:return _compiled(y,frequency_hz,1)
    z=invert_transformer_admittance(y)
    d=Decimal.from_float
    omega=d(frequency_hz)*d(TWO_PI)
    l1,l2,m=d(z["z11"].imag)/omega,d(z["z22"].imag)/omega,-d(z["z12"].imag)/omega
    r1,r2=d(z["z11"].real)-d(z["z12"].real),d(z["z22"].real)-d(z["z12"].real)
    coupling=m/(l1*l2).sqrt()
    return dict(first_inductance_h=float(l1),second_inductance_h=float(l2),first_resistance_ohm=float(r1),
                second_resistance_ohm=float(r2),ground_resistance_ohm=z["z12"].real,mutual_h=float(m),coupling=float(coupling)),z


@_guard
def solve_transformer(first,second,technology,frequency_hz,*,ground=None,termination_ohm=0,
                      length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,
                      capacitance_width_cell=1000,max_filaments=256,max_contacts=256,max_width_cells=500,include_matrices=False,eddy=False):
    """Original CALCTRANS including junction termination and both winding meshes.

    A missing reference, or one with the first winding's name, selects the
    joined device as native self-reference. Terminations below 1e-10 ohm use
    native 1e15 S. Secondary segment order is reversed without flipping edges.
    """
    if not all(math.isfinite(v) and v>0 for v in (frequency_hz,length_cell,width_cell,thickness_cell,capacitance_length_cell,capacitance_width_cell)):
        raise ValueError("CALCTRANS frequency and mesh sizes must be finite and positive")
    if not math.isfinite(termination_ohm):raise ValueError("CALCTRANS termination must be finite")
    working=copy.deepcopy((first,second))
    if ground is not None:
        # An explicit parser type-8 reference marks the named winding before
        # CALCTRANS copies/discretizes it. Omission leaves both originals intact.
        for winding in working:
            if winding.name==ground.name:
                for segment in winding.segments:segment.nx=segment.ny=-1
    a,b=(discretize(shape,capacitance_length_cell,length_cell) for shape in working)
    boundary=sum(s.metal<len(technology.metals) for s in a.segments)
    second_count=sum(s.metal<len(technology.metals) for s in b.segments)
    if not boundary or not second_count:raise ValueError("CALCTRANS requires metal conductors in both windings")
    from .model import copy_geometry
    a,b=copy_geometry(a),copy_geometry(b)
    b.reverse_segments()
    joined=_join_for_pads(a,b);joined.name=first.name+"_"
    reference=joined if ground is None or ground.name==first.name else ground
    cap=solve_capacitance(joined,technology,frequency_hz,ground=reference,length_cell=capacitance_length_cell,
                          width_cell=capacitance_width_cell,max_contacts=max_contacts)
    capacitance=_complex_matrix(cap["matrix"])
    cell=capacitance[boundary][boundary]
    conductance=Decimal(10)**15 if termination_ohm<float.fromhex("0x1.b7cdfd9d7bdbbp-34") else Decimal(1)/Decimal.from_float(termination_ohm)
    capacitance[boundary][boundary]=complex(float(conductance+Decimal.from_float(cell.real)),cell.imag+0.0)
    try:
        ind=solve_impedance(joined,technology,frequency_hz,width_cell=width_cell,thickness_cell=thickness_cell,
                            max_filaments=max_filaments,max_width_cells=max_width_cells,admittance=True,discretized=True,eddy=eddy)
    except ValueError as error:
        if "expected a positive input" in str(error) or str(error)=="math domain error":
            raise ValueError("CALCTRANS has a nonfinite inductive kernel for this reference mesh; omit the explicit first-winding reference or use a ground strip") from error
        raise
    y,nodal=solve_node_equations(capacitance,_complex_matrix(ind["matrix"]))
    model,z=extract_transformer_equivalent(y,frequency_hz)
    model={key:value if math.isfinite(value) else None for key,value in model.items()}
    warnings=list(dict.fromkeys(first.warnings+second.warnings+ind["warnings"]))
    if model["coupling"] is None:warnings.append("Native CALCTRANS coupling is nonfinite for this frequency and termination.")
    data=dict(frequency_hz=frequency_hz,method="ASITIC CALCTRANS, native eddy on" if eddy else "ASITIC CALCTRANS, eddy off",
              first_winding=first.name,second_winding=second.name,eddy=bool(eddy),termination_ohm=termination_ohm,
              model=model,admittance_matrix=_pairs([[y["y22"],y["y21"]],[y["y12"],y["y11"]]]),
              impedance_matrix=_pairs([[z["z11"],z["z12"]],[z["z21"],z["z22"]]]),
              scattering_matrix=_pairs(convert_scattering(y)),reference_impedance_ohm=50,
              winding_segments=[boundary,second_count],contacts=cap["contacts"],filaments=ind["filaments"],segments=ind["segments"],warnings=warnings)
    if include_matrices:data.update(capacitance_matrix=_pairs(capacitance),nodal_capacitance_matrix=_pairs(nodal),inductive_admittance_matrix=ind["matrix"])
    if "eddy_details" in ind:data["eddy_details"]=ind["eddy_details"]
    return data

"""JSON interface shared by browser worker and CLI; no browser dependencies."""
import base64
import json
import math
from .geometry import build, KINDS
from .technology import Technology
from .resistance import resistance_dc, resistance_hf
from .inductance import inductance_estimate, coupling_estimate
from .gds import write_gds, layout_polygons
from .solver import solve_impedance
from .devices import build_device, PAIRED_KINDS
from .potential import solve_capacitance
from .network import solve_pi2,solve_pi3,solve_pi4
from .resonance import solve_self_resonance


def _technology(request):
    return Technology.from_text(request["technology"]) if request.get("technology") else Technology.default()


def _shape(request,tech):
    shapes = _shapes(request,tech)
    index = int(request.get("winding",0))
    if not 0<=index<len(shapes):
        raise ValueError("Invalid winding selection")
    return shapes[index]


def _shapes(request,tech):
    return build_device(request.get("kind","square"),technology=tech,**request.get("parameters",{}))


def handle(request,*,progress=None):
    """Execute one typed request; user input is never evaluated as Python."""
    tech = _technology(request)
    action = request.get("action","build")
    if action == "init":
        return dict(technology=tech.to_dict(),generators=list(KINDS)+list(PAIRED_KINDS))
    if action == "gds":
        definitions = request.get("shapes") or [request]
        shapes = [shape for definition in definitions for shape in _shapes(definition,tech)]
        return dict(base64=base64.b64encode(write_gds(shapes,tech,request.get("layer_map"))).decode())
    if action == "coupling":
        a,b = (_shape(request[key],tech) for key in ("first","second"))
        mutual,k = coupling_estimate(a,b,tech)
        return dict(mutual_nh=mutual,k=k)
    shape = _shape(request,tech)
    if action=="selfres":
        mesh=request.get("mesh",{})
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        return solve_self_resonance(shape,tech,float(request["first_hz"]),float(request["last_hz"]),float(request["step_hz"]),
            ground=ground,differential=bool(request.get("differential",False)),fast=bool(request.get("fast",False)),eddy=request.get("eddy",False),
            observer=(lambda point:progress(json.dumps(point,allow_nan=False))) if progress is not None else None,
            **{key:float(mesh.get(key,1000)) for key in ("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")})
    if action in ("pi","pi2","pi3","pi4"):
        if action=="pi":
            raise ValueError("The native fast Pi command faults on conductor coils before producing a model. Pi2, Pi3 and Pi4 use the working distributed solver.")
        mesh=request.get("mesh",{})
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        pads={"first_pad":_shape(request["first_pad"],tech),"second_pad":_shape(request["second_pad"],tech)} if action=="pi4" else {}
        solver={"pi2":solve_pi2,"pi3":solve_pi3,"pi4":solve_pi4}[action]
        return solver(shape,tech,float(request.get("frequency_hz",1e9)),ground=ground,eddy=request.get("eddy",False),**pads,
                         **{key:float(mesh.get(key,1000)) for key in ("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")})
    if action == "capacitance":
        mesh=request.get("mesh",{})
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        return solve_capacitance(shape,tech,float(request.get("frequency_hz",1e9)),ground=ground,
                                 length_cell=float(mesh.get("length_cell",1000)),width_cell=float(mesh.get("width_cell",1000)))
    if action == "lmat":
        mesh = request.get("mesh",{})
        return solve_impedance(shape,tech,float(request.get("frequency_hz",1e9)),
                               eddy=request.get("eddy",False),
                               length_cell=float(mesh.get("length_cell",1000)),
                               width_cell=float(mesh.get("width_cell",1000)),
                               thickness_cell=float(mesh.get("thickness_cell",1000)),
                               capacitance_length_cell=float(mesh["capacitance_length_cell"]) if "capacitance_length_cell" in mesh else None)
    if action == "build":
        data = shape.to_dict()
        windings = _shapes(request,tech)
        data["windings"] = [w.name for w in windings]
        # Render exactly the polygons exported to GDS, including individual cuts.
        if sum(s.nx*s.ny for w in windings for s in w.segments) > 100000:
            raise ValueError("Preview supports at most 100,000 via cuts")
        data["polygons"] = [dict(metal=metal,points=[[point[0]+w.origin[0]-shape.origin[0],point[1]+w.origin[1]-shape.origin[1]] for point in points])
                            for w in windings for metal,points in layout_polygons(w,tech)]
        data["dc_ohm"] = resistance_dc(shape,tech)
        return data
    if action == "simulate":
        frequency = float(request.get("frequency_hz",1e9))
        inductance = inductance_estimate(shape,tech)
        dc = resistance_dc(shape,tech)
        hf = resistance_hf(shape,tech,frequency)
        qlf = 2*math.pi*frequency*inductance*1e-9/dc if dc>0 else None
        return dict(inductance_nh=inductance,dc_ohm=dc,hf_ohm=hf,qlf=qlf,
                    frequency_hz=frequency,method="ASITIC INDUCTANCE / RESIS / RESISHF / QLF estimates",
                    warnings=list(dict.fromkeys(shape.warnings)))
    if action == "sweep":
        first,last = float(request["first_hz"]),float(request["last_hz"])
        count = int(request.get("count",31))
        if not all(math.isfinite(v) for v in (first,last)) or not 0<first<last or not 2<=count<=201:
            raise ValueError("Sweep needs 0 < start < stop and 2–201 points")
        inductance,dc = inductance_estimate(shape,tech),resistance_dc(shape,tech)
        rows = []
        for i in range(count):
            f = first*(last/first)**(i/(count-1))
            hf = resistance_hf(shape,tech,f)
            rows.append(dict(frequency_hz=f,inductance_nh=inductance,dc_ohm=dc,hf_ohm=hf,
                             qlf=2*math.pi*f*inductance*1e-9/dc if dc>0 else None))
        return dict(rows=rows)
    raise ValueError(f"Unknown action: {action}")


def request_json(payload,progress=None):
    try:
        return json.dumps(dict(result=handle(json.loads(payload),progress=progress)),allow_nan=False)
    except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as error:
        return json.dumps(dict(error=str(error)))

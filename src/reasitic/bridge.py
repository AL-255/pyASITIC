"""JSON interface shared by browser worker and CLI; no browser dependencies."""
import base64
import json
import math
from .geometry import build, KINDS
from .technology import Technology
from .resistance import resistance_dc, resistance_hf
from .inductance import inductance_estimate, coupling_estimate
from .gds import write_gds, layout_polygons


def _technology(request):
    return Technology.from_text(request["technology"]) if request.get("technology") else Technology.default()


def _shape(request,tech):
    return build(request.get("kind","square"),technology=tech,**request.get("parameters",{}))


def handle(request):
    """Execute one typed request; user input is never evaluated as Python."""
    tech = _technology(request)
    action = request.get("action","build")
    if action == "init":
        return dict(technology=tech.to_dict(),generators=list(KINDS))
    if action == "gds":
        definitions = request.get("shapes") or [request]
        shapes = [_shape(definition,tech) for definition in definitions]
        return dict(base64=base64.b64encode(write_gds(shapes,tech,request.get("layer_map"))).decode())
    if action == "coupling":
        a,b = (_shape(request[key],tech) for key in ("first","second"))
        mutual,k = coupling_estimate(a,b,tech)
        return dict(mutual_nh=mutual,k=k)
    shape = _shape(request,tech)
    if action == "build":
        data = shape.to_dict()
        # Render exactly the polygons exported to GDS, including individual cuts.
        if sum(s.nx*s.ny for s in shape.segments) > 100000:
            raise ValueError("Preview supports at most 100,000 via cuts")
        data["polygons"] = [dict(metal=metal,points=points) for metal,points in layout_polygons(shape,tech)]
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


def request_json(payload):
    try:
        return json.dumps(dict(result=handle(json.loads(payload))),allow_nan=False)
    except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as error:
        return json.dumps(dict(error=str(error)))

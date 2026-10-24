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
from .devices import build_device, PAIRED_KINDS, PAIRED_ALIASES
from .potential import solve_capacitance
from .network import solve_pi2,solve_pi3,solve_pi4
from .resonance import solve_self_resonance
from .extended import solve_pix
from .transformer import solve_transformer
from .mesh import mesh_information,MESH_KEYS
from .mesh_counts import maximum_width_cells
from .retained_scalar import Real
from .presets import list_presets,load_preset,identify
from .command_numbers import frequency_ghz,mesh_cell_um
from .conductor_metrics import retained_estimates,qlf as extrapolated_q
from .editing import apply_edits


def _frequency(request,prefix='frequency',default=1e9):
    ghz=prefix+'_ghz'
    if ghz in request:return frequency_ghz(request[ghz])
    hz=prefix+'_hz'
    return float(request.get(hz,default))if prefix=='frequency'else float(request[hz])


def _mesh(request,technology):
    """Positive fields as default CELL/CCELL commands; typed SI stays separate."""
    mesh=dict(request.get('mesh',{}))
    if request.get('native_mesh',False):
        for key in MESH_KEYS:
            if key in mesh:mesh[key]=mesh_cell_um(mesh[key])
        # CCELL raises both contact cells to the larger native FFT pitch.
        x=Real(technology.chip.get('chipx',1000))/Real(int(technology.chip.get('fftx',128)))
        y=Real(technology.chip.get('chipy',1000))/Real(int(technology.chip.get('ffty',128)))
        cap_keys=('length_cell','width_cell')if request.get('action')=='capacitance'else('capacitance_length_cell','capacitance_width_cell')
        for key in cap_keys:
            if key in mesh and(Real(mesh[key])<x or Real(mesh[key])<y):mesh[key]=float(x if y<x else y)
    return mesh


def _technology(request):
    return Technology.from_text(request["technology"]) if request.get("technology") else Technology.default()


def _shape(request,tech,*,shapes=None,reset_missing=False):
    if shapes is None:shapes = _shapes(request,tech)
    index = int(request.get("winding",0))
    if not 0<=index<len(shapes):
        if reset_missing:index=0
        else:raise ValueError("Invalid winding selection")
    return shapes[index]


def _shapes(request,tech,*,with_links=False):
    kind=request.get('kind','square').lower();kind=PAIRED_ALIASES.get(kind,kind);parameters=dict(request.get('parameters',{}))
    if request.get('native_keyword',False):
        if kind=='transformer3d':raise ValueError('The original 3D transformer command is interactive and accepts no keyword arguments')
        if kind not in('ring','square','polygon','wire','symmetric_square','symmetric_polygon','multimetal','capacitor','via','transformer','balun'):raise ValueError('Native keyword input mode currently supports ring, square, polygon, symmetric/multi-metal coils, wire, capacitor, transformer and balun geometry')
        parameters['native_keyword']=True
    if request.get('native_interactive',False):
        if kind not in('wire','capacitor','via','square','polygon','ring','multimetal','symmetric_square','symmetric_polygon','transformer','balun','transformer3d'):raise ValueError('Native interactive input mode is not supported for this generator')
        parameters['native_interactive']=True
    return apply_edits(build_device(kind,technology=tech,**parameters),tech,request.get('edits',[]),with_links=with_links)


def handle(request,*,progress=None):
    """Execute one typed request; user input is never evaluated as Python."""
    tech = _technology(request)
    action = request.get("action","build")
    if action == "init":
        return dict(technology=tech.to_dict(),generators=list(KINDS)+list(PAIRED_KINDS),presets=list_presets(),preset=identify(tech))
    if action == "technology":
        text=load_preset(request["preset"],request.get("mim_density","1.5"),
                         substrate_rho=float(request.get("substrate_rho",10)),substrate_thickness=float(request.get("substrate_thickness",700)))
        selected=Technology.from_text(text)
        return dict(text=text,technology=selected.to_dict(),presets=list_presets(),preset=identify(selected))
    if action == "gds":
        definitions = request.get("shapes") or [request]
        shapes = [shape for definition in definitions for shape in _shapes(definition,tech)]
        return dict(base64=base64.b64encode(write_gds(shapes,tech,request.get("layer_map"))).decode())
    if action == "coupling":
        a,b = (_shape(request[key],tech) for key in ("first","second"))
        if a.name==b.name:raise ValueError("Cannot find self-coupling; use inductance instead")
        mutual,k = coupling_estimate(a,b,tech)
        return dict(mutual_nh=mutual,k=k)
    if action == "calctrans" or (action=="mesh" and request.get("model")=="calctrans"):
        if "first" in request and "second" in request:
            first,second=(_shape(request[key],tech) for key in ("first","second"))
        else:
            windings=_shapes(request,tech)
            i=int(request.get("first_winding",request.get("winding",0)));j=int(request.get("second_winding",1-i))
            if len(windings)<2 or i==j or not 0<=i<len(windings) or not 0<=j<len(windings):
                raise ValueError("CALCTRANS requires two windings or explicit first and second definitions")
            first,second=windings[i],windings[j]
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        mesh=_mesh(request,tech)
        if action=="mesh":return mesh_information(first,tech,mesh,model="calctrans",second=second,ground=ground,fit=bool(request.get("fit",False)))
        return solve_transformer(first,second,tech,_frequency(request),ground=ground,
            termination_ohm=float(request.get("termination_ohm",0)),eddy=request.get("eddy",False),include_matrices=bool(request.get("include_matrices",False)),
            max_width_cells=maximum_width_cells(mesh.get("max_width_cells",500)),
            **{key:float(mesh.get(key,1000)) for key in ("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")})
    windings,partners=_shapes(request,tech,with_links=True)if action=='build'else(None,None)
    shape = _shape(request,tech,shapes=windings,reset_missing=action=='build'and bool(request.get('reset_missing_winding',False)))
    if shape.kind=='via'and not any(s.metal<len(tech.metals)for s in shape.segments)and(action=='pi2'or(action=='mesh'and request.get('model','pi2')=='pi2')):
        raise ValueError('The original standalone VIA Pi2 analysis faults before producing a model; add conductor geometry')
    if action=="mesh":
        pads={key:_shape(request[key],tech) for key in ("first_pad","second_pad") if request.get(key)}
        return mesh_information(shape,tech,_mesh(request,tech),model=request.get("model","pi2"),fit=bool(request.get("fit",False)),**pads)
    if action=="selfres":
        mesh=_mesh(request,tech)
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        return solve_self_resonance(shape,tech,_frequency(request,'first'),_frequency(request,'last'),_frequency(request,'step'),
            ground=ground,differential=bool(request.get("differential",False)),fast=bool(request.get("fast",False)),eddy=request.get("eddy",False),
            observer=(lambda point:progress(json.dumps(point,allow_nan=False))) if progress is not None else None,
            max_width_cells=maximum_width_cells(mesh.get("max_width_cells",500)),
            **{key:float(mesh.get(key,1000)) for key in ("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")})
    if action in ("pi","pi2","pi3","pi4","pix"):
        if action=="pi":
            raise ValueError("The native fast Pi command faults on conductor coils before producing a model. Pi2, Pi3 and Pi4 use the working distributed solver.")
        mesh=_mesh(request,tech)
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        pads={"first_pad":_shape(request["first_pad"],tech),"second_pad":_shape(request["second_pad"],tech)} if action=="pi4" else {}
        solver={"pi2":solve_pi2,"pi3":solve_pi3,"pi4":solve_pi4,"pix":solve_pix}[action]
        diagnostics={"include_matrices":bool(request.get("include_matrices",False))} if action=="pix" else {}
        return solver(shape,tech,_frequency(request),ground=ground,eddy=request.get("eddy",False),**pads,**diagnostics,
                         max_width_cells=maximum_width_cells(mesh.get("max_width_cells",500)),
                         **{key:float(mesh.get(key,1000)) for key in ("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")})
    if action == "capacitance":
        mesh=_mesh(request,tech)
        ground=_shape(request["ground"],tech) if request.get("ground") else None
        return solve_capacitance(shape,tech,_frequency(request),ground=ground,
                                 length_cell=float(mesh.get("length_cell",1000)),width_cell=float(mesh.get("width_cell",1000)))
    if action == "lmat":
        mesh = _mesh(request,tech)
        return solve_impedance(shape,tech,_frequency(request),
                               eddy=request.get("eddy",False),
                               length_cell=float(mesh.get("length_cell",1000)),
                               width_cell=float(mesh.get("width_cell",1000)),
                               thickness_cell=float(mesh.get("thickness_cell",1000)),
                               max_width_cells=maximum_width_cells(mesh.get("max_width_cells",500)),
                               capacitance_length_cell=float(mesh["capacitance_length_cell"]) if "capacitance_length_cell" in mesh else None)
    if action == "build":
        data = shape.to_dict()
        data["windings"] = [w.name for w in windings]
        data['partners']=partners
        data['winding']=next(i for i,w in enumerate(windings)if w is shape)
        # Render exactly the polygons exported to GDS, including individual cuts.
        if sum(s.nx*s.ny for w in windings for s in w.segments) > 100000:
            raise ValueError("Preview supports at most 100,000 via cuts")
        data["polygons"] = [dict(metal=metal,points=[[point[0]+w.origin[0]-shape.origin[0],point[1]+w.origin[1]-shape.origin[1]] for point in points])
                            for w in windings for metal,points in layout_polygons(w,tech)]
        data["dc_ohm"] = resistance_dc(shape,tech)
        return data
    if action == "simulate":
        frequency = _frequency(request)
        retained_l,retained_dc=retained_estimates(shape,tech)
        inductance,dc=float(retained_l),float(retained_dc)
        hf = resistance_hf(shape,tech,frequency)
        qlf = extrapolated_q(retained_l,retained_dc,frequency)
        if not math.isfinite(qlf):qlf=None
        return dict(inductance_nh=inductance,dc_ohm=dc,hf_ohm=hf,qlf=qlf,
                    frequency_hz=frequency,method="ASITIC INDUCTANCE / RESIS / RESISHF / QLF estimates",
                    warnings=list(dict.fromkeys(shape.warnings)))
    if action == "sweep":
        first,last = _frequency(request,'first'),_frequency(request,'last')
        count = int(request.get("count",31))
        if not all(math.isfinite(v) for v in (first,last)) or not 0<first<last or not 2<=count<=201:
            raise ValueError("Sweep needs 0 < start < stop and 2–201 points")
        retained_l,retained_dc=retained_estimates(shape,tech)
        inductance,dc=float(retained_l),float(retained_dc)
        rows = []
        for i in range(count):
            f = first*(last/first)**(i/(count-1))
            if 'first_ghz'in request or'last_ghz'in request:f=frequency_ghz(f/1e9)
            hf = resistance_hf(shape,tech,f)
            qlf=extrapolated_q(retained_l,retained_dc,f)
            rows.append(dict(frequency_hz=f,inductance_nh=inductance,dc_ohm=dc,hf_ohm=hf,
                             qlf=qlf if math.isfinite(qlf)else None))
        return dict(rows=rows)
    raise ValueError(f"Unknown action: {action}")


def request_json(payload,progress=None):
    try:
        result=handle(json.loads(payload),progress=progress)
        if 'admittance_matrix'in result and any(not math.isfinite(v)for row in result['admittance_matrix']for z in row for v in z):
            raise ValueError('Distributed model returned nonfinite admittance; review the contact grid and conductor geometry')
        return json.dumps(dict(result=result),allow_nan=False)
    except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as error:
        return json.dumps(dict(error=str(error)))

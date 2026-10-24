"""Cheap mesh counts and explicit coarsening; no electrical solve is performed."""
import copy,math
from .solver import discretize,filament_counts
from .mesh_counts import maximum_width_cells
from .network import _join_for_pads

MESH_KEYS=("length_cell","width_cell","thickness_cell","capacitance_length_cell","capacitance_width_cell")


def mesh_information(first,technology,mesh,*,model="pi2",second=None,ground=None,first_pad=None,second_pad=None,fit=False):
    cells={key:float(mesh.get(key,1000)) for key in MESH_KEYS}
    if not all(math.isfinite(v) and v>0 for v in cells.values()):raise ValueError("Mesh cell sizes must be finite and positive")
    cells["max_width_cells"]=maximum_width_cells(mesh.get("max_width_cells",500))
    if model not in ("lmat","pi2","pi3","pi4","pix","selfres","calctrans"):raise ValueError("Unknown mesh analysis")
    def count(values):
        length,width,thickness,caplength,_=(values[key] for key in MESH_KEYS)
        if model=="calctrans":
            if second is None:raise ValueError("Coupled mesh requires two windings")
            shapes=copy.deepcopy([first,second])
            if ground is not None:
                for shape in shapes:
                    if shape.name==ground.name:
                        for s in shape.segments:s.nx=s.ny=-1
            shapes=[discretize(s,caplength,length) for s in shapes]
        elif model=="pi4":
            if first_pad is None or second_pad is None:raise ValueError("Pi4 mesh requires both pad strips")
            pads=copy.deepcopy([first_pad,second_pad])
            for pad in pads:
                for s in pad.segments:s.nx=s.ny=-1
            winding=discretize(first,caplength,length)
            joined=_join_for_pads(_join_for_pads(pads[0],winding),pads[1])
            shapes=[discretize(joined,caplength,length)]
        else:shapes=[discretize(first,caplength if model!="lmat" else length,length)]
        total=segments=0
        for shape in shapes:
            for segment in shape.segments:
                if segment.metal>=len(technology.metals):continue
                ny,nz=filament_counts(segment,width,thickness,values["max_width_cells"]);total+=ny*nz;segments+=1
        return dict(filaments=total,segments=segments,limit=256,within_limit=total<=256,model=model,mesh=values)
    def attempt(values):
        try:return count(values)
        except ValueError as error:
            if "Longitudinal mesh exceeds" not in str(error):raise
            return None
    initial=attempt(cells)
    if not fit:
        if initial is None:raise ValueError("Longitudinal mesh exceeds 2000 segments; use Fit to 256 filaments or larger cell sizes")
        return initial
    if initial and initial["within_limit"]:return dict(initial,changed=False)
    baseline=count({key:1e15 if key in MESH_KEYS[:3] else value for key,value in cells.items()})
    if not baseline["within_limit"]:
        raise ValueError(f"Even the coarsest {model} mesh needs {baseline['filaments']} filaments. Reduce the number of turns/segments or analyze a single winding.")
    for exponent in range(1,64):
        proposed={key:value*2**exponent if key in MESH_KEYS[:3] else value for key,value in cells.items()}
        result=attempt(proposed)
        if result and result["within_limit"]:return dict(result,changed=True)
    raise ValueError("Could not fit this mesh; enter larger cell sizes")

"""Paired winding creators from winding_construction / console_geometry.

Every winding remains a separate electrical shape. GDS exports both, while
single-shape estimates and LMAT operate on the selected winding.
"""
import math
from .geometry import build
from .model import Shape
from .technology import Technology
from .retained_scalar import Real

PAIRED_KINDS = ("transformer","balun","transformer3d")
PAIRED_ALIASES = {"3dtrans":"transformer3d","3dmirrortrans":"transformer3d","trans3d":"transformer3d",
                  "transmim":"transformer3d","mirror_transformer3d":"transformer3d"}


def build_device(kind="square",*,technology=None,**parameters):
    tech = technology or Technology.default()
    kind = PAIRED_ALIASES.get(kind.lower(),kind.lower())
    if kind not in PAIRED_KINDS:
        return [build(kind,technology=tech,**parameters)]
    if kind in('transformer','balun'):
        from .paired_geometry import build_paired
        return build_paired(kind,tech,parameters)
    p = dict(parameters)
    keyword=bool(p.pop('native_keyword',False));interactive=bool(p.pop('native_interactive',False))
    if keyword and interactive:raise ValueError('Choose one native input mode')
    if keyword:raise ValueError('The original 3D transformer command is interactive and accepts no keyword arguments')
    def number(key,default):
        value = float(p.get(key,default))
        if not math.isfinite(value):
            raise ValueError(f"{key} must be finite")
        return value
    name = str(p.get("name","T1"))
    length = number("length",100)
    width = number("width",3)
    spacing = number("spacing",8 if kind=="transformer3d" else 2)
    x,y = number("x",0),number("y",0)
    angle = number("angle",0)
    if width<=0 or (not interactive and length<=0) or spacing<0 or max(abs(length),width)>1e6 or abs(angle)>360:
        raise ValueError("Invalid transformer dimensions or orientation")
    metal = tech.metal_index(p.get("metal",len(tech.metals)-1))
    primary_name = str(p.get("primary_name",name+"-P"))
    secondary_name = str(p.get("secondary_name",name+"-S"))
    if interactive:
        from .paired_geometry import _name
        primary_name,secondary_name=(_name(n).split(' ',1)[0]for n in(primary_name,secondary_name))
        if width<float.fromhex('0x1.b7cdfd9d7bdbbp-34'):raise ValueError('3D transformer width must be at least 1e-10 µm')
    if (not interactive and primary_name==secondary_name) or not all(0<len(n)<=79 and(not interactive or len(n.encode('utf8'))<=79)for n in(primary_name,secondary_name)):
        raise ValueError("Windings need distinct names of 1–79 characters")
    from .transformer3d import build_3d
    height = number("height",length)
    turns = number("turns",2)
    secondary_metal = tech.metal_index(p.get("secondary_metal",max(0,metal-1)))
    if secondary_metal==metal:
        raise ValueError("3D transformer windings must use distinct metals")
    projected = (Real(spacing)-Real(float.fromhex("0x1.a8240b780346ep-2"))*Real(width))/Real(float.fromhex("0x1.6a0902de00d1bp+0"))
    if projected<2:
        raise ValueError("Spacing too small for the original 3D transformer transitions")
    if not 1<=turns<=1000 or abs(height)>1e6 or(not interactive and height<=0):
        raise ValueError("3D transformer needs 1–1000 turns and a positive height")
    phase = number("phase",1)
    if interactive:phase=int(phase)
    if phase not in (-1,1):
        raise ValueError("3D transformer phase must be +1 or −1")
    common = dict(p,length=length,height=height,width=width,spacing=spacing,turns=turns,angle=angle,phase=phase,secondary_metal=secondary_metal)
    primary = Shape(primary_name,kind,[x,y],dict(common,metal=metal))
    secondary = Shape(secondary_name,kind,[x,y],dict(common,metal=secondary_metal))
    build_3d(primary,secondary,tech)
    if angle or phase<0:
        for winding in (primary,secondary):
            winding.warnings.append("The original 3D creator records orientation and phase without transforming its segments.")
    return [primary,secondary]

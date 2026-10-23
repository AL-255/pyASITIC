"""Paired winding creators from winding_construction / console_geometry.

Every winding remains a separate electrical shape. GDS exports both, while
single-shape estimates and LMAT operate on the selected winding.
"""
import math
from .geometry import build, _square
from .model import Shape
from .technology import Technology

PAIRED_KINDS = ("transformer","balun","transformer3d")


def build_device(kind="square",*,technology=None,**parameters):
    tech = technology or Technology.default()
    kind = {"3dtrans":"transformer3d","3dmirrortrans":"transformer3d","trans3d":"transformer3d",
            "transmim":"transformer3d","mirror_transformer3d":"transformer3d"}.get(kind.lower(),kind.lower())
    if kind not in PAIRED_KINDS:
        return [build(kind,technology=tech,**parameters)]
    p = dict(parameters)
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
    if min(length,width)<=0 or spacing<0 or max(length,width)>1e6 or abs(angle)>360:
        raise ValueError("Invalid transformer dimensions or orientation")
    metal = tech.metal_index(p.get("metal",len(tech.metals)-1))
    primary_name = str(p.get("primary_name",name+"-P"))
    secondary_name = str(p.get("secondary_name",name+"-S"))
    if primary_name==secondary_name or not all(0<len(n)<=79 for n in (primary_name,secondary_name)):
        raise ValueError("Windings need distinct names of 1–79 characters")
    if kind=="transformer":
        height = number("height",length)
        turns,secondary_turns = number("turns",1.5),number("secondary_turns",p.get("turns",1.5))
        internal_spacing = spacing*2+width
        maximum = math.floor((min(length,height)/(2*(width+internal_spacing))-.25)*4)/4
        if min(turns,secondary_turns)<=0 or max(turns,secondary_turns)>maximum:
            raise ValueError(f"Transformer windings support at most {maximum:g} turns")
        turns,secondary_turns = math.floor(turns*4)/4,math.floor(secondary_turns*4)/4
        if min(turns,secondary_turns)<=0 or max(turns,secondary_turns)>1000:
            raise ValueError("Invalid transformer turn count")
        exit_value = p.get("exit_metal",-1)
        exit_metal = -1 if str(exit_value)=="-1" else tech.metal_index(exit_value)
        if exit_metal==metal:
            raise ValueError("Exit metal must differ from the winding metal")
        phase = number("phase",1)
        primary = Shape(primary_name,kind,[x,y],dict(p,turns=turns))
        secondary = Shape(secondary_name,kind,[x,y],dict(p,turns=secondary_turns))
        for shape,n in ((primary,turns),(secondary,secondary_turns)):
            _square(shape,tech,metal,exit_metal,length,height,width,internal_spacing,n,math.radians(angle),phase)
        secondary.reflect(0)
        secondary.reflect(1)
        shift = width+spacing
        for point in (secondary.segments[0].start,secondary.segments[0].outer_start,secondary.segments[0].inner_start):
            point[0] += shift
        for point in (primary.segments[0].start,primary.segments[0].outer_start,primary.segments[0].inner_start):
            point[0] -= shift
        primary.origin[0] += shift
        primary.origin[1] += shift
        if exit_metal!=-1:
            fraction = secondary_turns%1
            if fraction==.25:
                primary.origin[0] += width
            elif fraction==.75:
                primary.origin[0] -= width
            elif fraction==.5:
                primary.origin[1] -= width
            else:
                primary.origin[1] += width
    elif kind=="balun":
        secondary_width = number("secondary_width",width)
        total_turns = number("turns",3)
        if total_turns<3 or secondary_width<=0:
            raise ValueError("Balun needs at least three total turns and positive winding widths")
        primary_turns = math.floor((total_turns+1)/2)
        secondary_turns = primary_turns-1
        gap = 2*spacing+width+secondary_width
        common = dict(technology=tech,metal=metal,secondary_metal=p.get("secondary_metal",max(0,metal-1)),
                      inner_gap=gap,angle=angle)
        primary = build("symmetric_square",**common,name=primary_name,length=length,width=width,
                        spacing=2*spacing+secondary_width,turns=primary_turns,x=x,y=y)
        secondary = build("symmetric_square",**common,name=secondary_name,length=length-2*(spacing+width),
                          width=secondary_width,spacing=2*spacing+width,turns=secondary_turns,x=x+width+spacing,y=y+width+spacing)
        primary.kind=secondary.kind=kind
        secondary.reflect(0)
        for segment in secondary.segments:
            segment.reverse()
    else:
        from .transformer3d import build_3d
        height = number("height",length)
        turns = number("turns",2)
        secondary_metal = tech.metal_index(p.get("secondary_metal",max(0,metal-1)))
        if secondary_metal==metal:
            raise ValueError("3D transformer windings must use distinct metals")
        projected = (spacing-float.fromhex("0x1.a8240b780346ep-2")*width)/float.fromhex("0x1.6a0902de00d1bp+0")
        if projected<2:
            raise ValueError("Spacing too small for the original 3D transformer transitions")
        if not 1<=turns<=1000 or not 0<height<=1e6:
            raise ValueError("3D transformer needs 1–1000 turns and a positive height")
        phase = number("phase",1)
        if phase not in (-1,1):
            raise ValueError("3D transformer phase must be +1 or −1")
        common = dict(p,length=length,height=height,width=width,spacing=spacing,turns=turns,angle=angle,phase=phase)
        primary = Shape(primary_name,kind,[x,y],dict(common,metal=metal))
        secondary = Shape(secondary_name,kind,[x,y],dict(common,metal=secondary_metal))
        build_3d(primary,secondary,tech)
        if angle or phase<0:
            for winding in (primary,secondary):
                winding.warnings.append("The original 3D creator records orientation and phase without transforming its segments.")
    return [primary,secondary]

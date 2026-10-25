"""Dependency-free GDSII stream output; 1 µm user unit, 1 nm database unit.

Metal i defaults to GDS layer i+1; via i defaults to 100+i. Foundry presets
can set chip gds_<name> mappings, and caller mappings override them.
Ribbons are BOUNDARY elements, never PATH strokes.
"""
import math
import struct


def _real8(value):
    if value == 0:
        return bytes(8)
    sign = 0x80 if value < 0 else 0
    value = abs(value)
    exponent = 64
    while value >= 1:
        value /= 16
        exponent += 1
    while value < 1/16:
        value *= 16
        exponent -= 1
    return bytes([sign|exponent])+int(value*2**56).to_bytes(7,"big")


def _record(kind, dtype=0, payload=b""):
    if len(payload)%2:
        payload += b"\0"
    return struct.pack(">HBB",len(payload)+4,kind,dtype)+payload


def layout_polygons(shape, technology):
    """Yield (encoded layer index, polygon) in local micrometres.

    Via array cuts follow cif_emit_via's pitch, with a rigid transform so
    rotated/flipped via records retain their orientation. Both metal landing
    pads include the technology's respective overplot.
    """
    count = len(technology.metals)
    for s in shape.all_segments:
        if s.metal < count:
            yield s.metal, s.polygon
            continue
        via = technology.vias[s.metal-count]
        a,b,c = s.outer_start,s.outer_end,s.inner_start
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        ex = (dx/length,dy/length)
        dx,dy = a[0]-c[0],a[1]-c[1]
        height = math.hypot(dx,dy)
        ey = (dx/height,dy/height)
        def point(x,y):
            return [c[0]+x*ex[0]+y*ey[0],c[1]+x*ex[1]+y*ey[1]]
        def rectangle(x0,y0,x1,y1):
            return [point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1)]
        for metal,overplot in ((via.bottom,via.overplot1),(via.top,via.overplot2)):
            yield metal,rectangle(-overplot,-overplot,length+overplot,height+overplot)
        step = via.width+via.spacing
        for ix in range(s.nx):
            for iy in range(s.ny):
                yield s.metal,rectangle(ix*step,iy*step,ix*step+via.width,iy*step+via.width)


def write_gds(shapes, technology, layer_map=None):
    """Return a complete GDSII library as bytes (deterministic timestamps).

    layer_map maps technology names to GDS layer integers or (layer,datatype).
    """
    if not isinstance(shapes,(list,tuple)):
        shapes = [shapes]
    # Bundled foundry presets can specify their drawn GDS layers in <chip>.
    # Explicit caller mappings retain precedence, including per-layer datatypes.
    layer_map = {**{m.name:int(technology.chip["gds_"+m.name.lower()]) for m in technology.metals+technology.vias
                   if "gds_"+m.name.lower() in technology.chip},**(layer_map or {})}
    stamp = struct.pack(">12h",*(2000,1,1,0,0,0)*2)
    data = bytearray(_record(0,2,struct.pack(">h",600))+_record(1,2,stamp))
    data += _record(2,6,b"reASITIC")+_record(3,5,_real8(1e-3)+_real8(1e-9))
    data += _record(5,2,stamp)+_record(6,6,b"LAYOUT")
    count = len(technology.metals)
    names = [m.name for m in technology.metals]+[v.name for v in technology.vias]
    for shape in shapes:
        for index,polygon in layout_polygons(shape,technology):
            mapped = layer_map.get(names[index],index+1 if index<count else 100+index-count)
            layer,datatype = (mapped,0) if isinstance(mapped,int) else mapped
            if not (0 <= layer <= 32767 and 0 <= datatype <= 32767):
                raise ValueError("GDS layer and datatype must be in [0,32767]")
            coords = [(round((x+shape.origin[0])*1000),round((y+shape.origin[1])*1000)) for x,y in polygon]
            # Original creators can retain zero-length metal ribbons (e.g.
            # symmetric explicit ILEN=0). Preserve their closed boundaries,
            # including repeated vertices, instead of dropping native records.
            if any(abs(c)>2147483647 for p in coords for c in p):
                raise ValueError("Layout exceeds the signed 32-bit GDS coordinate range")
            coords.append(coords[0])
            xy = struct.pack(">"+"i"*(2*len(coords)),*(c for p in coords for c in p))
            data += _record(8)+_record(13,2,struct.pack(">h",layer))+_record(14,2,struct.pack(">h",datatype))
            data += _record(16,3,xy)+_record(17)
    data += _record(7)+_record(4)
    return bytes(data)

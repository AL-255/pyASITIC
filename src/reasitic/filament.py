"""Original retained filament interpolation, with one compiled batch per mesh."""
from array import array
from decimal import Decimal,localcontext,InvalidOperation,DivisionByZero,Overflow
from .fft import _fft_extended,_fft_spill

try:
    from _reasitic_numeric import filaments as _compiled_filaments
except ImportError:
    _compiled_filaments=None


class _Real:
    def __init__(self,value):
        self.value=value.value if isinstance(value,_Real) else Decimal.from_float(value) if isinstance(value,float) else Decimal(value)
    def __float__(self):return _fft_spill(self.value)
    def __neg__(self):return _Real(self.value.copy_negate())
    def __add__(self,other):return _Real(_fft_extended(self.value+_Real(other).value))
    __radd__=__add__
    def __sub__(self,other):return _Real(_fft_extended(self.value-_Real(other).value))
    def __rsub__(self,other):return _Real(other)-self
    def __mul__(self,other):return _Real(_fft_extended(self.value*_Real(other).value))
    __rmul__=__mul__
    def __truediv__(self,other):return _Real(_fft_extended(self.value/_Real(other).value))
    def __gt__(self,other):return self.value>_Real(other).value
    def sqrt(self):return _Real(_fft_extended(self.value.sqrt()))


def _build(p):
    r=_Real
    a,b,c,d=(list(p[i:i+3]) for i in (0,3,6,9))
    width,thickness,layer,ox,oy,cell=p[12:18]
    cap,xi,yi,zi,nx,ny,nz,metal=map(int,p[18:])
    count=ny
    if r(width)/cell>cap:
        edges=int((r(.4)*ny).value);middle=cap-2*edges
        def blend(start,end,destination):
            ratio=(r(edges)*cell)/((r(start[0])*end[0]+r(start[1])*end[1])+r(start[2])*end[2]).sqrt()
            inv=r(1)-ratio
            return [float(r(start[0])*inv+ratio*end[0]),float(inv*start[1]+r(float(ratio))*end[1]),destination[2]]
        if yi<edges:
            c,d=blend(a,c,c),blend(b,d,d);filament_width=cell;count=edges
        elif yi>cap-edges-1:
            a,b=blend(c,a,a),blend(d,b,b);yi-=edges+middle;filament_width=cell;count=edges
        else:
            a,b,c,d=blend(a,c,a),blend(b,d,b),blend(c,a,c),blend(d,b,d);yi-=edges
            filament_width=float((r(width)-(r(cell)+cell)*edges)/edges);count=middle
    else:filament_width=float(r(width)/ny)
    u,v=float(r(xi)/nx),float((r(yi)+.5)/count)
    vm,um=float(r(1)-v),float(r(1)-u)
    weight=((r(u)*v+1)-u)-v
    vcx=float(r(v)*c[0]);vcy=r(v)*c[1]
    x=float((((r(b[0])*u*(r(1)-v)+r(a[0])*weight)+r(vcx)*(r(1)-u))+r(d[0])*u*v)+ox)
    y=float((((r(a[1])*weight+r(b[1])*u*vm)+vcy*um)+r(d[1])*u*v)+oy)
    z=float((r(layer)*.5+a[2])-(r(zi)+1)/(r(nz)+1))
    raw_u1=r(xi+1)/nx;u1=float(raw_u1)
    weight1=((raw_u1*v+1)-raw_u1)-v;um1=r(1)-u1
    endx=float((((r(b[0])*u1*vm+r(a[0])*weight1)+r(vcx)*um1)+r(d[0])*u1*v)+ox)
    endy=float((((r(a[1])*weight1+r(b[1])*u1*vm)+um1*float(vcy))+r(d[1])*u1*v)+oy)
    return [x,y,z,endx,endy,z,filament_width,float(r(thickness)/nz),float(metal)]


def filament_records(records):
    """26-double input rows to native 8-double filament records plus metal.

    Fields: four ribbon corners, width/thickness/layer thickness, XY origin,
    edge cell, maximum width count, XYZ indices, XYZ counts, metal index.
    Inputs are never modified. Nonfinite native coordinates remain observable.
    """
    result=[]
    if _compiled_filaments is not None:
        for start in range(0,len(records),256):
            chunk=records[start:start+256];data=array("d",(v for row in chunk for v in row));output=array("d",[0.])*(9*len(chunk))
            if _compiled_filaments(data,output):raise ValueError("Invalid filament configuration")
            result.extend(list(output[i:i+9]) for i in range(0,len(output),9))
        return result
    with localcontext() as context:
        context.prec=2048
        for signal in (InvalidOperation,DivisionByZero,Overflow):context.traps[signal]=False
        return [_build(row) for row in records]


def record(segment,origin,yi,zi,ny,nz,edge_cell,max_width_cells,technology):
    return [*segment.inner_start,*segment.inner_end,*segment.outer_start,*segment.outer_end,
            segment.width,segment.thickness,technology.metals[segment.metal].thickness,*origin[:2],
            edge_cell,max_width_cells,0,yi,zi,1,ny,nz,segment.metal]

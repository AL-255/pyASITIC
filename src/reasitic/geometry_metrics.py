"""Original GEOM running F64 stores and retained METALAREA calculation."""
from array import array
from functools import lru_cache
import struct
from .retained_scalar import Real as R
from .conductor_metrics import _operand

try:
    from _reasitic_numeric import geometry_metrics as _compiled
except ImportError:
    _compiled=None

EPS=R(float.fromhex('0x1.b7cdfd9d7bdbbp-34'))


def segment_length(start,end):
    dx,dy,dz=(R(end[k])-R.memory_operand(start[k])for k in range(3))
    return ((dx*dx+dy*dy)+dz*dz).sqrt()


def _portable(records,observe=None):
    length_sum=area_sum=0.;metal_area=R(0.)
    for i,p in enumerate(records):
        length=segment_length(p[:3],p[3:6]);width=R(p[6]);area=length*width
        length_sum=float(R(length_sum)+length);area_sum=float(area+R(area_sum))
        if length>EPS:metal_area=area+metal_area
        if observe is not None:observe(dict(segment=i,length=length,width=width,length_sum=length_sum,area_sum=area_sum,metal_area=metal_area))
    return length_sum,area_sum,metal_area


@lru_cache(maxsize=32)
def _evaluate(key):
    count=len(key)//56
    if _compiled is None or count>20000:return _portable(struct.iter_unpack('<7d',key))
    data=array('d',struct.unpack('<'+'d'*(7*count),key));out=array('d',[0.])*6
    if _compiled(data,out):raise ValueError('Invalid geometry metric configuration')
    return out[0],out[1],_operand(out[3:6])


def retained_geometry_metrics(shape):
    """Return GEOM length/area and raw METALAREA; does not alter geometry."""
    return _evaluate(b''.join(struct.pack('<7d',*s.start,*s.end,s.width)for s in shape.segments))

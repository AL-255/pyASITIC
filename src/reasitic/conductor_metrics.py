"""Retained original INDUCTANCE, DC total and Q/QUALITY extrapolation."""
from array import array
from fractions import Fraction
from functools import lru_cache
import math,struct
from .retained_scalar import Real as R
from .impedance import _log

try:
    from _reasitic_numeric import conductor_metrics as _compiled
except ImportError:
    _compiled=None

SCALE=R(float.fromhex('0x1.a36e2eb1c432dp-14'))
EPS=R(float.fromhex('0x1.b7cdfd9d7bdbbp-34'))
QLF_FACTOR=R(float.fromhex('0x1.afc6f70213be5p-28'))


def _records(shape,technology):
    from .resistance import _records as resistance_records
    rows=resistance_records(shape,technology);count=len(technology.metals)
    for s,row in zip(shape.segments,rows):
        if s.metal>=count:
            via=technology.vias[s.metal-count];row.extend([via.width,via.spacing,0.,0.])
        else:row.extend([0.,0.,s.width if s.primary_width is None else s.primary_width,s.thickness if s.primary_thickness is None else s.primary_thickness])
    return rows


def _operand(words):
    return R.from_words(*words)


def _self_and_dc(rows,observe=None):
    self=R(0.);dc=R(0.)
    for i,p in enumerate(rows):
        dx,dy,dz=(R(p[k+3])-R(p[k])for k in range(3))
        if p[9]:
            length=abs(dz)*SCALE;width=(SCALE*R(p[10]))*R(p[12]);thickness=(SCALE*R(p[11]))*R(p[13])
            cells=((int(p[10])*int(p[11])+(1<<31))%(1<<32))-(1<<31);contribution=R(p[8])/R(cells)
        else:
            length=((dx*dx+dy*dy)+dz*dz).sqrt()*SCALE;width=R(p[6])*SCALE;thickness=R(p[7])*SCALE
            contribution=(((dz*dz+dy*dy)+dx*dx).sqrt()/R(p[6]))*R(p[8])
        dc=contribution+dc;trace=dict(segment=i,length=length,width=width,thickness=thickness)
        if length>EPS:
            twice=length+length;size=width+thickness;argument=twice/size;logarithm=_log(argument)
            term=twice*(size/(R(3.)*length)+(logarithm+R(float.fromhex('0x1.004039abf3387p-1'))));self=term+self
            trace.update(log_argument=argument,log_return=logarithm)
        trace['accumulator']=self
        if observe is not None:observe(trace)
    return self,dc


def _portable(rows):
    from .inductance import segment_mutual
    self,dc=_self_and_dc(rows);mutual=R(0.);warnings=[]
    geometry=[[*p[:6],p[14],p[15]]for p in rows if not p[9]]
    for i,a in enumerate(geometry):
        for b in geometry[i+1:]:mutual=mutual+R(segment_mutual(a,b,warnings))
    return (mutual+mutual)+self,dc,tuple(dict.fromkeys(warnings))


@lru_cache(maxsize=8)
def _evaluate(key):
    rows=list(struct.iter_unpack('<16d',key))
    if _compiled is None:return _portable(rows)
    data=array('d',(v for p in rows for v in p));output=array('d',[0.])*9
    if _compiled(data,output):raise ValueError('Invalid conductor metric configuration')
    from .mutual_kernel import WARNING_MESSAGES
    warnings=tuple(message for code,message in WARNING_MESSAGES.items()if int(output[8])&(1<<code))
    return _operand(output[1:4]),_operand(output[5:8]),warnings


def retained_estimates(shape,technology):
    if len(shape.segments)>2000:raise ValueError('Inductance estimate is limited to 2000 segments')
    result=_evaluate(b''.join(struct.pack('<16d',*p)for p in _records(shape,technology)))
    for warning in result[2]:
        if warning not in shape.warnings:shape.warnings.append(warning)
    return result[:2]


def qlf(inductance,dc,frequency):
    """Original Q command: retained constant*frequency*L / raw DC return."""
    return float(((QLF_FACTOR*R(frequency))*inductance)/dc)

"""Original COUPLING F64 sum, retained normalization and in-place translations."""
from array import array
from .retained_scalar import Real as R
from .conductor_metrics import retained_estimates,_operand

try:
    from _reasitic_numeric import coupling_metrics as _compiled
except ImportError:
    _compiled=None

EPS=R(float.fromhex('0x1.b7cdfd9d7bdbbp-34'))


def _translate(record,origin,subtract=False):
    for k in(0,1,3,4):record[k]=float(R(record[k])-R(origin[k%3])if subtract else R(record[k])+R(origin[k%3]))


def _portable(first,second,origins,l1,l2,observe=None):
    from .inductance import segment_mutual
    mutual=0.;warnings=[]
    for i,a in enumerate(first):
        for j,b in enumerate(second):
            _translate(a,origins[0]);_translate(b,origins[1])
            event=dict(first=i,second=j,inputs=[*a,*b])if observe is not None else None
            pair=segment_mutual(a,b,warnings);mutual=float(R(mutual)+R(pair))
            if observe is not None:observe(dict(event,value=pair,sum=mutual))
            _translate(a,origins[0],True);_translate(b,origins[1],True)
    coefficient=R(mutual)/(R(l1)*R(l2)).sqrt()if EPS<R(l1)and EPS<R(l2)else R(0.)
    return mutual,coefficient,warnings


def _evaluate(first,second,origins,l1,l2,observe=None):
    if _compiled is None or observe is not None:return _portable(first,second,origins,l1,l2,observe)
    data=array('d',(v for p in first+second for v in p));data.extend([*origins[0],*origins[1],l1,l2]);out=array('d',[0.])*len(data)
    if _compiled(data,out,len(first),len(second)):raise ValueError('Invalid coupling metric configuration')
    for i,p in enumerate(first+second):p[:]=out[8*i:8*i+8]
    offset=8*(len(first)+len(second));from .mutual_kernel import WARNING_MESSAGES
    warnings=[message for code,message in WARNING_MESSAGES.items()if int(out[offset+5])&(1<<code)]
    return out[offset],_operand(out[offset+2:offset+5]),warnings


def retained_coupling(first,second,technology,observe=None):
    if first is second:raise ValueError('Cannot find self-coupling; use inductance instead')
    if len(first.segments)*len(second.segments)>1000000:raise ValueError('Coupling estimate exceeds one million segment pairs')
    l1,l2=(float(retained_estimates(s,technology)[0])for s in(first,second))
    metals=len(technology.metals);segments=[[p for p in s.segments if p.metal<metals]for s in(first,second)]
    records=[[[*p.start,*p.end,p.width if p.primary_width is None else p.primary_width,p.thickness if p.primary_thickness is None else p.primary_thickness]for p in winding]for winding in segments]
    mutual,coefficient,warnings=_evaluate(*records,[first.origin,second.origin],l1,l2,observe)
    # Native add/store, mutual, subtract/store runs for every pair. Subtraction
    # need not restore the original F64 coordinates; retain this actual history.
    # Edge coordinates and primary widths/thicknesses are untouched by COUPLING.
    for winding,computed in zip(segments,records):
        for segment,p in zip(winding,computed):segment.start[:]=p[:3];segment.end[:]=p[3:6]
    for warning in warnings:
        if warning not in first.warnings:first.warnings.append(warning)
    return mutual,coefficient

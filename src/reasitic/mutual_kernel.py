"""Batched retained segment-pair transport with geometry-only caching."""
from array import array
from functools import lru_cache
import struct

try:
    from _reasitic_numeric import mutual as _compiled_mutual
except ImportError:
    _compiled_mutual=None

WARNING_MESSAGES={1:"Segments intersect; their mutual contribution is zero, as in ASITIC.",2:"Warning:  An unknown error has occurred."}


def probe(rows):
    if _compiled_mutual is None:return None
    result=[]
    for start in range(0,len(rows),256):
        chunk=rows[start:start+256]
        data=array("d",(value for row in chunk for value in [*row,*([0.]*(18-len(row)))]));out=array("d",[0.])*(6*len(chunk))
        if _compiled_mutual(data,out):raise ValueError("Invalid mutual configuration")
        result.extend(list(out[i:i+6]) for i in range(0,len(out),6))
    return result


@lru_cache(maxsize=32768)
def _pair(record):
    out=probe([[4,*struct.unpack("=16d",record)]])[0]
    if out[0]:raise ValueError("Native segment mutual evaluation failed")
    return out[1],int(out[5])


def segment_value(a,b):
    if _compiled_mutual is None:return None
    return _pair(struct.pack("=16d",*a,*b))


@lru_cache(maxsize=8)
def mesh_mutual(records):
    """Return packed status/value/warning triples in upper-triangle order.

    The key contains only filament geometry, preserving signed zeros. Cache
    values use bounded packed doubles rather than Python per-pair objects.
    Nonzero statuses remain explicit; environments without the module use the
    existing portable Python implementation instead.
    """
    if _compiled_mutual is None:return None
    wires=list(struct.iter_unpack("=8d",records));result=array("d");chunk=[]
    for i,first in enumerate(wires):
        for second in wires[i+1:]:
            chunk.append([4,*first,*second])
            if len(chunk)==256:
                result.extend(v for row in probe(chunk) for v in (row[0],row[1],row[5]));chunk=[]
    if chunk:result.extend(v for row in probe(chunk) for v in (row[0],row[1],row[5]))
    return result

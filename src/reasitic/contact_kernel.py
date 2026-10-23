"""Batch transport for the original retained contact-potential arithmetic."""
from array import array

try:
    from _reasitic_numeric import contact_pair as _compiled_contact_pair
except ImportError:
    _compiled_contact_pair=None


def contact_matrix(contacts,nx,ny,width,height,records,coefficients,depths,get_table):
    n,nm,nl=len(contacts),len(records),len(coefficients)
    if _compiled_contact_pair is None or max(n,nm,nl)>256:return None
    config=array("d",[1,n,nx,ny,nm,nl,0,0,width,height,0,0,0,0,0,0])
    config.extend(v for c in contacts for v in (c.x0,c.x1,c.y0,c.y1,c.metal))
    config.extend(v for record in records for v in record)
    config.extend(v for z in coefficients for v in (z.real,z.imag))
    config.extend(depths)
    result=array("d",[0.0])*(2*n*n)
    metals=sorted({c.metal for c in contacts})
    for i,low in enumerate(metals):
        for high in metals[i:]:
            config[6],config[7]=low,high
            tables=array("d",(v for table in get_table(low,high) for z in table for v in (z.real,z.imag)))
            if _compiled_contact_pair(config,tables,result):raise ValueError("Invalid contact-potential kernel configuration")
    return [[complex(result[2*(i*n+j)],result[2*(i*n+j)+1]) for j in range(n)] for i in range(n)]

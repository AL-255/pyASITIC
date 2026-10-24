"""Original via impedance formula and matrix-store order (vias.cpp)."""
from array import array
from decimal import Decimal,localcontext,InvalidOperation,DivisionByZero
from fractions import Fraction
from .inductance import SELF_CONSTANT,_round_extended

try:
    from _reasitic_numeric import via_stamp as _compiled_via_stamp
except ImportError:
    _compiled_via_stamp=None


def active_height(start,end):
    return _round_extended(Fraction(end)-Fraction(start))>Fraction(float.fromhex("0x1.b7cdfd9d7bdbbp-34"))


def stamp(rows):
    """Stamp bounded batches of nine-value via records; return complex cells.

    Records contain frequency, start/end Z, perimeter step, resistance,
    width/thickness counts and the existing matrix real/imaginary values.
    The browser retains 80-bit operations through each original binary64 store.
    The portable Decimal path retains guard precision, as other solver fallbacks.
    """
    result=[]
    for start in range(0,len(rows),256):
        chunk=rows[start:start+256]
        if any(len(row)!=9 or any(not isinstance(n,int) or not -65535<=n<=65535 for n in row[5:7]) for row in chunk):
            raise ValueError("Invalid via record or cell counts")
        if _compiled_via_stamp is not None:
            data=array("d",(v for row in chunk for v in row));output=array("d",[0.])*(2*len(chunk))
            if _compiled_via_stamp(data,output):raise ValueError("Invalid via batch")
            result.extend(complex(output[i],output[i+1]) for i in range(0,len(output),2))
            continue
        with localcontext() as context:
            context.prec=25
            context.traps[InvalidOperation]=context.traps[DivisionByZero]=False
            d=Decimal.from_float
            for f,lo,hi,width,resistance,nx,ny,real,imag in chunk:
                height=d(hi)-d(lo)
                if not height>d(float.fromhex("0x1.b7cdfd9d7bdbbp-34")):
                    result.append(complex(real,imag));continue
                perimeter=d(width)*ny+d(width)*nx
                cells=(nx*ny+2**31)%2**32-2**31
                omega=d(float(d(float.fromhex("0x1.921fb54442d18p+2"))*d(f)))
                inductance=(height*d(float.fromhex("0x1.a36e2eb1c432dp-13")))*(((height*2/perimeter).ln()+d(SELF_CONSTANT))+perimeter/(height*3))
                reactance=float((inductance*omega)*d(float.fromhex("0x1.12e0be826d695p-30")))
                result.append(complex(float(d(real)+d(resistance)/cells),float(d(imag)+d(reactance))))
    return result

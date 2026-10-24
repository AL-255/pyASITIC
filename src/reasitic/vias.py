"""Original via impedance formula and matrix-store order (vias.cpp)."""
from array import array
import struct
from .inductance import SELF_CONSTANT
from .retained_scalar import Real as R
from .x87_math import log_retained

try:
    from _reasitic_numeric import via_stamp as _compiled_via_stamp
except ImportError:
    _compiled_via_stamp=None


def active_height(start,end):
    return R(end)-R(start)>R(float.fromhex("0x1.b7cdfd9d7bdbbp-34"))


def _terms(f,lo,hi,width,resistance,nx,ny):
    height=R(hi)-R(lo)
    if not height>R(float.fromhex("0x1.b7cdfd9d7bdbbp-34")):return None
    perimeter=R(width)*R(ny)+R(width)*R(nx)
    cells=(nx*ny+2**31)%2**32-2**31
    omega=float(R(float.fromhex("0x1.921fb54442d18p+2"))*R(f))
    inductance=(height*R(float.fromhex("0x1.a36e2eb1c432dp-13")))*((log_retained((height+height)/perimeter)+R(SELF_CONSTANT))+perimeter/(height*R(3.)))
    reactance=float((inductance*R(omega))*R(float.fromhex("0x1.12e0be826d695p-30")))
    return R(resistance)/R(cells),reactance


def stamp_memory(memory,address,record):
    """Apply the original two loads/stores to shared guest memory in order.

    A seven-value record supplies frequency, Z endpoints, perimeter step,
    resistance and cell counts. The real store precedes the imaginary load,
    preserving partial writes if the second component faults.
    """
    if len(record)!=7 or any(not isinstance(n,int)or not -65535<=n<=65535 for n in record[5:7]):
        raise ValueError('Invalid via record or cell counts')
    terms=_terms(*record)
    if terms is None:return False
    resistance,reactance=terms
    real=struct.unpack('<d',memory.read(address,8))[0]
    memory.write(address,struct.pack('<d',float(R(real)+resistance)))
    imag=struct.unpack('<d',memory.read(address+8,8))[0]
    memory.write(address+8,struct.pack('<d',float(R(imag)+R(reactance))))
    return True


def stamp(rows):
    """Stamp bounded batches of nine-value via records; return complex cells.

    Records contain frequency, start/end Z, perimeter step, resistance,
    width/thickness counts and the existing matrix real/imaginary values.
    The browser retains 80-bit operations through each original binary64 store.
    The portable path rounds each operation to the same retained significand.
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
        for f,lo,hi,width,resistance,nx,ny,real,imag in chunk:
            terms=_terms(f,lo,hi,width,resistance,nx,ny)
            if terms is None:
                result.append(complex(real,imag));continue
            resistance,reactance=terms
            result.append(complex(float(R(real)+resistance),float(R(imag)+R(reactance))))
    return result

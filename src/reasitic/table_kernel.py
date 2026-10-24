"""Batch transport for retained native spectral table generation."""
from array import array
from decimal import Decimal,localcontext,InvalidOperation,DivisionByZero,Overflow
from .fft import _fft_extended,_fft_spill
try:
    from _reasitic_numeric import spectral_tables as _compiled_tables
    from _reasitic_numeric import layer_coefficients as _compiled_coefficients
except ImportError:
    _compiled_tables=None
    _compiled_coefficients=None


def layer_coefficients(substrate,frequency_hz):
    """Native reader rho spill, retained frequency weight and scalar inverse."""
    with localcontext() as context:
        context.prec=2048
        records=[(_fft_spill(Decimal.from_float(float(layer["rho"]))*10000),float(layer["eps"])) for layer in substrate]
    return _coefficient_records(records,frequency_hz)


def _coefficient_records(records,frequency_hz):
    """Input resistivities have already crossed the native ohm-µm store."""
    with localcontext() as context:
        context.prec=2048
        for signal in (InvalidOperation,DivisionByZero,Overflow):context.traps[signal]=False
        d=Decimal.from_float;e=_fft_extended;spill=_fft_spill
        if _compiled_coefficients is not None and 1<=len(records)<=256:
            data=array("d",[1,len(records),frequency_hz])
            data.extend(v for record in records for v in record);data.extend([0.0]*(2*len(records)))
            if _compiled_coefficients(data):raise ValueError("Invalid layer coefficient configuration")
            return tuple(complex(data[i],data[i+1]) for i in range(3+2*len(records),len(data),2))
        weight=e(e(e(d(float(frequency_hz))*d(float.fromhex("0x1.921fb54442d18p+2")))*d(float.fromhex("0x1.8ebfab864ade4p-44")))*d(1e-4))
        result=[]
        for rho,eps in records:
            real,imag=d(spill(Decimal(1)/d(rho))),d(spill(weight*d(eps)))
            if abs(real)<=abs(imag):
                ratio=e(real/imag);denominator=e(e(e(ratio*ratio)*imag)+imag)
                result.append(complex(spill(e(ratio/denominator)),spill(e(-Decimal(1)/denominator))))
            else:
                ratio=e(imag/real);denominator=e(e(e(ratio*ratio)*real)+real)
                result.append(complex(spill(e(Decimal(1)/denominator)),spill(e(ratio.copy_negate()/denominator))))
        return tuple(result)


def configuration(source,target,nx,ny,width,height,records,coefficients,depths):
    result=array("d",[1,nx,ny,len(records),len(coefficients),source,target,width,height])
    result.extend(v for record in records for v in record)
    result.extend(v for z in coefficients for v in (z.real,z.imag))
    result.extend(depths)
    return result


def generate_tables(source,target,nx,ny,width,height,records,coefficients,depths,*,include_storage=False):
    if _compiled_tables is None or max(len(records),len(coefficients))>256:return None
    config=configuration(source,target,nx,ny,width,height,records,coefficients,depths)
    count=2*nx+2*ny+max((nx+1)*(ny+1),nx*(nx+1)+ny+1)
    output=array("d",[0.0])*(2*count)
    if include_storage:
        scratch=array('d',[0.])*(4*nx);status=_compiled_tables(config,output,scratch)
    else:status=_compiled_tables(config,output)
    if status:raise ValueError("Invalid spectral table configuration")
    values=[complex(output[i],output[i+1]) for i in range(0,len(output),2)]
    result=values[:2*nx],values[2*nx:2*nx+2*ny],values[2*nx+2*ny:]
    if include_storage:return(*result,tuple(complex(scratch[i],scratch[i+1])for i in range(0,len(scratch),2)))
    return result

"""Original x87-to-binary64 spill after every complex accumulation term."""
from array import array
from .retained_scalar import Real
from .numeric_limits import MATRIX_CAPACITY

try:
    from _reasitic_numeric import complex_sum as _compiled_sum
except ImportError:
    _compiled_sum=None


def sum_complex(values):
    data=array('d',(part for value in values for part in(value.real,value.imag)))
    if _compiled_sum is not None and len(data)<=2*MATRIX_CAPACITY*MATRIX_CAPACITY:
        output=array('d',[0.,0.])
        if _compiled_sum(data,output):raise ValueError('Invalid complex sum dimensions')
        return complex(*output)
    real=imag=0.
    for i in range(0,len(data),2):
        real=float(Real(real)+Real.memory_operand(data[i]))
        imag=float(Real(imag)+Real.memory_operand(data[i+1]))
    return complex(real,imag)

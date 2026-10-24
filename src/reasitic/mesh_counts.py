"""Original set_filament_counts retained division, FISTPL and MAXNW rules."""
import math
from .retained_scalar import Real as R

DEFAULT_MAX_WIDTH_CELLS=500


def maximum_width_cells(value=DEFAULT_MAX_WIDTH_CELLS):
    try:number=float(value)
    except (TypeError,ValueError,OverflowError):raise ValueError('MAXNW must be an integer from 1 to 2147483647') from None
    if isinstance(value,bool)or not math.isfinite(number)or not number.is_integer()or not 1<=number<=2147483647:
        raise ValueError('MAXNW must be an integer from 1 to 2147483647')
    return int(number)


def _count(dimension,cell):
    value=R(dimension)/R.memory_operand(cell)+R(.5)
    if value.kind:return -2147483648
    count=int(value.value)
    return count if -2147483648<=count<=2147483647 else -2147483648


def counts(width,thickness,width_cell,thickness_cell,maximum=DEFAULT_MAX_WIDTH_CELLS,nx=0,ny=0):
    w=max(1,_count(width,width_cell));t=max(1,_count(thickness,thickness_cell));w=min(w,maximum)
    return (3,3)if nx==-1 and ny==-1 else(w,t)

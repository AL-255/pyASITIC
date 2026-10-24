"""Original RING/SPIRAL interactive input bounds and double gap stores."""
import math
from .retained_scalar import Real as R


def prepare_interactive(parameters,technology,kind):
    from .paired_geometry import _name
    p=parameters;p['name']=_name(p.get('name','L1'));p['angle']=0.;p['phase']=1
    radius=float(p.get('radius',50));width=float(p.get('width',5));sides=float(p.get('sides',16))
    chip=min(float(technology.chip.get('chipx',512)),float(technology.chip.get('chipy',512)))
    if not math.isfinite(radius)or not 1e-10<=radius<=chip:raise ValueError('Interactive radius exceeds chip bounds or is too small')
    if not math.isfinite(width)or not 1e-10<=width<=radius:raise ValueError('Interactive metal width exceeds radius or is too small')
    if not math.isfinite(sides)or not -(1<<31)<=sides<(1<<31):raise ValueError('Sides exceed the native integer range')
    p['sides']=int(sides)
    if p['sides']<3:raise ValueError('Interactive radial shapes require at least three sides')
    if kind=='polygon':
        spacing=float(p.get('spacing',2))
        if not math.isfinite(spacing)or not 1e-10<=spacing<=radius:raise ValueError('Interactive spacing exceeds radius or is too small')
    return ['You can also use the <Square> command for a square spiral.']if p['sides']==4 else[]


def gap_radians(value):
    """The ring prompt stores wrapped degrees and radians as binary64."""
    value=R(value)
    whole=R(float(math.floor((value/R(360.)).value)))
    degrees=float(value-whole*R(360.))if value>0 else float(whole*R(360.)+value)if value<0 else 0.
    return float(R(degrees)*R(float.fromhex('0x1.1df46a2529d39p-6')))

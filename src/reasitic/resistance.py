"""Original RESIS/RESISHF operation order, retained scalars and explicit spills."""
from array import array
from decimal import Decimal,localcontext
from fractions import Fraction
import math
from .retained_scalar import Real as R

try:
    from _reasitic_numeric import conductor_resistance as _compiled
except ImportError:
    _compiled=None

FREQUENCY_FACTOR=float.fromhex('0x1.921fb544418ecp+4')
UNIT_SCALE=float.fromhex('0x1.a36e2eb1c432dp-14')


def _power(base,exponent):
    """Original integer fast path, otherwise FYL2X/F2XM1/FSCALE; F64 return."""
    base,exponent=R(base),R(exponent)
    if base==0 and exponent>0:return 0.
    if not exponent.kind and -(1<<63)<=exponent.value<(1<<63):
        integer=int(exponent.value)
        if exponent==R(integer):
            remaining=integer&((1<<64)-1);result=R(1.)
            while remaining:
                if remaining&1:result=base*result
                remaining>>=1
                if remaining:base=base*base
            return float(result)
    if base.kind==2 or base<0:return math.nan
    if base==0:logarithm=R(-math.inf)
    elif base.kind:logarithm=base
    else:
        with localcontext()as context:
            context.prec=100
            x=Decimal(base.value.numerator)/Decimal(base.value.denominator)
            logarithm=R._result(Fraction(x.ln()/Decimal(2).ln()))
    power=exponent*logarithm
    if power.kind:return math.nan
    whole=round(power.value)
    if whole>16384:return math.inf
    if whole<-16446:return 0.
    fraction=power-R(whole)
    with localcontext()as context:
        context.prec=100
        x=Decimal(fraction.value.numerator)/Decimal(fraction.value.denominator)
        context.prec=max(100,100-x.adjusted())if x else 100
        part=R._result(Fraction(Decimal(2)**x-1))
    result=part+R(1.)
    if whole<-16382:result*=R(Fraction(2)**(whole+16382));whole=-16382
    if whole>16383:result*=R(2.);whole=16383
    return float(result*R(Fraction(2)**whole))


def _high_factor(u,aspect):
    aspect64=float(aspect)
    first=_power(aspect,float.fromhex('0x1.30a3d70a3d70ap+0'))
    cube=_power(u,3.)
    last=_power(R(aspect64)-R(1.),float.fromhex('0x1.ccccccccccccdp+0'))
    skin=(R(float.fromhex('0x1.b945b6c3760bfp-2'))*u)/(R(float.fromhex('0x1.4fdf3b645a1cbp-5'))*R(first)+R(1.))
    fraction=(R(float.fromhex('0x1.496bb98c7e282p+0'))*u+R(float.fromhex('0x1.1d5cfaacd9e84p+0')))/(R(float.fromhex('0x1.4978d4fdf3b64p+0'))*R(cube)+R(float.fromhex('0x1.3ac710cb295eap+0')))
    return (skin+fraction)+R(float.fromhex('0x1.cac083126e979p-9'))*R(last)


def _records(shape,technology):
    rows=[];metals=len(technology.metals)
    for s in shape.segments:
        via=s.metal>=metals
        m=technology.vias[s.metal-metals]if via else technology.metals[s.metal]
        rows.append([*s.start,*s.end,s.width,0. if via else m.thickness,m.resistance,float(via),s.nx if via else 0,s.ny if via else 0])
    return rows


def _retained(records,frequency=None):
    """Portable raw return for identical consumed inputs; None selects RESIS."""
    result=R(0.)
    for row in records:
        x,y,z,xx,yy,zz,width,thickness,sheet,via,nx,ny=row
        if via:
            count=((int(nx)*int(ny)+(1<<31))%(1<<32))-(1<<31)
            contribution=R(sheet)/R(count)
        else:
            dx,dy,dz=R(xx)-R(x),R(yy)-R(y),R(zz)-R(z)
            dc=(((dz*dz+dy*dy)+dx*dx).sqrt()/R(width))*R(sheet)
            if frequency is None:contribution=dc
            else:
                u=(((((R(frequency)*R(FREQUENCY_FACTOR))*R(1e-9))*R(width))*R(UNIT_SCALE))/R(sheet)).sqrt()
                if u>=R(2.5):factor=_high_factor(u,R(width)/R(thickness))
                else:
                    power=_power(u,R(3.)+(R(.01)*u)*u)
                    factor=R(float.fromhex('0x1.8fc504816f007p-7'))*R(power)+R(1.)
                contribution=factor*dc
        result=contribution+result
        if frequency is not None:result=R(float(result))
    return result


def _evaluate(shape,technology,frequency=None):
    records=_records(shape,technology)
    if _compiled is not None and len(records)<=20000:
        data=array('d',(v for row in records for v in row));output=array('d',[0.])*4
        status=_compiled(data,output,0 if frequency is None else 1,0. if frequency is None else frequency)
        if status:raise ValueError('Invalid conductor resistance configuration')
        return output[0]
    return float(_retained(records,frequency))


def resistance_dc(shape,technology):
    """Original RESIS in ohms, with retained norm, via count and total sum."""
    return _evaluate(shape,technology)


def resistance_hf(shape,technology,frequency_hz):
    """Original RESISHF in ohms; accepts Hz and spills after every segment."""
    if not math.isfinite(frequency_hz)or frequency_hz<0:raise ValueError('Frequency must be finite and nonnegative')
    result=_evaluate(shape,technology,frequency_hz)
    if math.isnan(result)and any(s.metal<len(technology.metals)and s.width<technology.metals[s.metal].thickness for s in shape.segments):
        raise ValueError("ASITIC's high-frequency model requires width ≥ metal thickness")
    return result

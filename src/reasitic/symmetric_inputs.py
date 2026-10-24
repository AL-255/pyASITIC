"""Literal retained symmetric-keyword transition-clearance arithmetic."""
from decimal import Decimal,localcontext
from fractions import Fraction
import math
from .retained_scalar import Real as R
from .precision import _atan2 as decimal_atan2
from .polygon import PI,NATIVE_PI,TRUE_PI


def _decimal(value):return Decimal(value.numerator)/Decimal(value.denominator)


def _atan2(y,x):
    if y.kind==2 or x.kind==2:return R(math.nan)
    if y.kind==1:
        value=TRUE_PI/(4 if x.kind==1 else 2)
        if x.negative:value=TRUE_PI-value
    elif x.kind==1:value=TRUE_PI if x.negative else Decimal(0)
    elif y==0:
        if not x.negative:return R(y)
        value=TRUE_PI
    else:value=decimal_atan2(_decimal(y.value),_decimal(x.value))
    if y.negative and (y.kind or y==0):value=-value
    return R._result(Fraction(value))


def _tan(value):
    if value.kind:return R(math.nan)
    if value==0:return R(value)
    magnitude=abs(value).value;quotient=R._result(magnitude/(NATIVE_PI/2)).value
    n,remainder=divmod(quotient.numerator,quotient.denominator)
    if 2*remainder>quotient.denominator or(2*remainder==quotient.denominator and n&1):n+=1
    reduced=magnitude-n*NATIVE_PI/2
    z=_decimal(reduced/NATIVE_PI)*TRUE_PI;square=-z*z
    sine=st=z;cosine=ct=Decimal(1)
    for i in range(1,65):
        st=st*square/((2*i)*(2*i+1));sine+=st
        ct=ct*square/((2*i-1)*(2*i));cosine+=ct
    answer=-cosine/sine if n&1 else sine/cosine
    if value.negative:answer=-answer
    return R._result(Fraction(answer))


def transition(width,spacing,gap):
    """Original explicit-ILEN rejection and inspectable retained/store boundaries.

    Omitted ILEN bypasses this function. Unordered comparisons do not reject,
    matching the original x87 condition rather than a separate domain guard.
    """
    with localcontext()as context:
        context.prec=100
        w,s,y=R(width),R(spacing),R(gap)
        radius=(s*s+y*y).sqrt();radius64=float(radius)
        angle=_atan2(y/s,R(1.));ratio=w/R(radius64)
        acos=_atan2((R(1.)-ratio*ratio).sqrt(),ratio);acos64=float(acos)
        half=((R(PI)-angle)-R(acos64))*R(.5)
        tangent=_tan(half);tangent64=float(tangent)
        extent=w*R(tangent64);extent=extent+extent;limit=y-R(1e-10)
        return dict(reject=extent>limit,radius=radius,angle=angle,acos=acos,half=half,tangent=tangent,extent=extent,limit=limit,
                    radius64=radius64,acos64=acos64,tangent64=tangent64)


def prepare_interactive(parameters,technology,kind):
    """Finite successful prompt inputs; warning-only lower bounds stay warnings.

    Repeated scans are represented by their final accepted input. Nonzero-SMIN
    symmetric-polygon acquisition currently has no verified successful native
    history; preserve its repeated-prompt failure rather than inventing a limit.
    """
    from .paired_geometry import _name
    from .command_numbers import quantize_turns
    from .polygon import _trig
    p=parameters;warnings=[]
    def number(key,default):
        value=float(p.get(key,default))
        if not math.isfinite(value):raise ValueError(f'{key} must be finite')
        return value
    def bounded(key,minimum,maximum,fallback):
        value=number(key,float(R(fallback)+R(1e-10)))
        if value>maximum:raise ValueError(f'Error: Dimension exceeds maximum dimension of {maximum:5.2f}.')
        if value<minimum:warnings.append(f'Warning:  Dimension less than {minimum:5.2f}')
        p[key]=value;return value
    chipx,chipy=(float(technology.chip.get(k,512))for k in('chipx','chipy'))
    p['name']=_name(p.get('name','L1'));p['angle']=0.;p['phase']=0
    metal=technology.metal_index(p.get('metal',len(technology.metals)-1));record=technology.metals[metal]
    secondary=technology.metal_index(p.get('secondary_metal',metal-1 if metal else 1))
    if secondary==metal:raise ValueError('Interactive symmetric coils require a different transition metal')
    p['metal']=metal;p['secondary_metal']=secondary
    if kind=='symmetric_square':
        dimension=bounded('length',float(R(chipx)/R(float(technology.chip.get('fftx',128)))),chipx,float(R(chipx)*R(.25)))
        sides=4
    else:
        dimension=number('radius',50)
        if not 1e-10<=dimension<=min(chipx,chipy):raise ValueError('Interactive symmetric polygon radius exceeds chip bounds')
        raw=number('sides',16)
        if not -(1<<31)<=raw<(1<<31):raise ValueError('Sides exceed native integer range')
        sides=int(raw)
        if not 3<=sides<=1024:raise ValueError('Sides must be an integer from 3 to 1024')
        sides+=sides&1;p['sides']=sides
    width=number('width',5)
    if not 1e-10<=width<=min(dimension,chipx,chipy):raise ValueError('Interactive metal width exceeds spiral/chip dimensions')
    minimum=record.minimum_spacing;maximum=float(R(dimension)*R(.5))
    if not minimum:
        spacing=number('spacing',2)
        if not 1e-10<=spacing<=min(maximum,chipx,chipy):raise ValueError('Interactive spacing exceeds spiral/chip dimensions')
        gap=bounded('inner_gap',0.,maximum,float(R(width)+R(spacing)))
    else:
        if kind=='symmetric_polygon':raise ValueError('The original interactive symmetric polygon repeats a maximum-zero spacing/transition prompt with nonzero SMIN; use keyword input')
        spacing=bounded('spacing',minimum,maximum,minimum)
        if spacing<=minimum:required=minimum;lower=minimum
        else:
            squared=float(R(spacing)*R(spacing))
            required=float(((R(spacing)+R(width))*R(minimum))/(R(squared)-R(minimum)*R(minimum)).sqrt());lower=float(R(required)-R(1e-10))
        gap=bounded('inner_gap',lower,maximum,required)
        if not required<gap:raise ValueError('Warning:  Need more space for transitions.')
        squared_y=float(R(gap)*R(gap));squared_s=float(R(spacing)*R(spacing))
        hypotenuse=float((R(squared_s)+R(squared_y)).sqrt());pitch=R(spacing)+R(width);pitch_squared=float(pitch*pitch)
        denominator=(R(squared_y)+R(pitch_squared)).sqrt()
        transition_width=float(R(hypotenuse)-((R(spacing)+R(spacing))*R(gap))/denominator)
        if record.minimum_width and transition_width<record.minimum_width:warnings.append('Warning:  Transition metal width less than WMIN specified in technology file')
    p['width']=width;p['spacing']=spacing;p['sides']=sides
    pitch=R(width)+R(spacing)
    if pitch<=0:raise ValueError('Interactive symmetric turn capacity is below one')
    capacity=((R(dimension)+R(spacing))/pitch)*R(.5)if kind=='symmetric_square'else(_trig(R(PI)/R(sides),True)*R(dimension))/pitch
    maximum_turns=math.floor(quantize_turns(capacity,sides,keyword=False).value)
    turns=math.floor(number('turns',2))
    if not 1<=turns<=maximum_turns:raise ValueError(f'Symmetric winding supports 1–{maximum_turns} turns')
    p['turns']=turns
    return warnings,maximum_turns

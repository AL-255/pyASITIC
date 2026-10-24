"""Retained original square/MMSQUARE inner-opening descriptor expansion."""
import math
from .retained_scalar import Real as R
from .command_numbers import quantize_turns


def expand_inner(parameters,*,interactive=False,multimetal=False):
    p=parameters
    def number(key,default):
        value=float(p.get(key,default))
        if not math.isfinite(value):raise ValueError(f'{key} must be finite')
        return value
    width,spacing=number('width',5),number('spacing',2)
    turns=number('turns',2)
    if interactive:
        if turns<1:raise ValueError('Interactive spirals need at least 1 turn')
        turns=float(quantize_turns(turns,4,keyword=False));p['turns']=turns
    x=number('inner_length',0);y=number('inner_height',x)
    if interactive and min(x,y)<=0:raise ValueError('Interactive inner dimensions must be positive')
    n=R(turns);whole=math.floor(n.value)
    if interactive and multimetal:
        # Native interactive MMSQUARE ignores the fractional part here, with
        # distinct associations in the X and Y retained expressions.
        dx=(R(whole)-R(1))*R(spacing)+R(whole)*R(width)
        dy=R(whole)*R(width)+R(spacing)*(R(whole)-R(1))
        p['length']=float(dx+dx+R(x));p['height']=float(dy+dy+R(y));return
    fraction=float(n-R(whole));biased=float(R(fraction)+R(1e-10))
    part=int((R(biased)*R(4)).value);nx=ny=2*whole
    if part==1:ny+=1
    elif part==2:nx+=1;ny+=1
    elif part==3:nx+=1;ny+=2
    if interactive:
        p['length']=float(R(spacing)*R(nx-2)+R(width)*R(nx)+R(x))
        p['height']=float(R(spacing)*R(ny-2)+R(width)*R(ny)+R(y))
    else:
        p['length']=float(R(width)*R(nx)+R(spacing)*R(nx-2)+R(x))
        p['height']=float(R(width)*R(ny)+R(spacing)*R(ny-2)+R(y))

"""ASITIC's QUADPACK infinite-interval rule and adaptive extrapolation.

Direct port of recomp_cpp/src/quadrature.cpp (DQK15I, DQPSRT, DQELG,
DQAGIE). Binary64 stores are explicit; each retained operation rounds to the
original significand. Fourier/oscillatory integration is separate.
"""
from dataclasses import dataclass
from decimal import localcontext
from .retained_scalar import Real as _d
from functools import wraps
import math
import sys

EPSILON=2.0**-52
HUGE=sys.float_info.max
TINY=sys.float_info.min


def _guard(function):
    @wraps(function)
    def call(*args,**kwargs):
        with localcontext() as context:
            context.prec=25
            return function(*args,**kwargs)
    return call


def error_power(value):
    """The original QUADPACK error estimator's 1.5 power."""
    if value==0:
        return 0.0
    if value<0 or math.isnan(value):
        return math.nan
    if math.isinf(value):
        return value
    with localcontext() as context:
        context.prec=25
        v=_d(value)
        return float(v*v.sqrt())


@dataclass
class RuleResult:
    integral:float=0.0
    error:float=0.0
    absolute:float=0.0
    ascendant:float=0.0


@dataclass
class IntegralResult:
    integral:float=0.0
    error:float=0.0
    evaluations:int=0
    status:int=0
    intervals:int=0


def sort_errors(limit,last,maximum,errors,order,rank):
    """Native one-based error ranking; mutates order, returns maximum/error/rank."""
    if last<=2:
        order[0:2]=[1,2]
    else:
        top=errors[maximum-1]
        for _ in range(rank-2,-1,-1):
            if top<=errors[order[rank-2]-1]:
                break
            order[rank-1]=order[rank-2]
            rank-=1
        count=limit-last+3 if last>limit//2+2 else last
        bottom=errors[last-1]
        end=count-1
        next_rank=rank+1
        while next_rank<=end and not top>=errors[order[next_rank-1]-1]:
            order[next_rank-2]=order[next_rank-1]
            next_rank+=1
        if next_rank>end:
            order[count-2],order[count-1]=maximum,last
        else:
            order[next_rank-2]=maximum
            k=end
            while k>=next_rank and not bottom<errors[order[k-1]-1]:
                order[k]=order[k-1]
                k-=1
            order[k]=last
    maximum=order[rank-1]
    return maximum,errors[maximum-1],rank


@_guard
def extrapolate(length,table,history,calls):
    """Native epsilon-table update; mutates table/history and returns state."""
    calls+=1
    error,result=HUGE,table[length-1]
    if length>=3:
        original_length,new_elements=length,(length-1)//2
        table[length+1],table[length-1]=result,HUGE
        k=length
        for i in range(1,new_elements+1):
            e2,e0,e1=map(_d,(table[k+1],table[k-3],table[k-2]))
            delta2,delta3=e2-e1,e1-e0
            d2,d3,err2=float(delta2),float(delta3),float(abs(delta2))
            tol2=float(max(abs(e2),abs(e1))*_d(EPSILON))
            err3,tol3=abs(delta3),max(abs(e1),abs(e0))*_d(EPSILON)
            if not err2>tol2 and not tol3<err3:
                return length,float(e2),max(float(_d(err2)+err3),float(5*_d(EPSILON)*abs(e2))),calls
            e3=_d(table[k-1])
            table[k-1]=float(e1)
            delta1=e1-e3
            err1=float(abs(delta1))
            tol1=max(abs(e3),abs(e1))*_d(EPSILON)
            if tol1>=err1 or err2<=tol2 or err3<=tol3:
                length=2*i-1
                break
            s=(1/_d(d2)+1/delta1)-1/_d(d3)
            if not abs(s*e1)>_d(.0001):
                length=2*i-1
                break
            estimate=e1+1/s
            table[k-1]=float(estimate)
            k-=2
            estimate_error=(abs(estimate-e2)+_d(err2))+err3
            if not estimate_error>_d(error):
                error,result=float(estimate_error),float(estimate)
        if length==50:
            length=49
        at=1 if original_length%2==0 else 0
        for _ in range(new_elements+1):
            table[at]=table[at+2]
            at+=2
        if original_length!=length:
            for i in range(length):
                table[i]=table[original_length-length+i]
        if calls<4:
            history[calls-1]=result
            error=HUGE
        else:
            error=float((abs(_d(result)-_d(history[2]))+abs(_d(result)-_d(history[1])))+abs(_d(result)-_d(history[0])))
            history[:]=[history[1],history[2],result]
    return length,result,max(error,float(5*_d(EPSILON)*abs(_d(result)))),calls


GAUSS=tuple(map(float.fromhex,("0x0p0","0x0p0","0x1.092f69f826d57p-3","0x0p0","0x1.1e6b1713d8644p-2","0x0p0","0x1.86fe74ee32b3dp-2","0x0p0")))
KRONROD=tuple(map(float.fromhex,("0x1.abfd7e03c2fa6p-2","0x1.77c5b67d57470p-6","0x1.026cdaa7b61c4p-4","0x1.ad384a34814c6p-4","0x1.200ed0f46e8c1p-3","0x1.5a1f266e47d5cp-3","0x1.85d6861c80eb1p-3","0x1.a2adbcbec9cd8p-3")))
NODES=tuple(map(float.fromhex,("0x1.ad04f9087090fp-3","0x1.fba009d4d09b1p-1","0x1.e5f178e7c6229p-1","0x1.bacf827b9bb3ep-1","0x1.7ba9f9be3a1d6p-1","0x1.2c13a049dfa24p-1","0x1.9f95df119fd62p-2","0x1.a98b2892e0c77p-3")))


@_guard
def infinite_rule(function,bound,direction,a,b):
    sign=1 if direction>1 else direction
    center,half=float((_d(a)+_d(b))/2),float((_d(b)-_d(a))/2)
    x=float(((1-_d(center))*sign)/_d(center)+_d(bound))
    fc=float(function(x))
    if direction==2:
        fc=float(_d(function(-x))+_d(fc))
    central=(_d(fc)/_d(center))/_d(center)
    central64=float(central)
    g,k=float(central*_d(KRONROD[0])),float(_d(central64)*_d(NODES[0]))
    out=RuleResult(absolute=float(abs(_d(central64)*_d(NODES[0]))))
    left,right=[],[]
    for j in range(1,8):
        offset=_d(half)*_d(NODES[j])
        low=_d(center)-offset
        low64,high=float(low),float(offset+_d(center))
        x=float(((1-low)*sign)/low+_d(bound))
        y=float(((1-_d(high))*sign)/_d(high)+_d(bound))
        f1,f2=float(function(x)),float(function(y))
        if direction==2:
            f1=float(_d(function(-x))+_d(f1))
            f2=float(_d(function(-y))+_d(f2))
        l,r=float((_d(f1)/_d(low64))/_d(low64)),float((_d(f2)/_d(high))/_d(high))
        left.append(l);right.append(r)
        total=_d(l)+_d(r)
        g=float(total*_d(GAUSS[j])+_d(g))
        k=float(total*_d(KRONROD[j])+_d(k))
        out.absolute=float((abs(_d(l))+abs(_d(r)))*_d(KRONROD[j])+_d(out.absolute))
    mean=_d(k)/2
    out.ascendant=float(abs(_d(central64)-mean)*_d(NODES[0]))
    for j in range(1,8):
        out.ascendant=float((abs(_d(left[j-1])-mean)+abs(_d(right[j-1])-mean))*_d(KRONROD[j])+_d(out.ascendant))
    out.integral=float(_d(k)*_d(half))
    asc=_d(half)*_d(out.ascendant)
    out.ascendant,out.absolute=float(asc),float(_d(half)*_d(out.absolute))
    raw=abs((_d(k)-_d(g))*_d(half))
    out.error=float(raw)
    if asc!=0 and raw!=0:
        ratio=float(raw*200/_d(out.ascendant))
        out.error=float(_d(min(error_power(ratio),1.0))*_d(out.ascendant))
    if _d(TINY)/(50*_d(EPSILON))<out.absolute:
        floor=50*_d(EPSILON)*_d(out.absolute)
        if floor>=out.error:
            out.error=float(floor)
    return out


@_guard
def integrate_infinite(function,bound=0.0,direction=1,absolute_tolerance=0.0,relative_tolerance=1e-6,limit=200):
    """Native DQAGIE; nonzero status preserves its partial numerical result.

    Directions -1, 1 and 2 select negative, positive and both infinite tails.
    Evaluation and subdivision counts include unsuccessful convergence paths.
    """
    if direction not in (-1,1,2) or not isinstance(limit,int) or not 1<=limit<=10000:
        raise ValueError("Infinite integration needs direction -1, 1 or 2 and limit 1–10000")
    if not all(math.isfinite(v) for v in (bound,absolute_tolerance,relative_tolerance)):
        raise ValueError("Integration bounds and tolerances must be finite")
    out=IntegralResult()
    if absolute_tolerance<=0 and _d(relative_tolerance)<50*_d(EPSILON):
        out.status=6
        return out
    if direction==2:
        bound=0.0
    left,right,areas,errors,order=([0.0]*limit for _ in range(5))
    right[0]=1.0
    first=infinite_rule(function,bound,direction,0.0,1.0)
    out.integral,out.error,out.intervals=first.integral,first.error,1
    areas[0],errors[0],order[0]=out.integral,out.error,1
    def tolerance(value):
        return float(max(_d(absolute_tolerance),abs(_d(value))*_d(relative_tolerance)))
    def finish():
        out.evaluations=(30*out.intervals-15)*(2 if direction==2 else 1)
        if out.status>2:
            out.status-=1
        return out
    target=tolerance(out.integral)
    if _d(out.error)<=100*_d(EPSILON)*_d(first.absolute) and target<out.error:
        out.status=2
    if limit==1:
        out.status=1
    if out.status or (out.error<=target and first.ascendant!=out.error) or out.error==0:
        return finish()
    table,history=[0.0]*52,[0.0]*3
    table[0]=out.integral
    maximum_error,area,error_sum=out.error,out.integral,out.error
    small=error_large=extrap_target=correction=0.0
    out.error=HUGE
    maximum=rank=1
    extrap_calls=without_improvement=0
    table_length=2
    roundoff1=roundoff2=roundoff3=extrap_status=0
    extrapolating=no_extrapolation=False
    sign=1 if (1-50*_d(EPSILON))*_d(first.absolute)<=abs(_d(out.integral)) else -1
    def sum_intervals():
        out.integral=0.0
        for i in range(out.intervals):
            out.integral=float(_d(out.integral)+_d(areas[i]))
        out.error=error_sum
        return finish()
    for out.intervals in range(2,limit+1):
        at,new_at=maximum-1,out.intervals-1
        aleft,middle,bright=left[at],float((_d(left[at])+_d(right[at]))/2),right[at]
        previous_error=maximum_error
        a=infinite_rule(function,bound,direction,aleft,middle)
        b=infinite_rule(function,bound,direction,middle,bright)
        area12=_d(a.integral)+_d(b.integral)
        error12=float(_d(a.error)+_d(b.error))
        error_sum=float((_d(error_sum)+_d(error12))-_d(maximum_error))
        area=float((_d(area)+area12)-_d(areas[at]))
        if a.error!=a.ascendant and b.error!=b.ascendant:
            if not abs(area12)*_d(1e-5)<abs(_d(areas[at])-area12) and not _d(maximum_error)*_d(.99)>error12:
                if extrapolating:
                    roundoff2+=1
                else:
                    roundoff1+=1
            if out.intervals>10 and maximum_error<error12:
                roundoff3+=1
        areas[at],areas[new_at]=a.integral,b.integral
        target=tolerance(area)
        if roundoff1+roundoff2>9 or roundoff3>19:
            out.status=2
        if roundoff2>4:
            extrap_status=3
        if out.intervals==limit:
            out.status=1
        largest=max(abs(_d(aleft)),abs(_d(bright)))
        if largest<=(1000*_d(TINY)+abs(_d(middle)))*(100*_d(EPSILON)+1):
            out.status=4
        if a.error<b.error:
            left[at],left[new_at],right[new_at]=middle,aleft,middle
            areas[at],areas[new_at]=b.integral,a.integral
            errors[at],errors[new_at]=b.error,a.error
        else:
            left[new_at],right[at],right[new_at]=middle,middle,bright
            errors[at],errors[new_at]=a.error,b.error
        maximum,maximum_error,rank=sort_errors(limit,out.intervals,maximum,errors,order,rank)
        if error_sum<=target:
            return sum_intervals()
        if out.status:
            break
        if out.intervals==2:
            small,extrap_target,error_large,table[1]=.375,target,error_sum,area
        elif not no_extrapolation:
            reduced=_d(error_large)-_d(previous_error)
            error_large=float(reduced)
            if small<abs(_d(middle)-_d(aleft)):
                error_large=float(reduced+_d(error12))
            if not extrapolating:
                if small<abs(_d(right[maximum-1])-_d(left[maximum-1])):
                    continue
                extrapolating,rank=True,2
            if extrap_status!=3 and not error_large<=extrap_target:
                count=limit-out.intervals+3 if out.intervals>limit//2+2 else out.intervals
                found=False
                for _ in range(count-rank,-1,-1):
                    maximum=order[rank-1]
                    maximum_error=errors[maximum-1]
                    if small<abs(_d(right[maximum-1])-_d(left[maximum-1])):
                        found=True
                        break
                    rank+=1
                if found:
                    continue
            table[table_length]=area
            table_length+=1
            table_length,estimate,estimate_error,extrap_calls=extrapolate(table_length,table,history,extrap_calls)
            without_improvement+=1
            if without_improvement>5 and out.error<_d(error_sum)*_d(.001):
                out.status=5
            if not estimate_error>=out.error:
                without_improvement,out.error,out.integral=0,estimate_error,estimate
                correction,extrap_target=error_large,tolerance(estimate)
                if out.error<=extrap_target:
                    break
            if table_length==1:
                no_extrapolation=True
            if out.status==5:
                break
            maximum=order[0]
            maximum_error=errors[maximum-1]
            rank,extrapolating=1,False
            small,error_large=small*.5,error_sum
    if out.error==HUGE:
        return sum_intervals()
    if extrap_status+out.status:
        if extrap_status==3:
            out.error=float(_d(correction)+_d(out.error))
        if out.status==0:
            out.status=3
        if out.integral==0 or area==0:
            if error_sum<out.error:
                return sum_intervals()
            if area==0:
                return finish()
        elif _d(error_sum)/abs(_d(area))<_d(out.error)/abs(_d(out.integral)):
            return sum_intervals()
    if sign==-1 and max(abs(_d(out.integral)),abs(_d(area)))<=_d(.01)*_d(first.absolute):
        return finish()
    ratio=_d(out.integral)/_d(area)
    if ratio<_d(.01) or ratio>100 or abs(_d(area))<error_sum:
        out.status=6
    return finish()

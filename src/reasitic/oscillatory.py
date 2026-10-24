"""ASITIC QUADPACK weighted, Chebyshev and oscillatory integration.

Direct port of recomp_cpp/src/oscillatory.cpp, retaining its explicit binary64
stores and rounding every retained operation to the original significand.
"""
from dataclasses import dataclass,field
import math
from .quadrature import (RuleResult,IntegralResult,_guard,_d,error_power,sort_errors,
                         extrapolate,integrate_infinite,EPSILON,HUGE,TINY)


@_guard
def solve_tridiagonal(c,d,e,rhs):
    """Native DGTSL in-place pivoted tridiagonal solve; returns singular index."""
    n=len(rhs)
    if n<1 or any(len(v)!=n for v in (c,d,e)):
        raise ValueError("Tridiagonal arrays must have the same positive length")
    c[0]=d[0]
    if n>1:
        d[0],e[0],e[n-1]=e[0],0.0,0.0
        for k in range(1,n):
            if not abs(c[k-1])>abs(c[k]):
                for values in (c,d,e,rhs):
                    values[k],values[k-1]=values[k-1],values[k]
            if c[k-1]==0:
                return k
            multiplier=-(_d(c[k])/_d(c[k-1]))
            c[k]=float(multiplier*_d(d[k-1])+_d(d[k]))
            d[k]=float(multiplier*_d(e[k-1])+_d(e[k]))
            e[k]=0.0
            rhs[k]=float(multiplier*_d(rhs[k-1])+_d(rhs[k]))
    if c[n-1]==0:
        return n
    rhs[n-1]=float(_d(rhs[n-1])/_d(c[n-1]))
    if n>1:
        rhs[n-2]=float((_d(rhs[n-2])-_d(d[n-2])*_d(rhs[n-1]))/_d(c[n-2]))
    for k in range(n-3,-1,-1):
        rhs[k]=float(((_d(rhs[k])-_d(d[k])*_d(rhs[k+1]))-_d(e[k])*_d(rhs[k+2]))/_d(c[k]))
    return 0


WG=tuple(map(float.fromhex,("0x0p0","0x1.092f69f826d57p-3","0x1.1e6b1713d8645p-2","0x1.86fe74ee3302ap-2")))
WK=tuple(map(float.fromhex,("0x1.abfd7e03c2fa6p-2","0x1.77c5b67d5746fp-6","0x1.026cdaa7b61c3p-4","0x1.ad384a34814c7p-4","0x1.200ed0f46e8c0p-3","0x1.5a1f266e47d5cp-3","0x1.85d6861c80eb0p-3","0x1.a2adbcbec9cd9p-3")))
XK=tuple(map(float.fromhex,("0x1.ad04f9087090ep-3","0x1.fba009d4d09b1p-1","0x1.e5f178e7c6229p-1","0x1.bacf827b9bb3ep-1","0x1.7ba9f9be3a1d5p-1","0x1.2c13a049dfa24p-1","0x1.9f95df119fd62p-2","0x1.a98b2892e0c78p-3")))
CHEB_COSINES=tuple(map(float.fromhex,("0x1.fb9ea92ec689bp-1","0x1.ee8dd4748bf15p-1","0x1.d906bcf328d46p-1","0x1.bb67ae8584caap-1","0x1.963268b572492p-1","0x1.6a09e667f3bcdp-1","0x1.37af93f9513eap-1","0x1.0000000000000p-1","0x1.87de2a6aea963p-2","0x1.0907dc1930690p-2","0x1.0b5150f6da2d1p-3")))


@_guard
def weighted_rule(function,weight,a,b):
    """Native DQK15W; weight returns the callback's retained scalar value."""
    center,half=float((_d(a)+_d(b))/2),float((_d(b)-_d(a))/2)
    absolute_half=float(abs((_d(b)-_d(a))/2))
    central_f=float(function(center))
    central=_d(weight(center))*_d(central_f)
    central64=float(central)
    g,k=float(central*_d(WK[0])),float(_d(central64)*_d(XK[0]))
    out=RuleResult(absolute=float(abs(_d(central64)*_d(XK[0]))))
    left,right=[0.0]*7,[0.0]*7
    for phase in range(2):
        for i in range(1,4 if phase==0 else 5):
            j=2*i-(0 if phase==0 else 1)
            offset=_d(half)*_d(XK[j])
            x,y=float(_d(center)-offset),float(offset+_d(center))
            f1=float(function(x))
            weighted1=float(_d(weight(x))*_d(f1))
            f2=float(function(y))
            weighted2=_d(f2)*_d(weight(y))
            left[j-1],right[j-1]=weighted1,float(weighted2)
            total=_d(weighted1)+weighted2
            if phase==0:
                g=float(total*_d(WG[i])+_d(g))
            k=float(total*_d(WK[j])+_d(k))
            out.absolute=float((abs(weighted2)+abs(_d(weighted1)))*_d(WK[j])+_d(out.absolute))
    mean=_d(k)/2
    out.ascendant=float(abs(_d(central64)-mean)*_d(XK[0]))
    for j in range(1,8):
        out.ascendant=float((abs(_d(left[j-1])-mean)+abs(_d(right[j-1])-mean))*_d(WK[j])+_d(out.ascendant))
    out.integral=float(_d(k)*_d(half))
    out.absolute=float(_d(absolute_half)*_d(out.absolute))
    asc=_d(absolute_half)*_d(out.ascendant)
    out.ascendant=float(asc)
    raw=abs((_d(k)-_d(g))*_d(half))
    out.error=float(raw)
    if asc!=0 and raw!=0:
        power=error_power(float(raw*200/_d(out.ascendant)))
        out.error=float(_d(min(power,1.0))*_d(out.ascendant))
    if _d(TINY)/(50*_d(EPSILON))<out.absolute:
        floor=50*_d(EPSILON)*_d(out.absolute)
        if floor>=out.error:
            out.error=float(floor)
    return out


@_guard
def chebyshev_transform(samples,cosines=CHEB_COSINES):
    """Native DQCHEB butterfly; endpoints are pre-halved, samples overwritten."""
    if len(samples)!=25 or len(cosines)!=11:
        raise ValueError("Chebyshev transform needs 25 samples and 11 cosines")
    c=list(map(_d,cosines));f=samples
    y,z,v=[0.0]*13,[0.0]*25,[0.0]*12
    for i in range(12):
        v[i]=float(_d(f[i])-_d(f[24-i]))
        f[i]=float(_d(f[i])+_d(f[24-i]))
    base=_d(v[0])-_d(v[8])
    t=float(((_d(v[2])-_d(v[6]))-_d(v[10]))*c[5])
    y[3],y[9]=float(base+_d(t)),float(base-_d(t))
    u,w=float((_d(v[1])-_d(v[7]))-_d(v[9])),float((_d(v[3])-_d(v[5]))-_d(v[11]))
    def rounded_pair(a,b,center,r):
        z[a],z[b]=float(r+_d(y[center])),float(_d(y[center])-_d(float(r)))
    def extended_pair(a,b,center,r):
        z[a],z[b]=float(r+_d(y[center])),float(_d(y[center])-r)
    rounded_pair(3,21,3,_d(u)*c[2]+_d(w)*c[8])
    rounded_pair(9,15,9,_d(u)*c[8]-_d(w)*c[2])
    p,q,r=float(c[3]*_d(v[4])),float(c[7]*_d(v[8])),float(c[5]*_d(v[6]))
    a=float((_d(p)+_d(v[0]))+_d(q))
    b=float(c[9]*_d(v[10])+_d(float(c[1]*_d(v[2])+_d(r))))
    y[1],y[11]=float(_d(a)+_d(b)),float(_d(a)-_d(b))
    s=float(c[0]*_d(v[1])+c[2]*_d(v[3]))
    for index,coefficient in ((5,4),(7,6),(9,8)):
        s=float(c[coefficient]*_d(v[index])+_d(s))
    rounded_pair(1,23,1,c[10]*_d(v[11])+_d(s))
    s=float(c[10]*_d(v[1])-c[8]*_d(v[3]))
    s=float(c[6]*_d(v[5])+_d(s))
    s=float(_d(s)-c[4]*_d(v[7]))
    s=float(c[2]*_d(v[9])+_d(s))
    rounded_pair(11,13,11,_d(s)-c[0]*_d(v[11]))
    a2=float((_d(v[0])-_d(p))+_d(q))
    b2,b3=float(c[9]*_d(v[2])-_d(r)),float(c[1]*_d(v[10]))
    b4=_d(b2)+_d(b3)
    y[5],y[7]=float(_d(a2)+b4),float(_d(a2)-b4)
    s=float(c[4]*_d(v[1])-c[8]*_d(v[3]))
    s=float(_d(s)-c[0]*_d(v[5]))
    s=float(_d(s)-c[10]*_d(v[7]))
    s=float(c[2]*_d(v[9])+_d(s))
    rounded_pair(5,19,5,c[6]*_d(v[11])+_d(s))
    value=((((c[6]*_d(v[1])-c[2]*_d(v[3]))-c[10]*_d(v[5]))+c[0]*_d(v[7]))-c[8]*_d(v[9]))-c[4]*_d(v[11])
    extended_pair(7,17,7,value)
    for i in range(6):
        v[i]=float(_d(f[i])-_d(f[12-i]))
        f[i]=float(_d(f[i])+_d(f[12-i]))
    a3,b5=c[7]*_d(v[4])+_d(v[0]),c[3]*_d(v[2])
    y[2],y[10],y[6]=float(a3+b5),float(_d(float(a3))-b5),float(_d(v[0])-_d(v[4]))
    s=float(c[1]*_d(v[1])+c[5]*_d(v[3]))
    rounded_pair(2,22,2,c[9]*_d(v[5])+_d(s))
    rounded_pair(6,18,6,((_d(v[1])-_d(v[3]))-_d(v[5]))*c[5])
    extended_pair(10,14,10,(c[9]*_d(v[1])-c[5]*_d(v[3]))+c[1]*_d(v[5]))
    for i in range(3):
        v[i]=float(_d(f[i])-_d(f[6-i]))
        f[i]=float(_d(f[i])+_d(f[6-i]))
    y[4],y[8]=float(c[7]*_d(v[2])+_d(v[0])),float(_d(f[0])-c[7]*_d(f[2]))
    extended_pair(4,20,4,c[3]*_d(v[1]))
    extended_pair(8,16,8,c[7]*_d(f[1])-_d(f[3]))
    y[0]=float(_d(f[0])+_d(f[2]))
    extended_pair(0,24,0,_d(f[1])+_d(f[3]))
    y[12]=z[12]=float(_d(v[0])-_d(v[2]))
    for i in range(1,12):
        y[i]=float(_d(y[i])*_d(float.fromhex("0x1.5555555555555p-3")))
    for i in (0,12):
        y[i]=float(_d(y[i])*_d(float.fromhex("0x1.5555555555555p-4")))
    for i in range(1,24):
        z[i]=float(_d(z[i])*_d(float.fromhex("0x1.5555555555555p-4")))
    for i in (0,24):
        z[i]=float(_d(z[i])*_d(float.fromhex("0x1.5555555555555p-5")))
    return y,z


class MomentCache:
    def __init__(self,rows=50):
        if not isinstance(rows,int) or not 1<=rows<=1000:
            raise ValueError("Moment cache needs 1–1000 rows")
        self.rows,self.computed=rows,0
        self.data=[[0.0]*25 for _ in range(rows)]


@_guard
def compute_moments(par,row,cache):
    squared,plus=float(_d(par)*_d(par)),float(_d(par)*_d(par)+2)
    sine,cosine=math.sin(par),math.cos(par)
    p,sq,pl,sn,cs=map(_d,(par,squared,plus,sine,cosine))
    v,diagonal,lower,upper=[0.0]*28,[0.0]*25,[0.0]*25,[0.0]*25
    v[0]=float((sn+sn)/p)
    eight_cos=float(cs*8)
    v[1]=float((((sq+sq)-8)*sn/p+_d(eight_cos))/sq)
    polynomial=(sq-80)*sq+192
    v[2]=float(((polynomial+polynomial)*sn/p+(sq-12)*32*cs)/(sq*sq))
    ac=p*24*sn
    if abs(par)>24:
        for k in range(3,13):
            n=_d(2*k-2);nsq=n*n;difference=(pl-nsq)-nsq
            v[k]=float(((((difference+difference)*_d(v[k-1])-_d(eight_cos))*(nsq-4)+ac)-(n+1)*sq*(n+2)*_d(v[k-2]))/((n-2)*(n-1)*sq))
    else:
        for i in range(25):
            n=_d(6+2*i);nsq=n*n;difference=nsq-4
            diagonal[i]=float(-((difference+difference)*((pl-nsq)-nsq)))
            v[i+3]=float(ac-difference*_d(eight_cos))
            if i<24:
                upper[i]=float((n-2)*(n-1)*sq)
                lower[i+1]=float((n+4)*(n+3)*sq)
        v[3]=float(_d(v[3])-(56*sq)*_d(v[2]))
        n=_d(54);nsq=n*n;b=p*sn
        asymptote=((((b*15+((sq*210-1)*cs-(sq*105-63)*b)/nsq-(1-sq*15)*cs)/nsq-cs)+b*3)/nsq-cs)/nsq
        v[27]=float(_d(v[27])-(n-2)*(n-1)*(asymptote+asymptote)*sq)
        rhs=v[3:28]
        solve_tridiagonal(lower,diagonal,upper,rhs)
        v[3:28]=rhs
    for i in range(13):
        cache.data[row][2*i]=v[i]
    v[0]=float(((sn-p*cs)*2)/sq)
    div48=48/sq
    v[1]=float(((18-div48)*sn)/sq+((div48-2)*cs)/p)
    ac_odd=float(-(p*24*cs))
    eight_sine=-(sn*8)
    if abs(par)>24:
        for k in range(2,12):
            n=_d(2*k-1);nsq=n*n;difference=(pl-nsq)-nsq
            v[k]=float(((((difference+difference)*_d(v[k-1])+eight_sine)*(nsq-4)+_d(ac_odd))-(n+1)*sq*(n+2)*_d(v[k-2]))/((n-2)*(n-1)*sq))
    else:
        for i in range(25):
            n=_d(5+2*i);nsq=n*n;difference=nsq-4
            diagonal[i]=float(-(((pl-nsq)-nsq)*(difference+difference)))
            v[i+2]=float(difference*eight_sine+_d(ac_odd))
            if i<24:
                upper[i]=float((n-2)*(n-1)*sq)
                lower[i+1]=float((n+4)*(n+3)*sq)
        v[2]=float(_d(v[2])-(42*sq)*_d(v[1]))
        n=_d(53);nsq=n*n;b=p*cs
        asymptote=((((sq*15-1)*sn+((sq*210-1)*sn+(sq*105-63)*b)/nsq-b*15)/nsq-b*3-sn)/nsq-sn)/nsq
        v[26]=float(_d(v[26])-(n-2)*(n-1)*(asymptote+asymptote)*sq)
        rhs=v[2:27]
        solve_tridiagonal(lower,diagonal,upper,rhs)
        v[2:27]=rhs
    for i in range(12):
        cache.data[row][2*i+1]=v[i]


@dataclass
class OscillatoryRuleResult:
    value:RuleResult
    evaluations:int


@_guard
def oscillatory_rule(function,a,b,frequency,selector,level,reuse,cache):
    center,half=float((_d(b)+_d(a))/2),float((_d(b)-_d(a))/2)
    extended_par=((_d(b)-_d(a))/2)*_d(frequency)
    par=float(extended_par)
    if not abs(extended_par)>2:
        def weight(x):
            argument=float(_d(frequency)*_d(x))
            return math.sin(argument) if selector==2 else math.cos(argument)
        return OscillatoryRuleResult(weighted_rule(function,weight,a,b),15)
    argument=float(_d(center)*_d(frequency))
    cc,ss=float(_d(math.cos(argument))*_d(half)),float(_d(math.sin(argument))*_d(half))
    row=cache.computed
    if level>=cache.computed and not reuse:
        compute_moments(par,row,cache)
    if level<cache.computed:
        row=level
    if cache.computed<cache.rows-1 and level>=cache.computed:
        cache.computed+=1
    samples=[0.0]*25
    x=float(_d(half)+_d(center));samples[0]=float(_d(function(x))/2)
    samples[12]=float(function(center))
    x=float(_d(center)-_d(half));samples[24]=float(_d(function(x))/2)
    for i in range(11):
        x=float(_d(half)*_d(CHEB_COSINES[i])+_d(center));samples[i+1]=float(function(x))
        x=float(_d(center)-_d(half)*_d(CHEB_COSINES[i]));samples[23-i]=float(function(x))
    c12,c24=chebyshev_transform(samples)
    moment=cache.data[row]
    even12,odd12=_d(c12[12])*_d(moment[12]),_d(0)
    for j in range(11,0,-2):
        even12+=_d(c12[j-1])*_d(moment[j-1]);odd12+=_d(c12[j])*_d(moment[j])
    even24,odd24=_d(c24[24])*_d(moment[24]),_d(0)
    out=RuleResult(absolute=abs(c24[24]))
    for j in range(23,0,-2):
        even24+=_d(c24[j-1])*_d(moment[j-1]);odd24+=_d(c24[j])*_d(moment[j])
        # Native RESABS is overwritten, rather than accumulated, each time.
        out.absolute=float(abs(_d(c24[j]))+abs(_d(c24[j-1])))
    out.absolute=float(abs(_d(half))*_d(out.absolute))
    out.ascendant=HUGE
    even_error,odd_error=abs(even24-even12),abs(odd24-odd12)
    if selector==2:
        out.integral=float(_d(cc)*odd24+_d(ss)*even24)
        out.error=float(abs(_d(ss)*even_error)+abs(_d(cc)*odd_error))
    else:
        out.integral=float(_d(cc)*even24-_d(ss)*odd24)
        out.error=float(abs(_d(ss)*odd_error)+abs(_d(cc)*even_error))
    return OscillatoryRuleResult(out,25)


@_guard
def integrate_oscillatory(function,a,b,frequency,selector=1,absolute_tolerance=0.0,relative_tolerance=1e-6,
                          *,sequence=1,limit=200,cache=None):
    """Native DQAWOE; sequence/cache permit Fourier-cycle moment reuse."""
    if not isinstance(limit,int) or not 1<=limit<=10000:
        raise ValueError("Oscillatory integration needs limit 1–10000")
    if not all(math.isfinite(v) for v in (a,b,frequency,absolute_tolerance,relative_tolerance)):
        raise ValueError("Oscillatory bounds, frequency and tolerances must be finite")
    cache=MomentCache() if cache is None else cache
    out=IntegralResult()
    if selector not in (1,2) or (absolute_tolerance<=0 and _d(relative_tolerance)<50*_d(EPSILON)) or sequence<1:
        out.status=6
        return out
    omega=abs(frequency)
    if sequence<2:
        cache.computed=0
    left,right,areas,errors=([0.0]*limit for _ in range(4))
    order,levels=[0]*limit,[0]*limit
    left[0],right[0]=a,b
    first_rule=oscillatory_rule(function,a,b,omega,selector,0,False,cache)
    first=first_rule.value
    out.integral,out.error,out.evaluations=first.integral,first.error,first_rule.evaluations
    def tolerance(value):
        return float(max(_d(absolute_tolerance),abs(_d(value))*_d(relative_tolerance)))
    def sign_result():
        if selector==2 and frequency<0:
            out.integral=-out.integral
        return out
    def finish():
        if out.status>2:
            out.status-=1
        return sign_result()
    target=tolerance(out.integral)
    areas[0],errors[0],order[0]=out.integral,out.error,1
    if _d(out.error)<=100*_d(EPSILON)*_d(first.absolute) and target<out.error:
        out.status=2
    if limit==1:
        out.status=1
    # Native LAST remains zero on every initial-return path.
    if out.status or out.error<=target:
        return sign_result()
    table,history=[0.0]*52,[0.0]*3
    maximum_error,area,error_sum=out.error,out.integral,out.error
    small=float(abs(_d(b)-_d(a))*_d(.75))
    error_large=extrap_target=correction=0.0
    out.error=HUGE
    maximum=rank=1
    extrap_calls=without_improvement=table_length=0
    roundoff1=roundoff2=roundoff3=extrap_status=0
    extrapolating=no_extrapolation=False
    span=abs(_d(b)-_d(a))
    eligible=not 2<span/2*_d(omega)
    if eligible:
        table[table_length]=out.integral
        table_length+=1
    eligible=span/4*_d(omega)<=2 or eligible
    sign=1 if (1-50*_d(EPSILON))*_d(first.absolute)<=abs(_d(out.integral)) else -1
    def sum_intervals():
        out.integral=0.0
        for i in range(out.intervals):
            out.integral=float(_d(out.integral)+_d(areas[i]))
        out.error=error_sum
        return finish()
    for out.intervals in range(2,limit+1):
        at,new_at=maximum-1,out.intervals-1
        level=levels[at]+1
        aleft,middle,bright=left[at],float((_d(left[at])+_d(right[at]))/2),right[at]
        previous_error=maximum_error
        rule_a=oscillatory_rule(function,aleft,middle,omega,selector,level,False,cache)
        out.evaluations+=rule_a.evaluations
        rule_b=oscillatory_rule(function,middle,bright,omega,selector,level,True,cache)
        out.evaluations+=rule_b.evaluations
        va,vb=rule_a.value,rule_b.value
        area12=_d(va.integral)+_d(vb.integral)
        error12=float(_d(va.error)+_d(vb.error))
        error_sum=float((_d(error_sum)+_d(error12))-_d(maximum_error))
        area=float((_d(area)+area12)-_d(areas[at]))
        if va.error!=va.ascendant and vb.error!=vb.ascendant:
            if not abs(area12)*_d(1e-5)<abs(_d(areas[at])-area12) and not _d(maximum_error)*_d(.99)>error12:
                if extrapolating:
                    roundoff2+=1
                else:
                    roundoff1+=1
            if out.intervals>10 and maximum_error<error12:
                roundoff3+=1
        areas[at],areas[new_at]=va.integral,vb.integral
        levels[at]=levels[new_at]=level
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
        if va.error<vb.error:
            left[at],left[new_at],right[new_at]=middle,aleft,middle
            areas[at],areas[new_at]=vb.integral,va.integral
            errors[at],errors[new_at]=vb.error,va.error
        else:
            left[new_at],right[at],right[new_at]=middle,middle,bright
            errors[at],errors[new_at]=va.error,vb.error
        maximum,maximum_error,rank=sort_errors(limit,out.intervals,maximum,errors,order,rank)
        if error_sum<=target:
            return sum_intervals()
        if out.status:
            break
        if out.intervals==2 and eligible:
            small*=.5
            table[table_length]=area
            table_length+=1
            extrap_target,error_large=target,error_sum
            continue
        if no_extrapolation:
            continue
        if eligible:
            reduced=_d(error_large)-_d(previous_error)
            error_large=float(reduced)
            if small<abs(_d(middle)-_d(aleft)):
                error_large=float(reduced+_d(error12))
        if not extrapolating:
            width=abs(_d(right[maximum-1])-_d(left[maximum-1]))
            if width>small:
                continue
            if not eligible:
                small*=.5
                if width/4*_d(omega)<=2:
                    eligible,extrap_target,error_large=True,target,error_sum
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
        if table_length>2:
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
    if out.error==HUGE or extrap_calls==0:
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
    if ratio<_d(.01) or ratio>100 or abs(_d(area))<=error_sum:
        out.status=6
    return finish()


@dataclass
class FourierResult:
    integral:float=0.0
    error:float=0.0
    evaluations:int=0
    status:int=0
    cycles:int=0
    cycle_integrals:list=field(default_factory=list)
    cycle_errors:list=field(default_factory=list)
    cycle_statuses:list=field(default_factory=list)
    history:list=field(default_factory=list)


@_guard
def integrate_fourier(function,start,frequency,selector=1,absolute_tolerance=1e-2,*,limit=500,
                      cycle_limit=1000,moment_rows=50,history=None):
    """Native DQAWFE with its cycle-tail selection and partial-result statuses."""
    if not isinstance(limit,int) or not 1<=limit<=10000 or not isinstance(cycle_limit,int) or not 1<=cycle_limit<=10000:
        raise ValueError("Fourier workspace limits must be integers from 1 to 10000")
    if not all(math.isfinite(v) for v in (start,frequency,absolute_tolerance)):
        raise ValueError("Fourier start, frequency and tolerance must be finite")
    history=[0.0]*3 if history is None else history
    if len(history)!=3:
        raise ValueError("Fourier extrapolation history needs three cells")
    cache=MomentCache(moment_rows)
    out=FourierResult()
    integrals,errors,statuses=[0.0]*cycle_limit,[0.0]*cycle_limit,[0]*cycle_limit
    def finish():
        out.cycle_integrals=integrals[:out.cycles]
        out.cycle_errors=errors[:out.cycles]
        out.cycle_statuses=statuses[:out.cycles]
        out.history=history.copy()
        return out
    if selector not in (1,2) or absolute_tolerance<=0 or cycle_limit<3:
        out.status=6
        return finish()
    if frequency==0:
        if selector==1:
            value=integrate_infinite(function,0.0,1,absolute_tolerance,0.0,limit)
            out.integral,out.error,out.evaluations,out.status=value.integral,value.error,value.evaluations,value.status
        integrals[0],errors[0],statuses[0]=out.integral,out.error,out.status
        out.cycles=1
        return finish()
    absolute_frequency=abs(_d(frequency))
    truncated=math.trunc(abs(frequency)) if abs(frequency)<2**31 else -2**31
    odd=(2*truncated+1)&0xffffffff
    if odd>=2**31:
        odd-=2**32
    cycle_length=float((_d(odd)*_d(float.fromhex("0x1.921fb54442d18p+1")))/absolute_frequency)
    decay=float.fromhex("0x1.ccccccccccccdp-1")
    one_minus=float(1-_d(decay))
    eps=absolute_tolerance
    if _d(TINY)/_d(one_minus)<eps:
        eps=float(_d(one_minus)*_d(eps))
    initial_eps=eps
    factor,correction,error_sum,tail=1.0,0.0,0.0,0.0
    left,right=start,float(_d(cycle_length)+_d(start))
    table=[0.0]*52
    table_length=previous_length=extrap_calls=without_improvement=0
    def direct_sum():
        # The native jump can occur before appending the current cycle.
        out.integral=table[table_length-1]
        out.error=float(_d(error_sum)+_d(tail))
        return finish()
    for out.cycles in range(1,cycle_limit+1):
        at=out.cycles-1
        tolerance=float(_d(eps)*_d(factor))
        value=integrate_oscillatory(function,left,right,frequency,selector,tolerance,0.0,
                                    sequence=out.cycles,limit=limit,cache=cache)
        integrals[at],errors[at],statuses[at]=value.integral,value.error,value.status
        out.evaluations+=value.evaluations
        factor=float(_d(factor)*_d(decay))
        updated_sum=_d(error_sum)+_d(value.error)
        error_sum=float(updated_sum)
        tail=float(abs(_d(value.integral))*50)
        if updated_sum+_d(tail)<=absolute_tolerance and out.cycles>5:
            return direct_sum()
        if not correction>=value.error:
            correction=value.error
        if value.status:
            updated_eps=_d(correction)*_d(one_minus)
            eps=float(max(_d(initial_eps),updated_eps))
            out.status=7
        if out.status==7 and _d(error_sum)+_d(tail)<=_d(correction)*10 and out.cycles>5:
            return direct_sum()
        table_length+=1
        if out.cycles<2:
            table[0]=value.integral
        else:
            table[table_length-1]=float(_d(table[previous_length-1])+_d(value.integral))
            if out.cycles!=2:
                if out.cycles==cycle_limit:
                    out.status=1
                table_length,estimate,estimate_error,extrap_calls=extrapolate(table_length,table,history,extrap_calls)
                without_improvement+=1
                if without_improvement>14 and out.error<=(_d(error_sum)+_d(tail))*_d(.001):
                    out.status=4
                if estimate_error<=out.error or out.cycles==3:
                    out.error,out.integral,without_improvement=estimate_error,estimate,0
                    if _d(correction)*10+_d(out.error)<=absolute_tolerance or (estimate_error<=absolute_tolerance and absolute_tolerance<=_d(correction)*10):
                        break
                if out.status not in (0,7):
                    break
        previous_length=table_length
        left,right=right,float(_d(cycle_length)+_d(right))
    out.error=float(_d(correction)*10+_d(out.error))
    if out.status==0:
        return finish()
    if out.integral==0 or table[table_length-1]==0:
        if error_sum<out.error:
            return direct_sum()
        if table[table_length-1]==0:
            return finish()
    if (_d(error_sum)+_d(tail))/abs(_d(table[table_length-1]))<_d(out.error)/abs(_d(out.integral)):
        return direct_sum()
    if out.status>0 and out.status!=7:
        out.error=float(_d(tail)+_d(out.error))
    return finish()

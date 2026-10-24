"""Retained native parallel mutual and cross-section separation kernels."""
from decimal import Decimal,localcontext
from .retained_scalar import Real as R
from .impedance import _log
from fractions import Fraction
from functools import lru_cache
from .green import _guard
from .inductance import _round_extended
from .precision import _atan,_decimal

EPS=R(float.fromhex("0x1.b7cdfd9d7bdbbp-34"))
def _d(value):return R(value)


def _atan_native(value):
    value=value.value if isinstance(value,R)else _round_extended(Fraction(value))
    with localcontext() as context:
        context.prec=44
        return R._result(Fraction(_atan(_decimal(value))))


def _exp(value):
    if value.kind:return R(value)if value.kind==2 or not value.negative else R(0.)
    exponent=value*R._result(Fraction(0xb8aa3b295c17f0bc,1<<63))
    if exponent>16385.:return R(float('inf'))
    if exponent<-16447.:return R(0.)
    whole=round(exponent.value);part=exponent-R(whole)
    with localcontext() as context:
        context.prec=100
        p=Decimal(part.value.numerator)/Decimal(part.value.denominator)
        remainder=R._result(Fraction(Decimal(2)**p-1))
    return (remainder+R(1.))*R(Fraction(2)**whole)


@lru_cache(maxsize=8192)
@_guard
def cross_section_log_integral(xd,yd):
    x,y=_d(xd),_d(yd);x2,y2=x*x,y*y;angular=R(0.)
    if abs(x)>EPS and abs(y)>EPS:
        logarithmic=(_log(x2+y2)*((x2*x2-x2*6*y2)+y2*y2))/24
        a,b=_atan_native(y/x),_atan_native(x/y)
        angular=(-x*y*(x2*a+y2*b))/3
    else:
        square=x2 if abs(x)>EPS else y2
        logarithmic=(_log(square)*(square*square))/24 if abs(x)>EPS or abs(y)>EPS else R(0.)
    return logarithmic+angular


@lru_cache(maxsize=4096)
@_guard
def effective_separation(w1,w2,t1,t2,dx,dy):
    x,y=_d(dx),_d(dy);r=(x*x+y*y).sqrt();ts=_d(t1)+_d(t2);ws=_d(w1)+_d(w2)
    if ts*R(1.5)<r and ws*R(1.5)<r:return r
    wd,td=_d(w1)-_d(w2),_d(t1)-_d(t2)
    xs=[float(wd/2-x),float(-ws/2-x),float(ws/2-x),float(-wd/2-x)]
    ys=[float(td/2-y),float(ts/2-y),float(-ts/2-y),float(-td/2-y)]
    rows=[];last=R(0.)
    for i,x in enumerate(xs):
        v0,v1,v2=(_d(float(cross_section_log_integral(x,y))) for y in ys[:3])
        v3=cross_section_log_integral(x,ys[3])
        if i==0:rows.append(float((v0-v1-v2)+v3))
        elif i==1:rows.append(float(((-v0+v1)+v2)-_d(float(v3))))
        elif i==2:rows.append(float(((-v0+v1)+v2)-v3))
        else:last=((v0-v1)-v2)+_d(float(v3))
    total=((_d(rows[0])+_d(rows[1]))+_d(rows[2]))+last
    volume=((_d(w1)*_d(w2))*_d(t1))*_d(t2)
    offset=_d(float.fromhex("0x1.0aaaaaaaaaaabp+1"))
    return _d(float(_exp((total*R(-.5))/volume-offset)))


@lru_cache(maxsize=8192)
@_guard
def segment_self_inductance(length,radius):
    l=_d(length)
    if l<EPS:return R(0.)
    a=l/_d(radius);inv=1/a
    term=(_log((a*a+1).sqrt()+a)-(inv*inv+1).sqrt())+inv
    return (l+l)*term


@_guard
def parallel_segment_mutual(a,b,sep):
    """Return native status/value; rejected inputs leave the output undefined."""
    alo,ahi,bhi=a[0],a[3],b[3];ady=_d(a[4])-_d(a[1]);bdy=_d(b[4])-_d(b[1])
    alen=_d(ahi)-_d(alo);blo=_d(b[0]);bdx=_d(bhi)-blo;blen=float(bdx)
    abs_adx=float(abs(alen))
    if _d(float((_d(abs_adx)*_d(abs_adx)+abs(ady)*abs(ady)).sqrt()))<EPS or (abs(bdy)*abs(bdy)+abs(bdx)*abs(bdx)).sqrt()<EPS:return -1,None
    if abs(ady*_d(float(bdy))+alen*_d(blen))<EPS:return 0,0.0
    if ahi<alo:alen=_d(alo)-_d(ahi);ahi,alo=alo,ahi
    if _d(bhi)<blo:blo=_d(bhi);blen=float(_d(b[0])-blo);bhi=b[0]
    def classify(x):return 2 if blo<=_d(x)<=_d(bhi) else 1 if blo<=_d(x) else 0
    kind=classify(ahi)+3*classify(alo);ysep=abs(_d(a[1])-_d(b[1]))
    if EPS<_d(sep):ysep=R(0.) if abs(ysep-_d(sep))<EPS else (_d(sep)*_d(sep)+ysep*ysep).sqrt()
    radius=float(effective_separation(a[6],b[6],a[7],b[7],float(ysep),sep))
    def self(length):return segment_self_inductance(float(length),radius)
    def rounded(length):return _d(float(self(length)))
    def adjacent():
        total=alen+_d(blen)
        return _log(total/_d(blen))*_d(blen)+alen*_log(total/alen)
    def collinear(gap):
        total=(alen+_d(blen))+_d(gap);p=_d(gap)+alen;q=_d(blen)+_d(gap)
        return _log(_d(gap))*_d(gap)+((_log(total)*_d(float(total))-p*_log(p))-q*_log(q))
    def three(gap):return ((rounded(alen)+rounded(blen))-self(gap))/2
    if kind in (0,4):
        raw_gap=blo-_d(ahi) if kind==0 else _d(alo)-_d(bhi);gap=float(raw_gap)
        if ysep<EPS and raw_gap<EPS:value=adjacent()
        elif ysep<EPS:value=collinear(gap)
        elif _d(gap)>=EPS:
            s0=rounded((alen+_d(blen))+_d(gap));s1=rounded(gap);s2=rounded(alen+_d(gap));s3=self(_d(blen)+_d(gap))
            value=((s0+s1)-(s2+_d(float(s3))))/2 if kind==0 else (((s0+s1)-s2)-s3)/2
        else:value=((rounded(alen+_d(blen))-rounded(alen))-self(blen))/2
    elif kind in (2,7):
        raw_overlap=_d(ahi)-blo if kind==2 else _d(bhi)-_d(alo);overlap=float(raw_overlap)
        if raw_overlap<EPS and ysep<EPS:value=adjacent()
        elif _d(overlap)>=EPS:
            if ysep<EPS and (kind==2 or _d(sep)<EPS):return -1,None
            value=(((rounded((alen+_d(blen))-_d(overlap))+rounded(overlap))-rounded(alen-_d(overlap)))-self(_d(blen)-_d(overlap)))/2
        else:value=((rounded(alen+_d(blen))-rounded(alen))-self(blen))/2
    elif kind in (1,8):
        raw_left=blo-_d(alo) if kind==1 else _d(alo)-blo;raw_right=_d(ahi)-_d(bhi) if kind==1 else _d(bhi)-_d(ahi)
        left,right=float(raw_left),float(raw_right)
        if raw_left<EPS and raw_right<EPS:value=self(alen if kind==1 else blen)
        elif _d(left)>=EPS and _d(right)>=EPS:
            inside=_d(blen) if kind==1 else alen
            value=(((rounded(inside+_d(left))+rounded(inside+_d(right)))-rounded(left))-self(right))/2
        else:value=three(left if _d(left)>=EPS else right)
    else:return -1,None
    return 0,float(value)

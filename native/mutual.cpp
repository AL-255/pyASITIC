// Retained native scalar, parallel and canonical-basis operations.
#include "mutual_port.hpp"
namespace asitic {
SoftReal dot(const double* a, const double* b) {
    return (static_cast<SoftReal>(a[0]) * b[0]
          + static_cast<SoftReal>(a[1]) * b[1])
          + static_cast<SoftReal>(a[2]) * b[2];
}

SoftReal norm(const double* v) { return x87::sqrt(dot(v, v)); }
SoftReal sqrt_dot(const double* a, const double* b) {
    return x87::sqrt(dot(a, b));
}

SoftReal distance(const double* a, const double* b) {
    const SoftReal dx = static_cast<SoftReal>(a[0]) - b[0];
    const SoftReal dy = static_cast<SoftReal>(a[1]) - b[1];
    const SoftReal dz = static_cast<SoftReal>(a[2]) - b[2];
    return x87::sqrt((dx * dx + dy * dy) + dz * dz);
}

void cross(const double* a, const double* b, double* out) {
    // Store in original order: callers may alias out with either input.
    out[0] = x87::binary64(static_cast<SoftReal>(a[1]) * b[2]
                       - static_cast<SoftReal>(a[2]) * b[1]);
    out[1] = x87::binary64(static_cast<SoftReal>(a[2]) * b[0]
                       - static_cast<SoftReal>(a[0]) * b[2]);
    out[2] = x87::binary64(static_cast<SoftReal>(a[0]) * b[1]
                       - static_cast<SoftReal>(a[1]) * b[0]);
}

SoftReal segment_self_inductance(double length, double radius) {
    const SoftReal l = length;
    SoftReal term = 0;
    if (!(l < 0x1.b7cdfd9d7bdbbp-34)) {
        const SoftReal a = l / static_cast<SoftReal>(radius);
        const SoftReal inv = 1.0 / a;
        term = (x87::log(x87::sqrt(a * a + 1.0) + a)
                - x87::sqrt(inv * inv + 1.0)) + inv;
    }
    return (l + l) * term;
}
}

namespace asitic {
// 0x080b3c94. Two-dimensional logarithmic antiderivative used in
// the geometric mean distance of rectangular wire cross sections.
SoftReal cross_section_log_integral(double xd, double yd) {
    const SoftReal x = xd, y = yd, x2 = x*x, y2 = y*y;
    const SoftReal eps = 0x1.b7cdfd9d7bdbbp-34;
    SoftReal logarithmic, angular = 0.0;
    if (x87::abs(x) > eps && x87::abs(y) > eps) {
        logarithmic = (x87::log(x2+y2)*((x2*x2-x2*6.0*y2)+y2*y2))/24.0;
        const SoftReal a = x87::atan(y/x);
        const SoftReal b = x87::atan(x/y);
        angular = (-x*y*(x2*a+y2*b))/3.0;
    } else {
        const SoftReal square = x87::abs(x) > eps ? x2 : y2;
        if (x87::abs(x) > eps || x87::abs(y) > eps)
            logarithmic = (x87::log(square)*(square*square))/24.0;
        else logarithmic = 0.0;
    }
    return logarithmic+angular;
}

// 0x08063ca0. This returns a distance, not an inductance.
SoftReal effective_separation(double w1, double w2, double t1, double t2,
                                 double dx, double dy) {
    using x87::binary64;
    const SoftReal x = dx, y = dy;
    const SoftReal r = x87::sqrt(x*x+y*y);
    const SoftReal ts = static_cast<SoftReal>(t1)+t2;
    if (ts*1.5 < r && (static_cast<SoftReal>(w1)+w2)*1.5 < r) return r;
    const SoftReal ws = static_cast<SoftReal>(w1)+w2;
    const SoftReal wd = static_cast<SoftReal>(w1)-w2;
    const SoftReal td = static_cast<SoftReal>(t1)-t2;
    const double xs[] = {binary64(wd*0.5-x), binary64(-ws*0.5-x),
                         binary64(ws*0.5-x), binary64(-wd*0.5-x)};
    const double ys[] = {binary64(td*0.5-y), binary64(ts*0.5-y),
                         binary64(-ts*0.5-y), binary64(-td*0.5-y)};
    double rows[3] = {};
    SoftReal last = 0;
    for (unsigned i = 0; i < 4; ++i) {
        const double v0 = binary64(cross_section_log_integral(xs[i],ys[0]));
        const double v1 = binary64(cross_section_log_integral(xs[i],ys[1]));
        const double v2 = binary64(cross_section_log_integral(xs[i],ys[2]));
        const SoftReal v3 = cross_section_log_integral(xs[i],ys[3]);
        if (i == 0) rows[0] = binary64((static_cast<SoftReal>(v0)-v1-v2)+v3);
        if (i == 1) rows[1] = binary64(((-static_cast<SoftReal>(v0)+v1)+v2)-binary64(v3));
        if (i == 2) rows[2] = binary64(((-static_cast<SoftReal>(v0)+v1)+v2)-v3);
        if (i == 3) last = ((static_cast<SoftReal>(v0)-v1)-v2)+binary64(v3);
    }
    const SoftReal total = ((static_cast<SoftReal>(rows[0])+rows[1])+rows[2])+last;
    const SoftReal volume = ((static_cast<SoftReal>(w1)*w2)*t1)*t2;
    const SoftReal offset = 0x1.0aaaaaaaaaaabp+1; // original binary64 25/12
    return binary64(x87::exp((total*-0.5)/volume-offset));
}
}

namespace asitic {
// 0x08062230. Despite its old decompiler name, this is the projected
// parallel-segment case table, not the general three-dimensional integral.
int parallel_segment_mutual(const double* a, const double* b, double* out, double sep) {
    using x87::abs;
    using x87::binary64;
    const SoftReal eps = 0x1.b7cdfd9d7bdbbp-34;
    double alo = a[0], ahi = a[3], bhi = b[3];
    SoftReal ady = static_cast<SoftReal>(a[4])-a[1];
    SoftReal bdy = static_cast<SoftReal>(b[4])-b[1];
    SoftReal alen = static_cast<SoftReal>(ahi)-alo;
    SoftReal blo = b[0];
    SoftReal bdx = static_cast<SoftReal>(bhi)-blo;
    double blen = binary64(bdx);
    const double abs_adx = binary64(abs(alen));
    if (binary64(x87::sqrt(static_cast<SoftReal>(abs_adx)*abs_adx+abs(ady)*abs(ady))) < eps
        || x87::sqrt(abs(bdy)*abs(bdy)+abs(bdx)*abs(bdx)) < eps) return -1;
    if (abs(ady*binary64(bdy)+alen*blen) < eps) { *out = 0.0; return 0; }
    if (ahi < alo) {
        alen = static_cast<SoftReal>(alo)-ahi;
        double tmp = ahi; ahi = alo; alo = tmp;
    }
    if (bhi < blo) {
        blo = bhi;
        blen = binary64(static_cast<SoftReal>(b[0])-blo);
        bhi = b[0];
    }
    const auto classify = [&](double x) {
        return blo <= x ? (x <= bhi ? 2 : 1) : 0;
    };
    const int kind = classify(ahi)+3*classify(alo);
    SoftReal ysep = abs(static_cast<SoftReal>(a[1])-b[1]);
    if (eps < sep) {
        if (abs(ysep-sep) < eps) ysep = 0;
        else ysep = x87::sqrt(static_cast<SoftReal>(sep)*sep+ysep*ysep);
    }
    const double radius = binary64(effective_separation(a[6],b[6],a[7],b[7],binary64(ysep),sep));
    const auto self = [&](SoftReal length) {
        return segment_self_inductance(binary64(length),radius);
    };
    const auto rounded_self = [&](SoftReal length) {
        return static_cast<SoftReal>(binary64(self(length)));
    };
    const auto adjacent = [&]() {
        const SoftReal total = alen+blen;
        return x87::log(total/blen)*blen+alen*x87::log(total/alen);
    };
    const auto collinear = [&](double gap) {
        const SoftReal total = (alen+blen)+gap;
        const SoftReal p = static_cast<SoftReal>(gap)+alen;
        const SoftReal q = static_cast<SoftReal>(blen)+gap;
        return x87::log(static_cast<SoftReal>(gap))*gap
             + ((x87::log(total)*binary64(total)-p*x87::log(p))-q*x87::log(q));
    };
    const auto three = [&](double gap) {
        return 0.5*((rounded_self(alen)+rounded_self(blen))-self(gap));
    };
    SoftReal value = 0;
    switch (kind) {
    case 0:
    case 4: {
        const SoftReal raw_gap = kind == 0 ? blo-ahi : static_cast<SoftReal>(alo)-bhi;
        const double gap = binary64(raw_gap);
        if (ysep < eps && raw_gap < eps) value = adjacent();
        else if (ysep < eps) value = collinear(gap);
        else if (gap >= eps) {
            const SoftReal s0 = rounded_self((alen+blen)+gap);
            const SoftReal s1 = rounded_self(gap);
            const SoftReal s2 = rounded_self(alen+gap);
            const SoftReal s3 = self(static_cast<SoftReal>(blen)+gap);
            value = kind == 0 ? ((s0+s1)-(s2+binary64(s3)))*0.5
                              : (((s0+s1)-s2)-s3)*0.5;
        } else value = 0.5*((rounded_self(alen+blen)-rounded_self(alen))-self(blen));
        break;
    }
    case 2:
    case 7: {
        const SoftReal raw_overlap = kind == 2 ? static_cast<SoftReal>(ahi)-blo
                                                 : static_cast<SoftReal>(bhi)-alo;
        const double overlap = binary64(raw_overlap);
        if (raw_overlap < eps && ysep < eps) value = adjacent();
        else if (overlap >= eps) {
            if (ysep < eps && (kind == 2 || sep < eps)) return -1;
            value = (((rounded_self((alen+blen)-overlap)+rounded_self(overlap))
                       -rounded_self(alen-overlap))-self(static_cast<SoftReal>(blen)-overlap))*0.5;
        } else value = 0.5*((rounded_self(alen+blen)-rounded_self(alen))-self(blen));
        break;
    }
    case 1:
    case 8: {
        const SoftReal raw_left = kind == 1 ? blo-alo : static_cast<SoftReal>(alo)-blo;
        const SoftReal raw_right = kind == 1 ? static_cast<SoftReal>(ahi)-bhi
                                               : static_cast<SoftReal>(bhi)-ahi;
        const double left = binary64(raw_left), right = binary64(raw_right);
        if (raw_left < eps && raw_right < eps) value = self(kind == 1 ? alen : blen);
        else if (left >= eps && right >= eps) {
            const SoftReal inside = kind == 1 ? static_cast<SoftReal>(blen) : alen;
            value = (((rounded_self(inside+left)+rounded_self(inside+right))
                       -rounded_self(left))-self(right))*0.5;
        } else value = three(left >= eps ? left : right);
        break;
    }
    case 3: case 5: case 6: return -1;
    }
    *out = binary64(value);
    return 0;
}
}

namespace asitic {
namespace {
double projection_load(const double& value){return x87::binary64(SoftReal(value));}
double projection_delta(const double& first,const double& second){return x87::binary64(SoftReal(first)-second);}
}
// 0x08063654. This is an intersection predicate, not an integrator.
int segments_intersect_parametric(const double* p, const double* u,
                                  const double* q, const double* v,
                                  double length_a, double length_b, IntersectionHistory& history) {
    using x87::abs;
    using x87::binary64;
    const SoftReal eps = 0x1.b7cdfd9d7bdbbp-34;
    const double xy = binary64(static_cast<SoftReal>(binary64(static_cast<SoftReal>(v[0])*u[1]))
                              -static_cast<SoftReal>(u[0])*v[1]);
    const double xz = binary64(static_cast<SoftReal>(binary64(static_cast<SoftReal>(v[0])*u[2]))
                              -static_cast<SoftReal>(u[0])*v[2]);
    const double yz = binary64(static_cast<SoftReal>(v[1])*u[2]-static_cast<SoftReal>(u[1])*v[2]);
    if (abs(xy) < eps && abs(xz) < eps && abs(yz) < eps) {
        const bool x = abs(u[0]) > eps, y = abs(u[1]) > eps, z = abs(u[2]) > eps;
        const SoftReal tx = x ? (static_cast<SoftReal>(q[0])-p[0])/u[0] : 0;
        const SoftReal ty = y ? (static_cast<SoftReal>(q[1])-p[1])/u[1] : 0;
        const double tz = z ? binary64((static_cast<SoftReal>(q[2])-p[2])/u[2]) : 0;
        bool collinear = false;
        if (x && y && z) collinear = abs(tx-ty) < eps && abs(tx-tz) < eps;
        else if (x && y) collinear = abs(tx-ty) < eps;
        else if (x && z) collinear = abs(tx-tz) < eps;
        else if (y && z) collinear = abs(ty-tz) < eps;
        else if (x) collinear = abs(static_cast<SoftReal>(p[1])-q[1]) < eps
                             && abs(static_cast<SoftReal>(p[2])-q[2]) < eps;
        else if (y) collinear = abs(static_cast<SoftReal>(p[0])-q[0]) < eps
                             && abs(static_cast<SoftReal>(p[2])-q[2]) < eps;
        else if (z) collinear = abs(static_cast<SoftReal>(p[0])-q[0]) < eps
                             && abs(static_cast<SoftReal>(p[1])-q[1]) < eps;
        if (!collinear) return 0;
        unsigned k = 0;
        if (u[k] == 0) { k = 1; if (u[k] == 0) k = 2; }
        const SoftReal delta = static_cast<SoftReal>(q[k])-p[k];
        const SoftReal first = delta/u[k];
        const SoftReal last = (static_cast<SoftReal>(length_b)*v[k]+delta)/u[k];
        // Preserve the original asymmetric bounds, including last < length_b.
        return eps < first && first+eps < length_a && eps < last && last+eps < length_b;
    }
    unsigned i = 0, j = 1, k = 2;
    double det = xy;
    bool selected=abs(xy)>eps;
    if (!selected) {
        if (abs(xz) > eps) { j = 2; k = 1; det = xz; selected=true; }
        else if (abs(yz)>eps) { i = 1; j = 2; k = 0; det = yz; selected=true; }
        // Otherwise native retains the incoming projection slots and the XY
        // denominator, including when that denominator is NaN.
    }
    if(selected) {
        const unsigned axes[]={i,j,k};
        double first[3],second[3];
        for(unsigned axis=0;axis<3;++axis) {
            first[axis]=projection_load(u[axis]);
            second[axis]=projection_load(v[axis]);
        }
        for(unsigned axis=0;axis<3;++axis)history.u[axis]=first[axes[axis]];
        for(unsigned axis=0;axis<3;++axis)history.v[axis]=second[axes[axis]];
        for(unsigned axis=0;axis<3;++axis)history.delta[axis]=projection_delta(q[axes[axis]],p[axes[axis]]);
    }
    const double di=history.delta[0],dj=history.delta[1],dk=history.delta[2];
    const SoftReal t = (static_cast<SoftReal>(dj)*history.v[0]-static_cast<SoftReal>(di)*history.v[1])/det;
    const SoftReal s = (static_cast<SoftReal>(dj)*history.u[0]-static_cast<SoftReal>(di)*history.u[1])/det;
    if (abs((t*history.u[2]-s*history.v[2])-dk) > eps) return 0;
    return eps < t && t+eps < length_a && eps < s && s+eps < length_b;
}
int segments_intersect_parametric(const double* p,const double* u,const double* q,const double* v,
                                  double length_a,double length_b) {
    IntersectionHistory history{};
    return segments_intersect_parametric(p,u,q,v,length_a,length_b,history);
}
}

namespace asitic {
// 0x08062ebc. Set up the local basis and select a mutual-inductance path.
// It also rejects intersections; it does not itself compute inductance.
int canonicalize_segment_pair(double* a, double* b, IntersectionHistory& history) {
    using x87::abs;
    using x87::binary64;
    const SoftReal eps = 0x1.b7cdfd9d7bdbbp-34;
    double da[3], db[3], p[3], q[3];
    for (unsigned i=0;i<3;++i) {
        p[i]=a[i]; q[i]=b[i];
        da[i]=binary64(static_cast<SoftReal>(a[i+3])-a[i]);
        db[i]=binary64(static_cast<SoftReal>(b[i+3])-b[i]);
    }
    if (abs(dot(da,db)) < eps) return 5;
    const SoftReal na=norm(da);
    if (na > eps) for (double& v : da) v=binary64(v/na);
    if (na < eps) return 6;
    const SoftReal nb=norm(db);
    if (nb > eps) for (double& v : db) v=binary64(v/nb);
    if (nb < eps) return 6;
    const auto length = [&](const double* s, const double* dir) {
        for (unsigned i=0;i<3;++i) {
            const SoftReal delta=static_cast<SoftReal>(s[i+3])-s[i];
            if (abs(delta) > eps && abs(dir[i]) > eps) return binary64(delta/dir[i]);
        }
        return 0.0;
    };
    const double la=length(a,da), lb=length(b,db);
    if (la == 0 || lb == 0) return 4;
    if (segments_intersect_parametric(p,da,q,db,la,lb,history)) return 3;

    double delta[3], start[3], end[3];
    for (unsigned i=0;i<3;++i) {
        const SoftReal shifted_start=static_cast<SoftReal>(a[i])+5000.0;
        const SoftReal shifted_end=static_cast<SoftReal>(a[i+3])+5000.0;
        // The original retains the z start in ST, but reloads x/y starts
        // from QWORD stores. Removing the translation changes low bits.
        delta[i]=binary64(shifted_end-(i == 2 ? shifted_start : binary64(shifted_start)));
        start[i]=binary64(static_cast<SoftReal>(b[i])-a[i]);
        end[i]=binary64(static_cast<SoftReal>(b[i+3])-a[i]);
    }
    const SoftReal nd=norm(delta);
    if (nd < eps) return 4;
    double e1[3], first[3], last[3], e3[3], e2[3];
    for (unsigned i=0;i<3;++i) e1[i]=binary64(delta[i]/nd);
    const SoftReal ns=norm(start), ne=norm(end);
    for (unsigned i=0;i<3;++i) {
        first[i]=ns > eps ? binary64(start[i]/ns) : 0.0;
        last[i]=ne > eps ? binary64(end[i]/ne) : 0.0;
    }
    cross(e1,first,e3);
    SoftReal n3=norm(e3);
    if (n3 < eps) {
        cross(e1,last,e3); n3=norm(e3);
        if (n3 < eps) return 0;
    }
    for (double& v : e3) v=binary64(v/n3);
    cross(e3,e1,e2);
    const SoftReal n2=norm(e2);
    for (double& v : e2) v=binary64(v/n2);
    a[0]=a[1]=a[2]=a[4]=a[5]=0.0;
    a[3]=binary64(norm(delta));
    b[0]=binary64(dot(start,e1)); b[1]=binary64(dot(start,e2)); b[2]=binary64(dot(start,e3));
    b[3]=binary64(dot(end,e1)); b[4]=binary64(dot(end,e2));
    const SoftReal last_z=dot(end,e3);
    b[5]=binary64(last_z);
    const SoftReal projection=abs(((static_cast<SoftReal>(a[0])-a[3])*(static_cast<SoftReal>(b[0])-b[3])
                                   +(static_cast<SoftReal>(a[1])-a[4])*(static_cast<SoftReal>(b[1])-b[4]))
                                   +(static_cast<SoftReal>(a[2])-a[5])*(static_cast<SoftReal>(b[2])-last_z));
    if (abs(projection-distance(b,b+3)*binary64(distance(a,a+3))) < eps) return 0;
    if (abs(b[5]) < eps && abs(b[2]) < eps) return 1;
    return 2;
}
int canonicalize_segment_pair(double* a,double* b) {
    IntersectionHistory history{};
    return canonicalize_segment_pair(a,b,history);
}
}

namespace {
using namespace asitic;
int segment(const double* a,const double* b,double* out,int& warning){
 double da[3],db[3];for(int i=0;i<3;i++){da[i]=x87::binary64(SoftReal(a[i])-a[i+3]);db[i]=x87::binary64(SoftReal(b[i])-b[i+3]);}
 const SoftReal eps(0x1.b7cdfd9d7bdbbp-34);const auto orientation=dot(da,db);double sign=1.;
 if(!(orientation>eps)){if(!(orientation<-eps)){*out=0.;return 0;}sign=-1.;}
 const SoftReal scale(0x1.a36e2eb1c432dp-14);
 const double separation=x87::binary64(x87::abs(SoftReal(a[2])*scale-SoftReal(b[2])*scale));
 double sa[8],sb[8];for(int i=0;i<8;i++){sa[i]=x87::binary64(SoftReal(a[i])*scale);sb[i]=x87::binary64(SoftReal(b[i])*scale);}
 IntersectionHistory history{};const int kind=canonicalize_segment_pair(sa,sb,history);double value=0.;
 if(kind==0)parallel_segment_mutual(sa,sb,&value,separation);
 else if(kind==1)planar_segment_mutual(sa,sb,&value);
 else if(kind==2)spatial_segment_mutual(sa,sb,&value);
 else if(kind==3)warning=1;
 else if(kind!=4&&kind!=5&&kind!=6)warning=2;
 *out=x87::binary64(x87::abs(SoftReal(value))*sign);return 0;
}
static double inputs[256*18],outputs[256*6];
}
namespace asitic {
int segment_mutual_value(const double* a,const double* b,double* out,int& warning){return segment(a,b,out,warning);}
}
extern "C" __attribute__((export_name("mutual_buffer"))) unsigned mutual_buffer(){return reinterpret_cast<unsigned>(inputs);}
extern "C" __attribute__((export_name("mutual_result_buffer"))) unsigned mutual_result_buffer(){return reinterpret_cast<unsigned>(outputs);}
extern "C" __attribute__((export_name("mutual_probe"))) int mutual_probe(int n){
 if(n<1||n>256)return -1;
 for(int i=0;i<n;i++){
  const double* p=inputs+18*i+1;const int mode=inputs[18*i];int status=0,warning=0;SoftReal value;
  if(mode==0)value=asitic::segment_self_inductance(p[0],p[1]);
  else if(mode==1)value=asitic::cross_section_log_integral(p[0],p[1]);
  else if(mode==2)value=asitic::effective_separation(p[0],p[1],p[2],p[3],p[4],p[5]);
  else if(mode==3){double result=423.;status=asitic::parallel_segment_mutual(p,p+8,&result,p[16]);value=SoftReal(result);}
  else if(mode==4){double result=423.;status=segment(p,p+8,&result,warning);value=SoftReal(result);}
  else return -2;
  double* out=outputs+6*i;out[0]=status;out[1]=asitic::x87::binary64(value);out[2]=double(unsigned(value.value.signif));out[3]=double(unsigned(value.value.signif>>32));out[4]=value.value.signExp;out[5]=warning;
 }
 return 0;
}

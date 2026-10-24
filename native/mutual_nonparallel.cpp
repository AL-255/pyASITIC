// Retained native planar/spatial formulas and original stores.
#include "mutual_port.hpp"
namespace asitic {
// 0x08061b84. Coplanar nonparallel case, not the orthogonal case
// suggested by the old symbol name. Orthogonal pairs are rejected earlier.
void planar_segment_mutual(const double* a, const double* b, double* out) {
    using x87::binary64;
    using x87::abs;
    using x87::atanh;
    const SoftReal eps=0x1.b7cdfd9d7bdbbp-34;
    double d0=binary64(distance(a+3,b+3));
    const double d1=binary64(distance(a+3,b));
    const double d2=binary64(distance(a,b));
    const double d3=binary64(distance(a,b+3));
    const double la=binary64(distance(a,a+3));
    const SoftReal raw_lb=distance(b,b+3);
    const double lb=binary64(raw_lb);
    const double p2=binary64(static_cast<SoftReal>(d3)*d3);
    const double q2=binary64(static_cast<SoftReal>(d2)*d2);
    const double diff=binary64(static_cast<SoftReal>(p2)-static_cast<SoftReal>(d2)*d2);
    const SoftReal r2=static_cast<SoftReal>(d1)*d1;
    const SoftReal s2=static_cast<SoftReal>(d0)*d0;
    const SoftReal delta=(static_cast<SoftReal>(diff)+r2)-s2;
    const double delta64=binary64(delta);
    const SoftReal magnitude=abs(delta);
    const SoftReal a2=static_cast<SoftReal>(la)*la;
    const SoftReal b2=raw_lb*raw_lb;
    const SoftReal cosine=magnitude/((static_cast<SoftReal>(la)+la)*lb);
    const double cosangle=binary64(x87::cos(binary64(x87::atan2(x87::sqrt(1.0-cosine*cosine),cosine))));
    SoftReal sum;
    if (abs(d0)<eps || abs(d1)<eps || abs(d2)<eps || abs(d3)<eps) {
        if (abs(d0)<eps) d0=d2;
        else if (abs(d1)<eps) d0=d3;
        else if (!(abs(d2)<eps) && abs(d3)<eps) d0=d1;
        const double hb=binary64(atanh(lb/(static_cast<SoftReal>(la)+d0)));
        const double ha=binary64(atanh(la/(static_cast<SoftReal>(lb)+d0)));
        sum=static_cast<SoftReal>(lb)*ha+static_cast<SoftReal>(hb)*la;
    } else {
        SoftReal v,w;
        if (delta64>eps) {
            w=static_cast<SoftReal>(diff)-b2;
            v=(static_cast<SoftReal>(binary64(r2))-q2)-a2;
        } else {
            v=(s2-p2)-a2;
            w=(static_cast<SoftReal>(q2)-p2)-b2;
        }
        const SoftReal numerator=la*((b2+b2)*v+magnitude*w);
        const SoftReal denominator=a2*4.0*b2-static_cast<SoftReal>(delta64)*delta64;
        const SoftReal x=numerator/denominator;
        const SoftReal y=(lb*(magnitude*v+w*(a2+a2)))/denominator;
        const double hb0=binary64(atanh(lb/(static_cast<SoftReal>(d0)+d1)));
        const double hb1=binary64(atanh(lb/(static_cast<SoftReal>(d2)+d3)));
        const double ha0=binary64(atanh(la/(delta64>eps ? static_cast<SoftReal>(d0)+d3
                                                       : static_cast<SoftReal>(d1)+d2)));
        const double ha1=binary64(atanh(la/(delta64>eps ? static_cast<SoftReal>(d1)+d2
                                                       : static_cast<SoftReal>(d0)+d3)));
        sum=((y+lb)*ha0+(static_cast<SoftReal>(hb0)*(x+la)-static_cast<SoftReal>(hb1)*x))
             -static_cast<SoftReal>(ha1)*y;
    }
    *out=binary64((static_cast<SoftReal>(cosangle)+cosangle)*sum);
}
}

namespace asitic {
// 0x080613bc. General spatial segment mutual-inductance formula.
void spatial_segment_mutual(const double* a, const double* b, double* out) {
    using x87::binary64;
    using x87::abs;
    using x87::atanh;
    const SoftReal eps=0x1.b7cdfd9d7bdbbp-34;
    const double d0=binary64(distance(a+3,b+3));
    const double d1=binary64(distance(a+3,b));
    const double d2=binary64(distance(a,b));
    const double d3=binary64(distance(a,b+3));
    const double la=binary64(distance(a,a+3));
    const double lb=binary64(distance(b,b+3));
    const double p2=binary64(static_cast<SoftReal>(d3)*d3);
    const double q2=binary64(static_cast<SoftReal>(d2)*d2);
    const double diff=binary64(static_cast<SoftReal>(p2)-static_cast<SoftReal>(d2)*d2);
    const SoftReal r2=static_cast<SoftReal>(d1)*d1;
    const SoftReal s2=static_cast<SoftReal>(d0)*d0;
    const SoftReal delta=(static_cast<SoftReal>(diff)+r2)-s2;
    const double delta64=binary64(delta);
    const SoftReal magnitude=abs(delta);
    const SoftReal cosine=magnitude/((static_cast<SoftReal>(la)+la)*lb);
    const double angle=binary64(x87::atan2(x87::sqrt(1.0-cosine*cosine),cosine));
    const double c=binary64(x87::cos(angle)), s=binary64(x87::sin(angle));
    const SoftReal a2=static_cast<SoftReal>(la)*la, b2=static_cast<SoftReal>(lb)*lb;
    SoftReal v,w;
    if (delta64 > eps) {
        w=static_cast<SoftReal>(diff)-b2;
        v=(static_cast<SoftReal>(binary64(r2))-q2)-a2;
    } else {
        v=(s2-p2)-a2;
        w=(static_cast<SoftReal>(q2)-p2)-b2;
    }
    const SoftReal den=a2*4.0*b2-static_cast<SoftReal>(delta64)*delta64;
    const SoftReal x=(la*(magnitude*w+(b2+b2)*v))/den;
    const SoftReal y=(lb*(w*(a2+a2)+magnitude*v))/binary64(den);
    const SoftReal h2=(x+x)*y*c+(((delta64 > eps ? q2 : p2)-x*x)-y*y);
    const double h=binary64(x87::sqrt(h2));
    const SoftReal n=c*h2;
    const SoftReal xp=x+la;
    const double yp=binary64(y+lb);
    const double a0=binary64(x87::atan2(xp*(y+lb)*s*s+n,
                                       static_cast<SoftReal>(h)*(delta64 > eps ? d0 : d1)*s));
    const double a1=binary64(x87::atan2(n+xp*y*s*s,
                                       static_cast<SoftReal>(h)*(delta64 > eps ? d1 : d0)*s));
    const double a2angle=binary64(x87::atan2(n+x*y*s*s,
                                           static_cast<SoftReal>(h)*(delta64 > eps ? d2 : d3)*s));
    const double a3=binary64(x87::atan2(x*yp*s*s+n,
                                       static_cast<SoftReal>(h)*(delta64 > eps ? d3 : d2)*s));
    const SoftReal angular=((static_cast<SoftReal>(a0)-a1)+a2angle)-a3;
    const double hb0=binary64(atanh(lb/(static_cast<SoftReal>(d0)+d1)));
    const double hb1=binary64(atanh(lb/(static_cast<SoftReal>(d2)+d3)));
    const double ha0=binary64(atanh(la/(delta64>eps ? static_cast<SoftReal>(d1)+d2
                                                   : static_cast<SoftReal>(d0)+d3)));
    const double ha1=binary64(atanh(la/(delta64>eps ? static_cast<SoftReal>(d0)+d3
                                                   : static_cast<SoftReal>(d1)+d2)));
    const SoftReal sum=static_cast<SoftReal>(ha1)*yp
                         +((static_cast<SoftReal>(hb0)*xp-static_cast<SoftReal>(hb1)*x)-y*ha0);
    *out=binary64(((sum+sum)-(angular*h)/s)*c);
}
}

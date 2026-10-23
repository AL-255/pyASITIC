// Retained-arithmetic port of recomp_cpp/src/complex.cpp.
// SoftReal preserves the original 80-bit operations and explicit stores.
#include "matrix_port.hpp"


namespace asitic::lapack {
[[noreturn]] __attribute__((weak)) void fatal_error(const char*) { __builtin_trap(); }
[[noreturn]] __attribute__((weak)) void application_fatal_error(const char* message) { fatal_error(message); }
__attribute__((weak)) void argument_error(const char*,int) {}
namespace {
using x87::binary64;
void store_binary64(double& destination,SoftReal value){destination=x87::binary64(value);}
ComplexValue product(const ComplexValue& a,const ComplexValue& b) {
    return {binary64((SoftReal)a.real*b.real-(SoftReal)a.imag*b.imag),
            binary64((SoftReal)a.imag*b.real+(SoftReal)a.real*b.imag)};
}
}
SoftReal abs1(const ComplexValue& z) {
    return x87::abs(z.real)+x87::abs(z.imag);
}
SoftReal magnitude(const ComplexValue& z) {
    SoftReal x=z.real,y=z.imag;
    if(x<0) x=-x;
    if(y<0) y=-y;
    if(x<y) { const SoftReal t=x;x=y;y=t; }
    if(x+y==x) return x;
    const SoftReal r=y/x;
    return x87::sqrt(1.0+r*r)*x;
}
void divide(ComplexValue& out,const ComplexValue& a,const ComplexValue& b) {
    const SoftReal c=b.real,d=b.imag;
    const SoftReal ac=c<0?-c:c,ad=d<0?-d:d;
    SoftReal real,imag;
    if(ac<=ad) {
        if(ad==0)fatal_error("complex division by zero");
        const SoftReal r=c/d,denom=r*r*d+d;
        real=((SoftReal)a.real*r+a.imag)/denom;
        imag=((SoftReal)a.imag*r-a.real)/denom;
    } else {
        const SoftReal r=d/c,denom=r*r*c+c;
        real=((SoftReal)a.imag*r+a.real)/denom;
        imag=((SoftReal)a.imag-(SoftReal)a.real*r)/denom;
    }
    store_binary64(out.imag,imag);store_binary64(out.real,real);
}
void square_root(ComplexValue& out,const ComplexValue& z) {
    const SoftReal real=z.real,imag=z.imag,m=magnitude(z);
    if(m==0) { out={0,0};return; }
    // The native test selects the first branch only for ordered real > 0.
    // A NaN real part takes this branch, including the imaginary sign change.
    if(!(real>0)) {
        const SoftReal t=x87::sqrt(0.5*(m-real));
        const double im=binary64(imag<0?-t:t);
        out.imag=im;store_binary64(out.real,(imag/im)/2.0);
    } else {
        const SoftReal t=x87::sqrt(0.5*(real+m));
        store_binary64(out.real,t);store_binary64(out.imag,(imag/t)/2.0);
    }
}
void integer_power(ComplexValue& out,const ComplexValue& z,int exponent) {
    ComplexValue acc{1,0},base=z;
    unsigned p=static_cast<unsigned>(exponent);
    if(exponent<0) { p=0u-p;divide(base,acc,z); }
    while(p) {
        if(p&1) acc=product(acc,base);
        p>>=1;
        if(!p)break;
        const SoftReal real=(SoftReal)base.real*base.real-(SoftReal)base.imag*base.imag;
        const SoftReal imag=((SoftReal)base.real+base.real)*base.imag;
        base.imag=binary64(imag);base.real=binary64(real);
    }
    out=acc;
}
void eigen2(const ComplexValue& a,const ComplexValue& b,const ComplexValue& c,
            ComplexValue& rt1,ComplexValue& rt2,ComplexValue& evscal,
            ComplexValue& cs1,ComplexValue& sn1) {
    if(magnitude(b)==0) {
        rt1=a;rt2=c;
        const double m=binary64(magnitude(rt1));
        if(magnitude(rt2)<=m) { cs1={1,0};sn1={0,0}; }
        else { const auto t=rt1;rt1=rt2;rt2=t;cs1={0,0};sn1={1,0}; }
        return;
    }
    const ComplexValue s{binary64(((SoftReal)a.real+c.real)*0.5),
                         binary64(((SoftReal)a.imag+c.imag)*0.5)};
    const ComplexValue diff{binary64((SoftReal)a.real-c.real),binary64((SoftReal)a.imag-c.imag)};
    ComplexValue t{binary64((SoftReal)diff.real*0.5),binary64((SoftReal)diff.imag*0.5)};
    const double bn=binary64(magnitude(b));
    SoftReal z=magnitude(t);
    if(z<=bn)z=bn;
    const double zd=binary64(z);
    if(z>0) {
        ComplexValue st{binary64(t.real/z),binary64(t.imag/z)},sb{binary64((SoftReal)b.real/zd),binary64((SoftReal)b.imag/zd)};
        ComplexValue t2,b2,root;
        integer_power(t2,st,2);integer_power(b2,sb,2);
        const ComplexValue sum{binary64((SoftReal)t2.real+b2.real),binary64((SoftReal)t2.imag+b2.imag)};
        square_root(root,sum);
        t={binary64((SoftReal)zd*root.real),binary64((SoftReal)zd*root.imag)};
    }
    rt1={binary64((SoftReal)s.real+t.real),binary64((SoftReal)s.imag+t.imag)};
    rt2={binary64((SoftReal)s.real-t.real),binary64((SoftReal)s.imag-t.imag)};
    const double m1=binary64(magnitude(rt1));
    if(m1<magnitude(rt2)) { const auto tmp=rt1;rt1=rt2;rt2=tmp; }
    const ComplexValue delta{binary64((SoftReal)rt1.real-a.real),binary64((SoftReal)rt1.imag-a.imag)};
    divide(sn1,delta,b);
    const SoftReal n=magnitude(sn1);
    const double nd=binary64(n);
    if(n>1.0) {
        const ComplexValue scaled{binary64(sn1.real/n),binary64(sn1.imag/n)};
        ComplexValue sq,root;
        integer_power(sq,scaled,2);
        const SoftReal inv=1.0/n;
        const ComplexValue sum{binary64(inv*inv+sq.real),sq.imag};
        square_root(root,sum);
        t={binary64((SoftReal)nd*root.real),binary64((SoftReal)nd*root.imag)};
    } else {
        const SoftReal re=(SoftReal)sn1.real*sn1.real-(SoftReal)sn1.imag*sn1.imag;
        const double im=binary64((SoftReal)sn1.real*sn1.imag+(SoftReal)sn1.real*sn1.imag);
        const ComplexValue sum{binary64(re+1.0),binary64((SoftReal)im+0.0)};
        square_root(t,sum);
    }
    if(magnitude(t)>=0x1.999999999999ap-4) {
        const ComplexValue one{1,0};divide(evscal,one,t);cs1=evscal;
        sn1=product(sn1,evscal);
    } else evscal={0,0};
}
}

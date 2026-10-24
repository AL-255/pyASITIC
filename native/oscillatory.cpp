// Retained SoftFloat port of recomp_cpp/src/oscillatory.cpp.
#include "quadrature_port.hpp"


namespace asitic::quadpack {
namespace {
using x87::binary64;
}
int solve_tridiagonal(int n,double* c,double* d,double* e,double* rhs) {
    c[0]=d[0];
    if(n>1) {
        d[0]=e[0];e[0]=0;e[n-1]=0;
        for(int k=1;k<n;++k) {
            // An unordered comparison also takes the original swap branch.
            if(!(x87::abs(c[k-1])>x87::abs(c[k]))) {
                double temp=c[k];c[k]=c[k-1];c[k-1]=temp;
                temp=d[k];d[k]=d[k-1];d[k-1]=temp;
                temp=e[k];e[k]=e[k-1];e[k-1]=temp;
                temp=rhs[k];rhs[k]=rhs[k-1];rhs[k-1]=temp;
            }
            if(c[k-1]==0)return k;
            const SoftReal multiplier=-((SoftReal)c[k]/c[k-1]);
            c[k]=binary64(multiplier*d[k-1]+d[k]);
            d[k]=binary64(multiplier*e[k-1]+e[k]);e[k]=0;
            rhs[k]=binary64(multiplier*rhs[k-1]+rhs[k]);
        }
    }
    if(c[n-1]==0)return n;
    rhs[n-1]=binary64((SoftReal)rhs[n-1]/c[n-1]);
    if(n>1)rhs[n-2]=binary64(((SoftReal)rhs[n-2]-(SoftReal)d[n-2]*rhs[n-1])/c[n-2]);
    for(int k=n-3;k>=0;--k)
        rhs[k]=binary64((((SoftReal)rhs[k]-(SoftReal)d[k]*rhs[k+1])-(SoftReal)e[k]*rhs[k+2])/c[k]);
    return 0;
}
RuleResult weighted_rule(Integrand f,Weight weight,const double* p1,const double* p2,
                          const double* p3,const double* p4,const int* selector,double a,double b) {
    constexpr double wg[]={0,0x1.092f69f826d57p-3,0x1.1e6b1713d8645p-2,0x1.86fe74ee3302ap-2};
    constexpr double wk[]={0x1.abfd7e03c2fa6p-2,0x1.77c5b67d5746fp-6,0x1.026cdaa7b61c3p-4,
        0x1.ad384a34814c7p-4,0x1.200ed0f46e8c0p-3,0x1.5a1f266e47d5cp-3,0x1.85d6861c80eb0p-3,0x1.a2adbcbec9cd9p-3};
    constexpr double xk[]={0x1.ad04f9087090ep-3,0x1.fba009d4d09b1p-1,0x1.e5f178e7c6229p-1,
        0x1.bacf827b9bb3ep-1,0x1.7ba9f9be3a1d5p-1,0x1.2c13a049dfa24p-1,0x1.9f95df119fd62p-2,0x1.a98b2892e0c78p-3};
    const double center=binary64(((SoftReal)a+b)*SoftReal(0.5)),half=binary64(((SoftReal)b-a)*SoftReal(0.5)),
        absolute_half=binary64(x87::abs(((SoftReal)b-a)*SoftReal(0.5)));
    const double central_f=binary64(f(&center));
    const SoftReal central=weight(&center,p1,p2,p3,p4,selector)*central_f;
    const double central64=binary64(central);
    double g=binary64(central*wk[0]),k=binary64((SoftReal)central64*xk[0]);
    RuleResult out{};out.absolute=binary64(x87::abs((SoftReal)central64*xk[0]));
    double left[7],right[7];
    for(int phase=0;phase<2;++phase)for(int i=1;i<=(phase==0?3:4);++i) {
        const int j=2*i-(phase==0?0:1);
        const SoftReal offset=(SoftReal)half*xk[j];
        const double x=binary64((SoftReal)center-offset),y=binary64(offset+center);
        const double f1=binary64(f(&x));
        const double weighted1=binary64(weight(&x,p1,p2,p3,p4,selector)*f1);
        const double f2=binary64(f(&y));
        const SoftReal weighted2=(SoftReal)f2*weight(&y,p1,p2,p3,p4,selector);
        left[j-1]=weighted1;right[j-1]=binary64(weighted2);
        const SoftReal sum=(SoftReal)weighted1+weighted2;
        if(phase==0)g=binary64(sum*wg[i]+g);
        k=binary64(sum*wk[j]+k);
        out.absolute=binary64((x87::abs(weighted2)+x87::abs(weighted1))*wk[j]+out.absolute);
    }
    const SoftReal mean=(SoftReal)k*SoftReal(0.5);
    out.ascendant=binary64(x87::abs((SoftReal)central64-mean)*xk[0]);
    for(int j=1;j<=7;++j)
        out.ascendant=binary64((x87::abs((SoftReal)left[j-1]-mean)+x87::abs((SoftReal)right[j-1]-mean))
            *wk[j]+out.ascendant);
    out.integral=binary64((SoftReal)k*half);out.absolute=binary64((SoftReal)absolute_half*out.absolute);
    const SoftReal asc=(SoftReal)absolute_half*out.ascendant;
    out.ascendant=binary64(asc);
    const SoftReal raw=x87::abs(((SoftReal)k-g)*half);out.error=binary64(raw);
    if(asc!=0 && raw!=0) {
        const double power=error_power(binary64(raw*SoftReal(200.0)/out.ascendant));
        out.error=binary64((power<=1.0?(SoftReal)power:SoftReal(1.0))*out.ascendant);
    }
    if(SoftReal(0x1p-1022)/(SoftReal(50.0)*SoftReal(0x1p-52))<out.absolute) {
        const SoftReal floor=(SoftReal(50.0)*SoftReal(0x1p-52))*out.absolute;
        if(floor>=out.error)out.error=binary64(floor);
    }
    return out;
}
void chebyshev_transform(const double* c,double* f,double* y,double* z) {
    double v[12];
    for(int i=0;i<12;++i) {
        v[i]=binary64((SoftReal)f[i]-f[24-i]);f[i]=binary64((SoftReal)f[i]+f[24-i]);
    }
    const SoftReal base=(SoftReal)v[0]-v[8];
    const double t=binary64((((SoftReal)v[2]-v[6])-v[10])*c[5]);
    y[3]=binary64(base+t);y[9]=binary64(base-t);
    const double u=binary64(((SoftReal)v[1]-v[7])-v[9]),w=binary64(((SoftReal)v[3]-v[5])-v[11]);
    auto rounded_pair=[&](int a,int b,int center,SoftReal r) {
        z[a]=binary64(r+y[center]);z[b]=binary64((SoftReal)y[center]-binary64(r));
    };
    auto extended_pair=[&](int a,int b,int center,SoftReal r) {
        z[a]=binary64(r+y[center]);z[b]=binary64((SoftReal)y[center]-r);
    };
    rounded_pair(3,21,3,(SoftReal)u*c[2]+(SoftReal)w*c[8]);
    rounded_pair(9,15,9,(SoftReal)u*c[8]-(SoftReal)w*c[2]);
    const double p=binary64((SoftReal)c[3]*v[4]),q=binary64((SoftReal)c[7]*v[8]),
        r=binary64((SoftReal)c[5]*v[6]),
        a=binary64(((SoftReal)p+v[0])+q),
        b=binary64((SoftReal)c[9]*v[10]+binary64((SoftReal)c[1]*v[2]+r));
    y[1]=binary64((SoftReal)a+b);y[11]=binary64((SoftReal)a-b);
    double s=binary64((SoftReal)c[0]*v[1]+(SoftReal)c[2]*v[3]);
    s=binary64((SoftReal)c[4]*v[5]+s);s=binary64((SoftReal)c[6]*v[7]+s);
    s=binary64((SoftReal)c[8]*v[9]+s);
    rounded_pair(1,23,1,(SoftReal)c[10]*v[11]+s);
    s=binary64((SoftReal)c[10]*v[1]-(SoftReal)c[8]*v[3]);
    s=binary64((SoftReal)c[6]*v[5]+s);s=binary64((SoftReal)s-(SoftReal)c[4]*v[7]);
    s=binary64((SoftReal)c[2]*v[9]+s);
    rounded_pair(11,13,11,(SoftReal)s-(SoftReal)c[0]*v[11]);
    const double a2=binary64(((SoftReal)v[0]-p)+q),
        b2=binary64((SoftReal)c[9]*v[2]-r),b3=binary64((SoftReal)c[1]*v[10]);
    const SoftReal b4=(SoftReal)b2+b3;
    y[5]=binary64((SoftReal)a2+b4);y[7]=binary64((SoftReal)a2-b4);
    s=binary64((SoftReal)c[4]*v[1]-(SoftReal)c[8]*v[3]);
    s=binary64((SoftReal)s-(SoftReal)c[0]*v[5]);s=binary64((SoftReal)s-(SoftReal)c[10]*v[7]);
    s=binary64((SoftReal)c[2]*v[9]+s);
    rounded_pair(5,19,5,(SoftReal)c[6]*v[11]+s);
    extended_pair(7,17,7,(((((SoftReal)c[6]*v[1]-(SoftReal)c[2]*v[3])-(SoftReal)c[10]*v[5])
                          +(SoftReal)c[0]*v[7])-(SoftReal)c[8]*v[9])-(SoftReal)c[4]*v[11]);
    for(int i=0;i<6;++i) {
        v[i]=binary64((SoftReal)f[i]-f[12-i]);f[i]=binary64((SoftReal)f[i]+f[12-i]);
    }
    const SoftReal a3=(SoftReal)c[7]*v[4]+v[0],b5=(SoftReal)c[3]*v[2];
    y[2]=binary64(a3+b5);y[10]=binary64((SoftReal)binary64(a3)-b5);y[6]=binary64((SoftReal)v[0]-v[4]);
    s=binary64((SoftReal)c[1]*v[1]+(SoftReal)c[5]*v[3]);
    rounded_pair(2,22,2,(SoftReal)c[9]*v[5]+s);
    rounded_pair(6,18,6,(((SoftReal)v[1]-v[3])-v[5])*c[5]);
    extended_pair(10,14,10,((SoftReal)c[9]*v[1]-(SoftReal)c[5]*v[3])+(SoftReal)c[1]*v[5]);
    for(int i=0;i<3;++i) {
        v[i]=binary64((SoftReal)f[i]-f[6-i]);f[i]=binary64((SoftReal)f[i]+f[6-i]);
    }
    y[4]=binary64((SoftReal)c[7]*v[2]+v[0]);y[8]=binary64((SoftReal)f[0]-(SoftReal)c[7]*f[2]);
    extended_pair(4,20,4,(SoftReal)c[3]*v[1]);
    extended_pair(8,16,8,(SoftReal)c[7]*f[1]-f[3]);
    y[0]=binary64((SoftReal)f[0]+f[2]);extended_pair(0,24,0,(SoftReal)f[1]+f[3]);
    y[12]=z[12]=binary64((SoftReal)v[0]-v[2]);
    for(int i=1;i<=11;++i)y[i]=binary64((SoftReal)y[i]*0x1.5555555555555p-3);
    y[0]=binary64((SoftReal)y[0]*0x1.5555555555555p-4);y[12]=binary64((SoftReal)y[12]*0x1.5555555555555p-4);
    for(int i=1;i<=23;++i)z[i]=binary64((SoftReal)z[i]*0x1.5555555555555p-4);
    z[0]=binary64((SoftReal)z[0]*0x1.5555555555555p-5);z[24]=binary64((SoftReal)z[24]*0x1.5555555555555p-5);
}
namespace {
constexpr double cheb_cosines[]={0x1.fb9ea92ec689bp-1,0x1.ee8dd4748bf15p-1,0x1.d906bcf328d46p-1,
    0x1.bb67ae8584caap-1,0x1.963268b572492p-1,0x1.6a09e667f3bcdp-1,0x1.37af93f9513eap-1,
    0x1.0000000000000p-1,0x1.87de2a6aea963p-2,0x1.0907dc1930690p-2,0x1.0b5150f6da2d1p-3};
SoftReal oscillatory_weight(const double* x,const double* frequency,const double* opaque,
                               const double*,const double*,const int* selector) {
    const auto& math=*reinterpret_cast<const Trigonometry*>(opaque);
    const double argument=binary64((SoftReal)*frequency**x);
    return *selector==2?math.sine(argument):math.cosine(argument);
}
void compute_moments(double par,int row,MomentCache& cache,Trigonometry math) {
    const double squared=binary64((SoftReal)par*par),plus=binary64((SoftReal)par*par+SoftReal(2.0)),
        sine=binary64(math.sine(par)),cosine=binary64(math.cosine(par));
    double v[28],diagonal[25],lower[25],upper[25];
    v[0]=binary64(((SoftReal)sine+sine)/par);
    const double eight_cos=binary64((SoftReal)cosine*SoftReal(8.0));
    v[1]=binary64(((((SoftReal)squared+squared)-SoftReal(8.0))*sine/par+eight_cos)/squared);
    const SoftReal polynomial=((SoftReal)squared-SoftReal(80.0))*squared+SoftReal(192.0);
    v[2]=binary64(((polynomial+polynomial)*sine/par+((SoftReal)squared-SoftReal(12.0))*SoftReal(32.0)*cosine)/
                   ((SoftReal)squared*squared));
    const SoftReal ac=(SoftReal)par*SoftReal(24.0)*sine;
    if(x87::abs(par)>SoftReal(24.0)) {
        for(int k=3;k<13;++k) {
            const SoftReal n=2*k-2,sq=n*n,difference=((SoftReal)plus-sq)-sq;
            v[k]=binary64(((((difference+difference)*v[k-1]-eight_cos)*(sq-SoftReal(4.0))+ac)
                -(n+SoftReal(1.0))*squared*(n+SoftReal(2.0))*v[k-2])/((n-SoftReal(2.0))*(n-SoftReal(1.0))*squared));
        }
    } else {
        for(int i=0;i<25;++i) {
            const SoftReal n=6+2*i,sq=n*n,difference=sq-SoftReal(4.0);
            diagonal[i]=binary64(-((difference+difference)*(((SoftReal)plus-sq)-sq)));
            v[i+3]=binary64(ac-difference*eight_cos);
            if(i<24) {
                upper[i]=binary64((n-SoftReal(2.0))*(n-SoftReal(1.0))*squared);
                lower[i+1]=binary64((n+SoftReal(4.0))*(n+SoftReal(3.0))*squared);
            }
        }
        v[3]=binary64((SoftReal)v[3]-(SoftReal(56.0)*squared)*v[2]);
        const SoftReal n=54,sq=n*n,b=(SoftReal)par*sine;
        const SoftReal asymptote=((((b*SoftReal(15.0)+((((SoftReal)squared*SoftReal(210.0)-SoftReal(1.0))*cosine-
            ((SoftReal)squared*SoftReal(105.0)-SoftReal(63.0))*b)/sq-(SoftReal(1.0)-(SoftReal)squared*SoftReal(15.0))*cosine))/sq
            -cosine)+b*SoftReal(3.0))/sq-cosine)/sq;
        v[27]=binary64((SoftReal)v[27]-(n-SoftReal(2.0))*(n-SoftReal(1.0))*(asymptote+asymptote)*squared);
        solve_tridiagonal(25,lower,diagonal,upper,v+3);
    }
    for(int i=0;i<13;++i)cache.data[(2*i)*cache.rows+row]=v[i];
    v[0]=binary64((((SoftReal)sine-(SoftReal)par*cosine)*SoftReal(2.0))/squared);
    const SoftReal div48=SoftReal(48.0)/squared;
    v[1]=binary64(((SoftReal(18.0)-div48)*sine)/squared+((div48-SoftReal(2.0))*cosine)/par);
    const double ac_odd=binary64(-((SoftReal)par*SoftReal(24.0)*cosine));
    const SoftReal eight_sine=-((SoftReal)sine*SoftReal(8.0));
    if(x87::abs(par)>SoftReal(24.0)) {
        for(int k=2;k<12;++k) {
            const SoftReal n=2*k-1,sq=n*n,difference=((SoftReal)plus-sq)-sq;
            v[k]=binary64(((((difference+difference)*v[k-1]+eight_sine)*(sq-SoftReal(4.0))+ac_odd)
                -(n+SoftReal(1.0))*squared*(n+SoftReal(2.0))*v[k-2])/((n-SoftReal(2.0))*(n-SoftReal(1.0))*squared));
        }
    } else {
        for(int i=0;i<25;++i) {
            const SoftReal n=5+2*i,sq=n*n,difference=sq-SoftReal(4.0);
            diagonal[i]=binary64(-((((SoftReal)plus-sq)-sq)*(difference+difference)));
            v[i+2]=binary64(difference*eight_sine+ac_odd);
            if(i<24) {
                upper[i]=binary64((n-SoftReal(2.0))*(n-SoftReal(1.0))*squared);
                lower[i+1]=binary64((n+SoftReal(4.0))*(n+SoftReal(3.0))*squared);
            }
        }
        v[2]=binary64((SoftReal)v[2]-(SoftReal(42.0)*squared)*v[1]);
        const SoftReal n=53,sq=n*n,b=(SoftReal)par*cosine;
        const SoftReal asymptote=((((((SoftReal)squared*SoftReal(15.0)-SoftReal(1.0))*sine+
            (((SoftReal)squared*SoftReal(210.0)-SoftReal(1.0))*sine+((SoftReal)squared*SoftReal(105.0)-SoftReal(63.0))*b)/sq)
            -b*SoftReal(15.0))/sq-b*SoftReal(3.0)-sine)/sq-sine)/sq;
        v[26]=binary64((SoftReal)v[26]-(n-SoftReal(2.0))*(n-SoftReal(1.0))*(asymptote+asymptote)*squared);
        solve_tridiagonal(25,lower,diagonal,upper,v+2);
    }
    for(int i=0;i<12;++i)cache.data[(2*i+1)*cache.rows+row]=v[i];
}
}
OscillatoryRuleResult oscillatory_rule(Integrand f,double a,double b,double frequency,int selector,
    int level,bool reuse,MomentCache& cache,Trigonometry math) {
    const double center=binary64(((SoftReal)b+a)*SoftReal(0.5)),half=binary64(((SoftReal)b-a)*SoftReal(0.5));
    const SoftReal extended_par=(((SoftReal)b-a)*SoftReal(0.5))*frequency;
    const double par=binary64(extended_par);
    if(!(x87::abs(extended_par)>SoftReal(2.0))) {
        const auto value=weighted_rule(f,oscillatory_weight,&frequency,reinterpret_cast<const double*>(&math),
            nullptr,nullptr,&selector,a,b);
        return {value,15};
    }
    const double argument=binary64((SoftReal)center*frequency),
        cc=binary64(math.cosine(argument)*half),ss=binary64(math.sine(argument)*half);
    int row=cache.computed;
    if(level>=cache.computed && !reuse)compute_moments(par,row,cache,math);
    if(level<cache.computed)row=level;
    if(cache.computed<cache.rows-1 && level>=cache.computed)++cache.computed;
    double samples[25],c12[13],c24[25];
    double x=binary64((SoftReal)half+center);samples[0]=binary64(f(&x)*SoftReal(0.5));
    samples[12]=binary64(f(&center));
    x=binary64((SoftReal)center-half);samples[24]=binary64(f(&x)*SoftReal(0.5));
    for(int i=0;i<11;++i) {
        x=binary64((SoftReal)half*cheb_cosines[i]+center);samples[i+1]=binary64(f(&x));
        x=binary64((SoftReal)center-(SoftReal)half*cheb_cosines[i]);samples[23-i]=binary64(f(&x));
    }
    chebyshev_transform(cheb_cosines,samples,c12,c24);
    const auto moment=[&](int column) { return cache.data[column*cache.rows+row]; };
    SoftReal even12=(SoftReal)c12[12]*moment(12),odd12=0;
    for(int j=11;j>=1;j-=2) { even12+=(SoftReal)c12[j-1]*moment(j-1);odd12+=(SoftReal)c12[j]*moment(j); }
    SoftReal even24=(SoftReal)c24[24]*moment(24),odd24=0;
    RuleResult out{};out.absolute=binary64(x87::abs(c24[24]));
    for(int j=23;j>=1;j-=2) {
        even24+=(SoftReal)c24[j-1]*moment(j-1);odd24+=(SoftReal)c24[j]*moment(j);
        // The original overwrites RESABS in every iteration instead of adding.
        out.absolute=binary64(x87::abs(c24[j])+x87::abs(c24[j-1]));
    }
    out.absolute=binary64(x87::abs(half)*out.absolute);out.ascendant=0x1.fffffffffffffp1023;
    const SoftReal even_error=x87::abs(even24-even12),odd_error=x87::abs(odd24-odd12);
    if(selector==2) {
        out.integral=binary64((SoftReal)cc*odd24+(SoftReal)ss*even24);
        out.error=binary64(x87::abs((SoftReal)ss*even_error)+x87::abs((SoftReal)cc*odd_error));
    } else {
        out.integral=binary64((SoftReal)cc*even24-(SoftReal)ss*odd24);
        out.error=binary64(x87::abs((SoftReal)ss*odd_error)+x87::abs((SoftReal)cc*even_error));
    }
    return {out,25};
}

IntegralResult integrate_oscillatory(Integrand f,double start,double end,double frequency,int selector,
    double absolute_tolerance,double relative_tolerance,int sequence,OscillatoryWorkspace workspace,
    MomentCache& cache,Trigonometry math) {
    constexpr double epsilon=0x1p-52,huge=0x1.fffffffffffffp1023;
    auto& w=workspace.intervals;
    IntegralResult out{};
    w.left[0]=start;w.right[0]=end;w.integrals[0]=0;w.errors[0]=0;w.order[0]=0;workspace.levels[0]=0;
    if(selector<1 || selector>2 || (absolute_tolerance<=0 && relative_tolerance<SoftReal(50.0)*epsilon)
       || sequence<1 || cache.rows<1) { out.status=6;return out; }
    const double omega=binary64(x87::abs(frequency));
    if(sequence<2)cache.computed=0;
    const auto first_rule=oscillatory_rule(f,start,end,omega,selector,0,false,cache,math);
    const auto& first=first_rule.value;
    out.integral=first.integral;out.error=first.error;out.evaluations=first_rule.evaluations;
    auto tolerance=[&](double value) {
        const SoftReal relative=x87::abs(value)*relative_tolerance;
        return absolute_tolerance>=relative?absolute_tolerance:binary64(relative);
    };
    double target=tolerance(out.integral);
    w.integrals[0]=out.integral;w.errors[0]=out.error;w.order[0]=1;
    if(out.error<=(SoftReal(100.0)*epsilon)*first.absolute && target<out.error)out.status=2;
    if(w.limit==1)out.status=1;
    // DQAWOE leaves LAST at zero on this initial-return path.
    if(out.status || out.error<=target)goto sign_result;
    {
        double table[52],history[3];
        double maximum_error=out.error,area=out.integral,error_sum=out.error,
            small=binary64(x87::abs((SoftReal)end-start)*SoftReal(0.75)),error_large=0,extrap_target=0,correction=0;
        out.error=huge;
        int maximum=1,rank=1,extrap_calls=0,without_improvement=0,table_length=0,
            roundoff1=0,roundoff2=0,roundoff3=0,extrap_status=0;
        bool extrapolating=false,no_extrapolation=false;
        const SoftReal span=x87::abs((SoftReal)end-start);
        bool eligible=!(SoftReal(2.0)<span*SoftReal(0.5)*omega);
        if(eligible)table[table_length++]=out.integral;
        eligible=(span*SoftReal(0.25)*omega<=SoftReal(2.0)) || eligible;
        const int sign=(SoftReal(1.0)-SoftReal(50.0)*epsilon)*first.absolute<=x87::abs(out.integral)?1:-1;
        for(out.intervals=2;out.intervals<=w.limit;++out.intervals) {
            const int at=maximum-1,new_at=out.intervals-1,level=workspace.levels[at]+1;
            const double left=w.left[at],middle=binary64(((SoftReal)w.left[at]+w.right[at])*SoftReal(0.5)),
                right=w.right[at],previous_error=maximum_error;
            const auto rule_a=oscillatory_rule(f,left,middle,omega,selector,level,false,cache,math);
            out.evaluations+=rule_a.evaluations;
            const auto rule_b=oscillatory_rule(f,middle,right,omega,selector,level,true,cache,math);
            out.evaluations+=rule_b.evaluations;
            const auto& a=rule_a.value;const auto& b=rule_b.value;
            const SoftReal area12=(SoftReal)a.integral+b.integral;
            const double error12=binary64((SoftReal)a.error+b.error);
            error_sum=binary64(((SoftReal)error_sum+error12)-maximum_error);
            area=binary64(((SoftReal)area+area12)-w.integrals[at]);
            if(a.error!=a.ascendant && b.error!=b.ascendant) {
                if(!(x87::abs(area12)*1e-5<x87::abs((SoftReal)w.integrals[at]-area12))
                   && !((SoftReal)maximum_error*0.99>error12)) {
                    if(extrapolating)++roundoff2;else ++roundoff1;
                }
                if(out.intervals>10 && maximum_error<error12)++roundoff3;
            }
            w.integrals[at]=a.integral;w.integrals[new_at]=b.integral;
            workspace.levels[at]=level;workspace.levels[new_at]=level;
            target=tolerance(area);
            if(roundoff1+roundoff2>9 || roundoff3>19)out.status=2;
            if(roundoff2>4)extrap_status=3;
            if(out.intervals==w.limit)out.status=1;
            const SoftReal largest=x87::abs(left)>=x87::abs(right)?x87::abs(left):x87::abs(right);
            if(largest<=(SoftReal(1000.0)*SoftReal(0x1p-1022)+x87::abs(middle))*(SoftReal(100.0)*epsilon+SoftReal(1.0)))out.status=4;
            if(a.error<b.error) {
                w.left[at]=middle;w.left[new_at]=left;w.right[new_at]=middle;
                w.integrals[at]=b.integral;w.integrals[new_at]=a.integral;
                w.errors[at]=b.error;w.errors[new_at]=a.error;
            } else {
                w.left[new_at]=middle;w.right[at]=middle;w.right[new_at]=right;
                w.errors[at]=a.error;w.errors[new_at]=b.error;
            }
            sort_errors(w.limit,out.intervals,maximum,maximum_error,w.errors,w.order,rank);
            if(error_sum<=target)goto sum;
            if(out.status)break;
            if(out.intervals==2 && eligible) {
                small=binary64((SoftReal)small*SoftReal(0.5));table[table_length++]=area;
                extrap_target=target;error_large=error_sum;continue;
            }
            if(no_extrapolation)continue;
            if(eligible) {
                const SoftReal reduced=(SoftReal)error_large-previous_error;
                error_large=binary64(reduced);
                if(small<x87::abs((SoftReal)middle-left))error_large=binary64(reduced+error12);
            }
            if(!extrapolating) {
                const SoftReal width=x87::abs((SoftReal)w.right[maximum-1]-w.left[maximum-1]);
                if(width>small)continue;
                if(!eligible) {
                    small=binary64((SoftReal)small*SoftReal(0.5));
                    if(width*SoftReal(0.25)*omega<=SoftReal(2.0)) { eligible=true;extrap_target=target;error_large=error_sum; }
                    continue;
                }
                extrapolating=true;rank=2;
            }
            if(extrap_status!=3 && !(error_large<=extrap_target)) {
                const int count=out.intervals>w.limit/2+2?w.limit-out.intervals+3:out.intervals;
                bool found=false;
                for(int remaining=count-rank;remaining>=0;--remaining) {
                    maximum=w.order[rank-1];maximum_error=w.errors[maximum-1];
                    if(small<x87::abs((SoftReal)w.right[maximum-1]-w.left[maximum-1])) { found=true;break; }
                    ++rank;
                }
                if(found)continue;
            }
            table[table_length++]=area;
            if(table_length>2) {
                double estimate,estimate_error;
                extrapolate(table_length,table,estimate,estimate_error,history,extrap_calls);
                ++without_improvement;
                if(without_improvement>5 && out.error<(SoftReal)error_sum*0.001)out.status=5;
                if(!(estimate_error>=out.error)) {
                    without_improvement=0;out.error=estimate_error;out.integral=estimate;
                    correction=error_large;extrap_target=tolerance(estimate);
                    if(out.error<=extrap_target)break;
                }
                if(table_length==1)no_extrapolation=true;
                if(out.status==5)break;
            }
            maximum=w.order[0];maximum_error=w.errors[maximum-1];rank=1;extrapolating=false;
            small=binary64((SoftReal)small*SoftReal(0.5));error_large=error_sum;
        }
        if(out.error==huge || extrap_calls==0)goto sum;
        if(extrap_status+out.status!=0) {
            if(extrap_status==3)out.error=binary64((SoftReal)correction+out.error);
            if(out.status==0)out.status=3;
            if(out.integral==0 || area==0) {
                if(error_sum<out.error)goto sum;
                if(area==0)goto finish;
            } else if((SoftReal)error_sum/x87::abs(area)<(SoftReal)out.error/x87::abs(out.integral))goto sum;
        }
        if(sign==-1) {
            const SoftReal largest=x87::abs(out.integral)>=x87::abs(area)?x87::abs(out.integral):x87::abs(area);
            if(largest<=0.01*first.absolute)goto finish;
        }
        {
            const SoftReal ratio=(SoftReal)out.integral/area;
            if(ratio<0.01 || ratio>100 || x87::abs(area)<=error_sum)out.status=6;
        }
        goto finish;
sum:
        out.integral=0;
        for(int i=0;i<out.intervals;++i)out.integral=binary64((SoftReal)out.integral+w.integrals[i]);
        out.error=error_sum;
    }
finish:
    if(out.status>2)--out.status;
sign_result:
    if(selector==2 && frequency<0)out.integral=-out.integral;
    return out;
}

FourierResult integrate_fourier(Integrand f,double start,double frequency,int selector,
    double absolute_tolerance,FourierWorkspace w,Trigonometry math) {
    FourierResult out{};
    if(selector<1 || selector>2 || absolute_tolerance<=0 || w.cycle_limit<3) { out.status=6;return out; }
    if(frequency==0) {
        if(selector==1) {
            const auto value=integrate_infinite(f,0,1,absolute_tolerance,0,w.cycle.intervals);
            out.integral=value.integral;out.error=value.error;out.evaluations=value.evaluations;out.status=value.status;
        }
        w.integrals[0]=out.integral;w.errors[0]=out.error;w.statuses[0]=out.status;out.cycles=1;
        return out;
    }
    const SoftReal absolute_frequency=x87::abs(frequency);
    const int truncated=x87::truncate_int(absolute_frequency);
    const int odd=static_cast<int>(2u*static_cast<unsigned>(truncated)+1u);
    const double cycle_length=binary64(((SoftReal)odd*0x1.921fb54442d18p+1)/absolute_frequency);
    constexpr double decay=0x1.ccccccccccccdp-1;
    const double one_minus=binary64(SoftReal(1.0)-decay);
    double eps=absolute_tolerance;
    if(SoftReal(0x1p-1022)/one_minus<eps)eps=binary64((SoftReal)one_minus*eps);
    const double initial_eps=eps;
    double factor=1.0,correction=0,error_sum=0,tail=0,left=start,right=binary64((SoftReal)cycle_length+start),
        table[52];
    double* const history=w.extrapolation_history;
    int table_length=0,previous_length=0,extrap_calls=0,without_improvement=0;
    MomentCache cache{w.moments,w.moment_rows,0};
    for(out.cycles=1;out.cycles<=w.cycle_limit;++out.cycles) {
        const int at=out.cycles-1;
        const double tolerance=binary64((SoftReal)eps*factor);
        const auto value=integrate_oscillatory(f,left,right,frequency,selector,tolerance,0,out.cycles,w.cycle,cache,math);
        w.integrals[at]=value.integral;w.errors[at]=value.error;w.statuses[at]=value.status;
        out.evaluations+=value.evaluations;
        factor=binary64((SoftReal)factor*decay);
        const SoftReal updated_sum=(SoftReal)error_sum+value.error;
        error_sum=binary64(updated_sum);tail=binary64(x87::abs(value.integral)*SoftReal(50.0));
        // The first convergence test keeps the unrounded error accumulator.
        if(updated_sum+tail<=absolute_tolerance && out.cycles>5)goto direct_sum;
        if(!(correction>=value.error))correction=value.error;
        if(value.status!=0) {
            const SoftReal updated_eps=(SoftReal)correction*one_minus;
            eps=initial_eps>=updated_eps?initial_eps:binary64(updated_eps);
            out.status=7;
        }
        if(out.status==7 && (SoftReal)error_sum+tail<=(SoftReal)correction*SoftReal(10.0) && out.cycles>5)goto direct_sum;
        ++table_length;
        if(out.cycles<2)table[0]=value.integral;
        else {
            table[table_length-1]=binary64((SoftReal)table[previous_length-1]+value.integral);
            if(out.cycles!=2) {
                if(out.cycles==w.cycle_limit)out.status=1;
                double estimate,estimate_error;
                extrapolate(table_length,table,estimate,estimate_error,history,extrap_calls);
                ++without_improvement;
                if(without_improvement>14 && out.error<=((SoftReal)error_sum+tail)*0.001)out.status=4;
                if(estimate_error<=out.error || out.cycles==3) {
                    out.error=estimate_error;out.integral=estimate;without_improvement=0;
                    if((SoftReal)correction*SoftReal(10.0)+out.error<=absolute_tolerance ||
                       (estimate_error<=absolute_tolerance && absolute_tolerance<=(SoftReal)correction*SoftReal(10.0)))break;
                }
                if(out.status!=0 && out.status!=7)break;
            }
        }
        previous_length=table_length;left=right;right=binary64((SoftReal)cycle_length+right);
    }
    out.error=binary64((SoftReal)correction*SoftReal(10.0)+out.error);
    if(out.status==0)return out;
    if(out.integral==0 || table[table_length-1]==0) {
        if(error_sum<out.error)goto direct_sum;
        if(table[table_length-1]==0)return out;
    }
    if(((SoftReal)error_sum+tail)/x87::abs(table[table_length-1])<
        (SoftReal)out.error/x87::abs(out.integral))goto direct_sum;
    if(out.status>0 && out.status!=7)out.error=binary64((SoftReal)tail+out.error);
    return out;
direct_sum:
    // This jump can precede appending the current cycle. Preserve the original
    // table-tail selection rather than recomputing a sum of all cycle entries.
    out.integral=table[table_length-1];out.error=binary64((SoftReal)error_sum+tail);
    return out;
}

}

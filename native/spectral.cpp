// Retained-arithmetic port of potential_tables.cpp.
#include "spectral_port.hpp"

namespace asitic {
namespace {
using x87::binary64;
double potential_tanh(SoftReal x) { return retained_tanh(x.value); }
struct Transfer { ComplexValue u,v; };
Transfer potential_transfer(bool down,int first,int last,double k,const PotentialLayers& layers) {
    const auto* z=layers.depths;
    const double initial=potential_tanh(static_cast<SoftReal>(k)*(down?
        static_cast<SoftReal>(z[last+1])-z[last]:static_cast<SoftReal>(z[0])-z[1]));
    Transfer state=down?Transfer{{1,0},{initial,0}}:Transfer{{initial,0},{1,0}};
    for(int i=down?last-1:1;down?i>=first:i<=last;down?--i:++i) {
        const SoftReal argument=static_cast<SoftReal>(k)*(down?
            static_cast<SoftReal>(z[i+1])-z[i]:static_cast<SoftReal>(z[i])-z[i+1]);
        const auto q=legacy::divide(layers.coefficients[i],layers.coefficients[down?i+1:i-1]);
        const double t=potential_tanh(argument);
        const SoftReal qr=q.real,qi=q.imag,ur=state.u.real,ui=state.u.imag,vr=state.v.real,vi=state.v.imag;
        const SoftReal pr=qr*vr-qi*vi,pi=qr*vi+qi*vr;
        const ComplexValue u{binary64(ur+(qr*t*vr-qi*t*vi)),binary64(qi*t*vr+qr*t*vi+ui)};
        const ComplexValue v{binary64(static_cast<SoftReal>(t)*ur+pr),binary64(static_cast<SoftReal>(t)*ui+pi)};
        state={u,v};
    }
    return state;
}
}
ComplexValue potential_transfer_up(int last,double k,const PotentialLayers& layers) {
    const auto state=potential_transfer(false,0,last,k,layers);
    return legacy::divide(state.u,state.v);
}
ComplexValue potential_transfer_down(int first,int last,double k,const PotentialLayers& layers) {
    const auto state=potential_transfer(true,first,last,k,layers);
    return legacy::divide(state.u,state.v);
}
ComplexValue potential_source_up(int source,double k,double height,const PotentialTableLayers& layers) {
    const double saved=binary64(layers.depths[source+1]);layers.depths[source+1]=binary64(height);
    const auto state=potential_transfer(false,0,source,k,layers.view());
    layers.depths[source+1]=saved;return state.u;
}
ComplexValue potential_source_down(int source,int last,double k,double height,const PotentialTableLayers& layers) {
    const double saved=binary64(layers.depths[source]);layers.depths[source]=binary64(height);
    const auto state=potential_transfer(true,source,last,k,layers.view());
    layers.depths[source]=saved;return state.u;
}
namespace {
struct SpectralExtended { SoftReal real,imag; };
SpectralExtended ext(ComplexValue z) { return {z.real,z.imag}; }
double spectral_cosh(SoftReal x,bool rounded=false) { return retained_cosh(x.value,rounded); }
ComplexValue spectral_combine(double s,ComplexValue ratio,ComplexValue upper,ComplexValue lower,
    ComplexValue top,ComplexValue bottom,double ta,double tb,double tc,bool down) {
    const auto r=ext(ratio),u=ext(upper),d=ext(lower),t=ext(top),b=ext(bottom);
    const SoftReal pr=binary64(binary64(u.real*b.real)-u.imag*b.imag);
    const SoftReal pi=u.imag*b.real+binary64(u.real*b.imag);
    const SoftReal qr=d.real*t.real-d.imag*t.imag,qi=d.real*t.imag+d.imag*t.real;
    const SoftReal cr=b.real*t.real-b.imag*t.imag,ci=t.imag*b.real+b.imag*t.real;
    const SoftReal sr=binary64(binary64(static_cast<SoftReal>(s)*r.real)-SoftReal(0.)*r.imag);
    const SoftReal si=binary64(static_cast<SoftReal>(s)*r.imag+r.real*SoftReal(0.));
    const double up_weight=down?tb:ta,down_weight=down?ta:tb;
    const SoftReal real_sum=((pr*up_weight+qr*down_weight)+static_cast<SoftReal>(binary64(cr*tb))*ta)+(d.real*u.real-d.imag*u.imag);
    const SoftReal imag_sum=((pi*up_weight+qi*down_weight)+(ci*tb)*ta)+(d.imag*u.real+binary64(d.real*u.imag));
    const ComplexValue numerator{binary64(binary64(sr*real_sum)-si*imag_sum),binary64(imag_sum*sr+real_sum*si)};
    const ComplexValue denominator{binary64(((qr-pr)+cr*tc)-((tc*d.real)*u.real-(tc*d.imag)*u.imag)),
        binary64(((qi-binary64(pi))+static_cast<SoftReal>(binary64(ci))*tc)-((tc*d.imag)*u.real+(tc*d.real)*u.imag))};
    return legacy::divide(numerator,denominator);
}
ComplexValue spectral_kernel(bool down,int source,int target,int last,double k,double source_height,double target_height,
    const PotentialTableLayers& layers) {
    const auto* z=layers.depths;const auto* c=layers.coefficients;
    const double ta=potential_tanh(static_cast<SoftReal>(k)*(down?
        static_cast<SoftReal>(z[target])-target_height:static_cast<SoftReal>(z[target+1])-target_height));
    const double tb=potential_tanh(static_cast<SoftReal>(k)*(down?
        static_cast<SoftReal>(z[target+1])-source_height:static_cast<SoftReal>(z[target])-source_height));
    const double tc=potential_tanh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[target+1])-z[target]));
    double scale=1;
    for(int i=down?target:source;i<=(down?source:target);++i) {
        const double a=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[0])-z[i+1]));
        const double b=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[0])-z[i]));
        const double d=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[i+1])-z[i]),true);
        scale=binary64((static_cast<SoftReal>(a)/(static_cast<SoftReal>(b)*d))*scale);
    }
    ComplexValue top{0,0},bottom{0,0},lower{1,0};
    if(target==last)top=legacy::divide(c[target],c[target-1]);
    else {
        if(target!=0)top=legacy::divide(c[target],c[target-1]);
        bottom=legacy::divide(c[target],c[target+1]);
        lower=potential_transfer_down(target+1,last,k,layers.view());
    }
    const auto upper=potential_transfer_up(target-1,k,layers.view());
    const auto from_source=down?potential_source_down(source,last,k,source_height,layers):potential_source_up(source,k,source_height,layers);
    const auto from_target=down?potential_source_down(target,last,k,source_height,layers):potential_source_up(target,k,source_height,layers);
    const auto ratio=legacy::divide(from_source,from_target);
    auto value=spectral_combine(scale,ratio,upper,lower,top,bottom,ta,tb,tc,down);
    const double first=spectral_cosh(static_cast<SoftReal>(k)*(down?
        static_cast<SoftReal>(z[target])-target_height:static_cast<SoftReal>(z[source])-source_height));
    value={binary64(static_cast<SoftReal>(value.real)*first-static_cast<SoftReal>(value.imag)*SoftReal(0.)),
           binary64(static_cast<SoftReal>(value.imag)*first+static_cast<SoftReal>(value.real)*SoftReal(0.))};
    const double second=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[0])-z[down?target:source]));
    const double third=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[0])-z[(down?source:target)+1]));
    const SoftReal weight=static_cast<SoftReal>(second)/third;
    value={binary64(static_cast<SoftReal>(value.real)*weight-static_cast<SoftReal>(value.imag)*SoftReal(0.)),
           binary64(static_cast<SoftReal>(value.imag)*weight+static_cast<SoftReal>(value.real)*SoftReal(0.))};
    const double final=spectral_cosh(static_cast<SoftReal>(k)*(static_cast<SoftReal>(z[(down?source:target)+1])-(down?source_height:target_height)));
    const SoftReal real=static_cast<SoftReal>(value.real)*final-static_cast<SoftReal>(value.imag)*SoftReal(0.);
    const SoftReal imag=SoftReal(0.)*value.real+static_cast<SoftReal>(value.imag)*final;
    const ComplexValue weighted{binary64(real*c[target].real-imag*c[target].imag),
        binary64(static_cast<SoftReal>(c[target].imag)*binary64(real)+static_cast<SoftReal>(c[target].real)*imag)};
    return legacy::divide(weighted,{k,0});
}
}
ComplexValue potential_spectral_a(int source,int target,int last,double k,double source_height,double target_height,const PotentialTableLayers& layers) {
    return spectral_kernel(true,source,target,last,k,source_height,target_height,layers);
}
ComplexValue potential_spectral_b(int source,int target,int last,double k,double source_height,double target_height,const PotentialTableLayers& layers) {
    return spectral_kernel(false,source,target,last,k,source_height,target_height,layers);
}
void generate_potential_tables(int source,int target,const PotentialTableGeometry& g,PotentialTableOutput out,bool samples_only) {
    constexpr double pi=0x1.921fb54442d18p+1;
    const auto sample=[&](double k,bool y_axis) {
        const auto& sm=g.metals[source];const auto& tm=g.metals[target];
        const int sl=sm.layer,tl=tm.layer;
        double sh=sm.height,th=tm.height;
        const bool a=sh<th;
        if(source!=target) {
            // The Y-axis code applies the opposite half-thickness offsets
            // from the combined-grid and X-axis paths in the original.
            if(a!=y_axis) { sh=binary64(sh+SoftReal(0.5)*sm.thickness);th=binary64(th-SoftReal(0.5)*tm.thickness); }
            else { sh=binary64(sh-SoftReal(0.5)*sm.thickness);th=binary64(th+SoftReal(0.5)*tm.thickness); }
        }
        return a?potential_spectral_a(sl,tl,g.layer_count-1,k,sh,th,g.layers):
                 potential_spectral_b(sl,tl,g.layer_count-1,k,sh,th,g.layers);
    };
    for(int x=0;x<=g.nx;++x)for(int y=0;y<=g.ny;++y) {
        auto& z=out.xy[x*(g.nx+1)+y];
        if(x==0 || y==0 || x==g.nx || y==g.ny) { z={0,0};continue; }
        const SoftReal kx=(static_cast<SoftReal>(x)*pi)/g.width,ky=(static_cast<SoftReal>(y)*pi)/g.height;
        z=sample(binary64(x87::sqrt(kx*kx+ky*ky)),false);
        const ComplexValue dx{static_cast<double>(x),0},dy{static_cast<double>(y),0};
        z=legacy::divide(z,dx);z=legacy::divide(z,dx);z=legacy::divide(z,dy);z=legacy::divide(z,dy);
    }
    if(!samples_only)retained_grid(out.xy,g.nx,g.ny);
    for(int x=0;x<=g.nx;++x) {
        auto& z=out.x[x];if(x==0 || x==g.nx) { z={0,0};continue; }
        z=sample(binary64((static_cast<SoftReal>(x)*pi)/g.width),false);
        const ComplexValue divisor{static_cast<double>(x),0};
        z=legacy::divide(z,divisor);z=legacy::divide(z,divisor);
    }
    for(int y=0;y<=g.ny;++y) {
        auto& z=out.y[y];if(y==0 || y==g.ny) { z={0,0};continue; }
        z=sample(binary64((static_cast<SoftReal>(y)*pi)/g.height),true);
        const ComplexValue divisor{static_cast<double>(y),0};
        z=legacy::divide(z,divisor);z=legacy::divide(z,divisor);
    }
    for(int x=g.nx;x<2*g.nx;++x)out.x[x]=out.x[2*g.nx-x];
    for(int y=g.ny;y<2*g.ny;++y)out.y[y]=out.y[2*g.ny-y];
    if(!samples_only){retained_fft(out.x,2*g.nx);retained_fft(out.y,2*g.ny);}
}
}

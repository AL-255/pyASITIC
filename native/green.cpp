// Retained SoftFloat port of recomp_cpp/src/green.cpp.
#include "green_port.hpp"



namespace asitic {
namespace {
using x87::binary64;
constexpr double factor=0x1.08ef67ae4dd49p-17;
}
ComplexValue green_propagation_constant(double k,double frequency,double layer) {
    return legacy::square_root({binary64((SoftReal)k*k+SoftReal(0.0)),
                                binary64((SoftReal)factor*layer*frequency)});
}
ComplexValue green_complex_tanh(ComplexValue z) {
    const auto c=legacy::cosh(z),s=legacy::sinh(z);
    return legacy::divide(s,c);
}
SoftReal green_reflection_imag(double k,double frequency,double layer1) {
    const auto g=green_propagation_constant(k,frequency,layer1);
    const ComplexValue a{binary64((SoftReal)k-g.real),-g.imag},
                       b{binary64((SoftReal)g.real+k),g.imag};
    return legacy::divide(a,b).imag;
}
SoftReal green_oscillating_integrand(double k,double frequency,const GreenLayers& layers) {
    const auto a=green_propagation_constant(k,frequency,layers.layer1),
               b=green_propagation_constant(k,frequency,layers.layer2);
    const SoftReal ar=a.real,ai=a.imag;
    const double sr=binary64(ar*ar-ai*ai),si=binary64((ar*ai)+(ar*ai));
    const auto t=green_complex_tanh({binary64((SoftReal)layers.depth*ar),
                                    binary64((SoftReal)layers.depth*ai)});
    const SoftReal difference=(SoftReal)k-b.real,negative_imag=-((SoftReal)b.imag);
    // 0x0809395d rounds the real base; the imaginary base remains live in
    // an x87 register through 0x08093a2f despite an intervening FST QWORD.
    const SoftReal base_i=ar*negative_imag+ai*difference;
    const double base_r=binary64(ar*difference-ai*negative_imag),
                 kr=binary64((SoftReal)k*b.real),ki=binary64((SoftReal)k*b.imag);
    const SoftReal nr=-(SoftReal)sr+kr,ni=-(SoftReal)si+ki;
    const ComplexValue numerator{binary64((nr*t.real-ni*t.imag)+base_r),
        binary64(base_i+(ni*t.real+nr*t.imag))};
    const SoftReal sum=(SoftReal)k+b.real,dr=(SoftReal)sr+kr,di=(SoftReal)si+ki;
    const ComplexValue denominator{binary64((ar*sum-ai*b.imag)+(dr*t.real-di*t.imag)),
        binary64((sum*ai+ar*b.imag)+(di*t.real+dr*t.imag))};
    return legacy::divide(numerator,denominator).imag;
}
SoftReal green_propagation_integrand(double frequency,const GreenLayers& layers) {
    const double omega=binary64((SoftReal)0x1.515370f99f6cbp-20*
        binary64((SoftReal)0x1.921fb54442d18p+2*frequency));
    const auto a=legacy::square_root({binary64(((SoftReal)layers.layer1*SoftReal(0.0))*omega),
                                     binary64((SoftReal)layers.layer1*omega)}),
               b=legacy::square_root({binary64(((SoftReal)layers.layer2*SoftReal(0.0))*omega),
                                     binary64((SoftReal)layers.layer2*omega)});
    const SoftReal twice_depth=(SoftReal)layers.depth+layers.depth;
    const auto e=legacy::exp({binary64(twice_depth*a.real),binary64(twice_depth*a.imag)}),
               f=legacy::exp({binary64(twice_depth*b.real),binary64(twice_depth*b.imag)});
    const double plus=binary64((SoftReal)e.real+SoftReal(1.0));
    // The sum is reloaded from a binary64 spill, while the difference and
    // subsequent complex products stay extended until the final division.
    const SoftReal minus=(SoftReal)e.real-SoftReal(1.0),
        twice_plus=(SoftReal)plus+plus,twice_ei=(SoftReal)e.imag+e.imag,
        twice_fr=(SoftReal)f.real+f.real,twice_fi=(SoftReal)f.imag+f.imag;
    const double base_r=binary64(twice_plus*a.real-twice_ei*a.imag);
    const SoftReal base_i=twice_plus*a.imag+twice_ei*a.real,
        ur=twice_fr*minus-twice_fi*e.imag,ui=twice_fr*e.imag+twice_fi*minus;
    const ComplexValue numerator{binary64((ur*b.real-ui*b.imag)+base_r),
        binary64(base_i+(ur*b.imag+ui*b.real))};
    const SoftReal ir=(minus*SoftReal(0.0)-(SoftReal)e.imag*SoftReal(1.0))*layers.layer1,
        ii=(SoftReal(0.0)*e.imag+minus*SoftReal(1.0))*layers.layer1,
        vr=(SoftReal)f.real*plus-(SoftReal)f.imag*e.imag,
        vi=(SoftReal)f.real*e.imag+(SoftReal)f.imag*plus,
        wr=vr*a.real-vi*a.imag,wi=vr*a.imag+vi*a.real;
    const ComplexValue denominator{binary64(ir*omega+(wr*b.real-wi*b.imag)),
        binary64(ii*omega+(wr*b.imag+wi*b.real))};
    return legacy::divide(numerator,denominator).imag;
}
SoftReal green_oscillating_kernel(double k,double frequency,const GreenLayers& layers,
                                     double height,double separation) {
    const SoftReal kh=(SoftReal)k*height;
    if(kh>=x87::log(SoftReal(0x1.fffffep127)))return SoftReal(0.0);
    const double integrand=binary64(green_oscillating_integrand(k,frequency,layers)),
                 decay=binary64(x87::exp(-kh));
    return ((x87::wide_cos((SoftReal)k*separation)*integrand)*decay)/k;
}
SoftReal green_reflection_kernel(double k,double height) {
    const SoftReal kh=(SoftReal)k*height;
    if(kh>=x87::log(SoftReal(0x1.fffffep127)))return SoftReal(0.0);
    return x87::exp(-kh);
}
}

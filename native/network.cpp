// Retained SoftFloat port of recomp_cpp/src/network.cpp.
#include "network_port.hpp"
namespace asitic {
namespace {
using x87::binary64;
struct ExtendedComplex { SoftReal real,imag; };
ExtendedComplex multiply(const ComplexValue& a,const ComplexValue& b) {
    return {(SoftReal)a.real*b.real-(SoftReal)a.imag*b.imag,
            (SoftReal)a.imag*b.real+(SoftReal)a.real*b.imag};
}
ComplexValue differential_impedance(const TwoPortAdmittance& y) {
    const auto product=multiply(y.y22,y.y11);
    const SoftReal squared_real=(SoftReal)y.y21.real*y.y21.real-(SoftReal)y.y21.imag*y.y21.imag;
    const double square64=binary64(squared_real);
    const SoftReal square_product=(SoftReal)y.y21.real*y.y21.imag,
        squared_imag=square_product+square_product;
    const ComplexValue determinant{binary64(product.real-square64),binary64(product.imag-squared_imag)};
    const ComplexValue numerator{binary64(((SoftReal)y.y22.real+y.y11.real)+((SoftReal)y.y21.real+y.y21.real)),
                                 binary64(((SoftReal)y.y22.imag+y.y11.imag)+((SoftReal)y.y21.imag+y.y21.imag))};
    return legacy::divide(numerator,determinant);
}
// Native804e9b0 explicitly quiets these loads. Its last cross-product
// operand is instead an FMUL memory operand: loading it separately can raise
// a denormal exception even when the native NaN operation suppresses it.
void terminated_discard(SoftReal value) {volatile double copy=binary64(value);(void)copy;}
SoftReal terminated_load(const double& x) {return (SoftReal)x;}
SoftReal terminated_multiply_memory(SoftReal x,const double& y) {return x*(SoftReal)y;}
ExtendedComplex terminated_base(const ComplexValue& a,const ComplexValue& b) {
    const SoftReal ar=terminated_load(a.real),br=terminated_load(b.real),first=ar*br,ai=terminated_load(a.imag),bi=terminated_load(b.imag);
    return {first-ai*bi,ar*bi+ai*br};
}
ExtendedComplex terminated_extra(const ComplexValue& a,const ComplexValue& b) {
    const SoftReal ar=terminated_load(a.real),ai=terminated_load(a.imag);
    return {terminated_multiply_memory(ar,b.real)-terminated_multiply_memory(ai,b.imag),
            terminated_multiply_memory(ar,b.imag)+terminated_multiply_memory(ai,b.real)};
}
ExtendedComplex terminated_cross(const ComplexValue& c,const ComplexValue& d) {
    const SoftReal cr=terminated_load(c.real),dr=terminated_load(d.real),first=cr*dr,ci=terminated_load(c.imag);
    return {first-terminated_multiply_memory(ci,d.imag),dr*ci+terminated_multiply_memory(cr,d.imag)};
}
double power_square(SoftReal x) { return x==0?0:binary64((x*x)*SoftReal(1.0)); }
}
ComplexValue two_port_impedance(const TwoPortAdmittance& y,bool differential,int port) {
    return differential?differential_impedance(y):legacy::divide(1.,port==1?y.y22:y.y11);
}
SoftReal two_port_imaginary_impedance(const TwoPortAdmittance& y,int differential) {
    return differential?differential_impedance(y).imag:legacy::divide(1.,y.y22).imag;
}
ComplexValue terminated_two_port_impedance(const TwoPortAdmittance& y,const ComplexValue& load,int port) {
    const auto admittance=legacy::divide(1.,load);
    const auto base=terminated_base(y.y22,y.y11);
    const auto extra=terminated_extra(port==1?y.y22:y.y11,admittance);
    // Discarded native FST copies raise overflow/underflow/inexact flags while
    // the live base, extra and combined values retain extended precision.
    terminated_discard(base.real);terminated_discard(base.imag);
    terminated_discard(extra.real);terminated_discard(extra.imag);
    const SoftReal total_real=base.real+extra.real,total_imag=base.imag+extra.imag;
    terminated_discard(total_real);terminated_discard(total_imag);
    const auto cross=terminated_cross(y.y21,y.y12);
    terminated_discard(cross.real);terminated_discard(cross.imag);
    const ComplexValue& other=port==1?y.y11:y.y22;
    const ComplexValue numerator{binary64(terminated_load(other.real)+admittance.real),binary64(terminated_load(other.imag)+admittance.imag)},
        denominator{binary64(total_real-cross.real),binary64(total_imag-cross.imag)};
    return legacy::divide(numerator,denominator);
}

SoftReal pi_shunt_resistance(const PiEquivalent& p,int differential) {
    const SoftReal two_pi=SoftReal(0x1.921fb54442d18p+2);
    const SoftReal capacitance=differential?((SoftReal)p.capacitance_second*p.capacitance_first)/
            ((SoftReal)p.capacitance_second+p.capacitance_first):p.capacitance_second,
        resistance=differential?(SoftReal)p.resistance_second+p.resistance_first:p.resistance_second,
        angular=(SoftReal)p.frequency*two_pi;
    const double a=power_square((angular*p.inductance)/p.resistance),b=power_square(SoftReal(1.0)/((angular*capacitance)*resistance));
    const SoftReal series=((SoftReal)a+SoftReal(1.0))*p.resistance,shunt=(SoftReal(1.0)+b)*resistance;
    return (series*shunt)/(series+shunt);
}
SoftReal pi_resonant_frequency(const PiEquivalent& p) {
    const SoftReal ratio=(SoftReal)p.capacitance_second/p.inductance,
        correction=(SoftReal(1.0)-((SoftReal)p.resistance*p.resistance)*ratio)/
                   (SoftReal(1.0)-((SoftReal)p.resistance_second*p.resistance_second)*ratio);
    SoftReal result=SoftReal(1.0)/((SoftReal)p.inductance*p.capacitance_second);
    if(correction>0)result*=correction;
    return x87::sqrt(result)/SoftReal(0x1.921fb54442d18p+2);
}
PiEquivalent extract_pi_equivalent(const TwoPortAdmittance& y,double frequency) {
    const ComplexValue second{binary64((SoftReal)y.y21.real+y.y22.real),binary64((SoftReal)y.y21.imag+y.y22.imag)},
        first{binary64((SoftReal)y.y11.real+y.y12.real),binary64((SoftReal)y.y11.imag+y.y12.imag)},
        series{-y.y21.real,-y.y21.imag};
    const double angular=binary64((SoftReal)frequency*SoftReal(0x1.921fb54442d18p+2));
    const auto impedance=legacy::divide(1.,series);
    PiEquivalent result{};result.frequency=frequency;result.resistance=impedance.real;
    result.inductance=binary64((SoftReal)impedance.imag/angular);
    if(binary64(x87::sqrt((SoftReal)second.real*second.real+(SoftReal)second.imag*second.imag))>0x1.b7cdfd9d7bdbbp-34) {
        const auto z=legacy::divide(1.,second);result.resistance_second=z.real;
        result.capacitance_second=binary64(-SoftReal(1.0)/((SoftReal)angular*z.imag));
    } else { result.resistance_second=1e15;result.capacitance_second=0; }
    if(binary64(x87::sqrt((SoftReal)first.real*first.real+(SoftReal)first.imag*first.imag))>0x1.b7cdfd9d7bdbbp-34) {
        const auto z=legacy::divide(1.,first);result.resistance_first=z.real;
        result.capacitance_first=binary64(-SoftReal(1.0)/((SoftReal)angular*z.imag));
    } else { result.resistance_first=1e15;result.capacitance_first=0; }
    result.quality_first=binary64(-((SoftReal)second.imag+series.imag)/((SoftReal)second.real+series.real));
    result.quality_second=binary64(-((SoftReal)series.imag+first.imag)/((SoftReal)series.real+first.real));
    const auto differential=two_port_impedance(y,true,1);
    result.quality_differential=binary64((SoftReal)differential.imag/differential.real);
    result.shunt_single=binary64(pi_shunt_resistance(result,0));
    result.shunt_differential=binary64(pi_shunt_resistance(result,1));
    return result;
}
}

#pragma once
#include "contact_port.hpp"
namespace asitic {
struct TwoPortAdmittance{ComplexValue y11,y12,y21,y22;};
struct TwoPortScattering{ComplexValue s11,s12,s21,s22;};
struct PiEquivalent {
 double frequency,inductance,resistance,capacitance_second,capacitance_first,
  resistance_second,resistance_first,quality_first,quality_second,quality_differential,
  shunt_single,shunt_differential;
};
ComplexValue two_port_impedance(const TwoPortAdmittance&,bool,int);
SoftReal two_port_imaginary_impedance(const TwoPortAdmittance&,int);
ComplexValue terminated_two_port_impedance(const TwoPortAdmittance&,const ComplexValue&,int);
SoftReal pi_shunt_resistance(const PiEquivalent&,int);
SoftReal pi_resonant_frequency(const PiEquivalent&);
PiEquivalent extract_pi_equivalent(const TwoPortAdmittance&,double);
TwoPortScattering convert_two_port_scattering(const TwoPortAdmittance&);
}

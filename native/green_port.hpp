#pragma once
#include "contact_port.hpp"
#include "retained_math.hpp"
namespace asitic {
struct GreenLayers { double layer1,layer2,depth; };
ComplexValue green_propagation_constant(double,double,double);
ComplexValue green_complex_tanh(ComplexValue);
SoftReal green_reflection_imag(double,double,double);
SoftReal green_oscillating_integrand(double,double,const GreenLayers&);
SoftReal green_propagation_integrand(double,const GreenLayers&);
SoftReal green_oscillating_kernel(double,double,const GreenLayers&,double,double);
SoftReal green_reflection_kernel(double,double);
namespace legacy {
ComplexValue square_root(const ComplexValue&);
ComplexValue exp(const ComplexValue&);
ComplexValue sinh(const ComplexValue&);
ComplexValue cosh(const ComplexValue&);
}
}

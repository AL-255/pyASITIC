// Legacy DSO arithmetic and stores, distinct from LAPACK's scaled sqrt.
#include "green_port.hpp"
namespace asitic::legacy {
using R=SoftReal;using x87::binary64;
ComplexValue square_root(const ComplexValue& z){
 const R real=z.real,imag=z.imag;const double m=binary64(x87::sqrt(real*real+imag*imag));
 if(m==0)return {0,0};
 if(real>R(0.)){
  const R t=x87::sqrt((R(m)+real)*R(.5));return {binary64(t),binary64((imag/t)*R(.5))};
 }
 R t=x87::sqrt((R(m)-real)*R(.5));if(imag<R(0.))t=-t;
 return {binary64((imag/t)*R(.5)),binary64(t)};
}
ComplexValue exp(const ComplexValue& z){
 const double e=binary64(x87::exp(R(z.real)));
 return {binary64(R(e)*x87::wide_cos(R(z.imag))),binary64(R(e)*x87::wide_sin(R(z.imag)))};
}
ComplexValue sinh(const ComplexValue& z){
 const double s=binary64(x87::sinh_real(R(z.real))),c=binary64(x87::cosh_real(R(z.real)));
 return {binary64(R(s)*x87::wide_cos(R(z.imag))),binary64(R(c)*x87::wide_sin(R(z.imag)))};
}
ComplexValue cosh(const ComplexValue& z){
 const double c=binary64(x87::cosh_real(R(z.real))),s=binary64(x87::sinh_real(R(z.real)));
 return {binary64(R(c)*x87::wide_cos(R(z.imag))),binary64(R(s)*x87::wide_sin(R(z.imag)))};
}
}

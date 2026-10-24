#include "matrix_port.hpp"
using namespace asitic;
static ComplexValue data[numerical_matrix_capacity*numerical_matrix_capacity],scratch[numerical_matrix_capacity];static int pivots[numerical_matrix_capacity];
namespace {
SoftReal memory_operand(double value){
 union{double d;uint64_t word;}bits={.d=value};
 if((bits.word&0x7ff0000000000000ULL)==0x7ff0000000000000ULL&&(bits.word&0xfffffffffffffULL))
  return SoftReal(extFloat80_t{.signif=0x8000000000000000ULL|((bits.word&0xfffffffffffffULL)<<11),.signExp=uint16_t(0x7fff|((bits.word>>48)&0x8000))});
 return SoftReal(value);
}
}
// Original reduce_filament_impedance and LMAT report accumulation:
// FLDL accumulator; FADDL input; FSTPL accumulator after every term.
extern "C" __attribute__((export_name("complex_sum"))) int complex_sum(int count){
 if(count<0||count>numerical_matrix_capacity*numerical_matrix_capacity)return -1;
 double real=0.,imag=0.;
 for(int i=0;i<count;i++){
  real=x87::binary64(SoftReal(real)+memory_operand(data[i].real));
  imag=x87::binary64(SoftReal(imag)+memory_operand(data[i].imag));
 }
 data[0]={real,imag};return 0;
}
extern "C" __attribute__((export_name("matrix_buffer"))) unsigned matrix_buffer(){return reinterpret_cast<unsigned>(data);}
extern "C" __attribute__((export_name("matrix_capacity"))) int matrix_capacity(){return numerical_matrix_capacity;}
extern "C" __attribute__((export_name("pivots_buffer"))) unsigned pivots_buffer(){return reinterpret_cast<unsigned>(pivots);}
extern "C" __attribute__((export_name("factor"))) int factor(int n){if(n<1||n>numerical_matrix_capacity)return -1;return lapack::factor_symmetric_upper(n,{data,n},pivots);}
extern "C" __attribute__((export_name("inverse"))) int inverse(int n){
 int status=factor(n);if(status)return status;status=lapack::invert_symmetric_upper(n,{data,n},pivots,scratch);if(status)return status;
 for(int i=0;i<n;i++)for(int j=0;j<i;j++)data[j*n+i]=data[i*n+j];return 0;
}

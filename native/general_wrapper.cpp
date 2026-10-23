#include "matrix_port.hpp"
using namespace asitic;
// PiX has two extra nodes and two unknowns per branch. Its 256-filament
// application limit therefore needs a larger system than the CAP matrix.
static constexpr int limit=514;
static ComplexValue data[limit*limit],rhs[limit],scratch[limit];
static int pivots[limit];
extern "C" __attribute__((export_name("general_buffer"))) unsigned general_buffer(){return reinterpret_cast<unsigned>(data);}
extern "C" __attribute__((export_name("general_rhs_buffer"))) unsigned general_rhs_buffer(){return reinterpret_cast<unsigned>(rhs);}
extern "C" __attribute__((export_name("general_pivots_buffer"))) unsigned general_pivots_buffer(){return reinterpret_cast<unsigned>(pivots);}
extern "C" __attribute__((export_name("general"))) int general(int n,int operation){
 if(n<1||n>limit||operation<0||operation>3)return -1;
 if(operation==3){
  // Original network_matrix_vector (0x0806cc30), using the transport's
  // column-major input rather than the caller's native row-major records.
  for(int i=0;i<n;i++){
   scratch[i]={0,0};
   for(int j=0;j<n;j++){
    const auto a=data[j*n+i],b=rhs[j];
    const SoftReal real=SoftReal(a.real)*b.real-SoftReal(a.imag)*b.imag;
    const SoftReal imag=SoftReal(b.real)*a.imag+SoftReal(a.real)*b.imag;
    scratch[i]={x87::binary64(real+scratch[i].real),x87::binary64(imag+scratch[i].imag)};
   }
  }
  for(int i=0;i<n;i++)rhs[i]=scratch[i];
  return 0;
 }
 if(operation==2){
  for(int i=0;i<n;i++)if(pivots[i]<1||pivots[i]>n)return -2;
  return lapack::solve_general(n,1,{data,n},pivots,{rhs,n});
 }
 int status=lapack::factor_general(n,n,{data,n},pivots);
 if(status||operation==0)return status;
 for(int i=0;i<n;i++)scratch[i]={0,0};
 return lapack::invert_general(n,{data,n},pivots,scratch,n);
}

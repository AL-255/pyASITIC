#include "matrix_port.hpp"
using namespace asitic;
static ComplexValue data[256*256],scratch[256];static int pivots[256];
extern "C" __attribute__((export_name("matrix_buffer"))) unsigned matrix_buffer(){return reinterpret_cast<unsigned>(data);}
extern "C" __attribute__((export_name("pivots_buffer"))) unsigned pivots_buffer(){return reinterpret_cast<unsigned>(pivots);}
extern "C" __attribute__((export_name("factor"))) int factor(int n){if(n<1||n>256)return -1;return lapack::factor_symmetric_upper(n,{data,n},pivots);}
extern "C" __attribute__((export_name("inverse"))) int inverse(int n){
 int status=factor(n);if(status)return status;status=lapack::invert_symmetric_upper(n,{data,n},pivots,scratch);if(status)return status;
 for(int i=0;i<n;i++)for(int j=0;j<i;j++)data[j*n+i]=data[i*n+j];return 0;
}

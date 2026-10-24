// Retained port of node_equations.cpp's folded two-port driver.
#include "contact_port.hpp"
namespace {
using C=asitic::ComplexValue;using R=SoftReal;using asitic::x87::binary64;
constexpr int limit=256;
static C input[2*limit*limit],lu[limit*limit],drive[limit],bias[limit],current[limit],rhs[limit],ports[4];
static int pivots[limit];
C sum(C a,C b){return {binary64(R(a.real)+R(b.real)),binary64(R(a.imag)+R(b.imag))};}
C difference(C a,C b){return {binary64(R(a.real)-R(b.real)),binary64(R(a.imag)-R(b.imag))};}
C negative(C a){return {binary64(-R(a.real)),binary64(-R(a.imag))};}
void product(const C* matrix,const C* vector,C* result,int n){
 // The original routine reads row-major records, even though its caller's
 // matrices are column-major. Preserve that distinction for asymmetric input.
 for(int i=0;i<n;i++){
  result[i]={0,0};
  for(int j=0;j<n;j++){
   const C a=matrix[i*n+j],b=vector[j];
   const R real=R(a.real)*R(b.real)-R(a.imag)*R(b.imag);
   const R imag=R(b.real)*R(a.imag)+R(a.real)*R(b.imag);
   result[i]={binary64(real+R(result[i].real)),binary64(imag+R(result[i].imag))};
  }
 }
}
}
extern "C" __attribute__((export_name("node_buffer"))) unsigned node_buffer(){return reinterpret_cast<unsigned>(input);}
extern "C" __attribute__((export_name("node_result_buffer"))) unsigned node_result_buffer(){return reinterpret_cast<unsigned>(ports);}
extern "C" __attribute__((export_name("folded_node"))) int folded_node(int n){
 if(n<1||n>limit)return -1;
 C* cap=input;const C* ind=input+n*n;
 for(int i=0;i<n;i++){
  C acc{0,0};
  for(int j=0;j<n;j++){C& value=cap[j*n+i];acc=sum(acc,value);if(i!=j)value=negative(value);}
  cap[i*n+i]=acc;
 }
 for(int j=n-1;j>0;j--)for(int i=0;i<n;i++)lu[j*n+i]=difference(ind[j*n+i],ind[(j-1)*n+i]);
 for(int i=0;i<n;i++)lu[i]=ind[i];
 for(int i=n-1;i>0;i--)for(int j=0;j<n;j++)lu[j*n+i]=difference(lu[j*n+i],lu[j*n+i-1]);
 for(int i=0;i<n*n;i++)lu[i]=sum(cap[i],lu[i]);
 int status=asitic::lapack::factor_general(n,n,{lu,n},pivots);if(status)return status;
 for(int i=0;i<n;i++)bias[i]=drive[i]={0,0};drive[0]={1,0};
 const auto run=[&](){
  product(ind,bias,rhs,n);
  for(int i=n-1;i>0;i--)rhs[i]=difference(rhs[i],rhs[i-1]);
  for(int i=0;i<n;i++)rhs[i]=sum(rhs[i],drive[i]);
  status=asitic::lapack::solve_general(n,1,{lu,n},pivots,{rhs,n});
  const C first=rhs[0];
  for(int i=0;i<n-1;i++)rhs[i]=difference(rhs[i],rhs[i+1]);
  for(int i=0;i<n;i++)rhs[i]=difference(rhs[i],bias[i]);
  product(ind,rhs,current,n);return first;
 };
 const C a=run(),c=negative(current[n-1]);if(status)return status;
 drive[0]={0,0};bias[n-1]={1,0};
 const C b=run(),d=negative(current[n-1]);if(status)return status;
 ports[3]=asitic::legacy::divide(1.,a);
 const R real=(R(a.real)*R(d.real)-R(a.imag)*R(d.imag))-(R(c.real)*R(b.real)-R(c.imag)*R(b.imag));
 const R imag=(R(d.real)*R(a.imag)+R(a.real)*R(d.imag))-(R(b.real)*R(c.imag)+R(c.real)*R(b.imag));
 ports[0]=asitic::legacy::divide(C{binary64(real),binary64(imag)},a);
 ports[1]=ports[2]=asitic::legacy::divide(negative(b),a);
 return 0;
}

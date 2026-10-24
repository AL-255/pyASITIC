#include <stdint.h>
#include "platform.h"
#include "softfloat.h"
typedef extFloat80_t E;
typedef struct { double re,im; } C;
static C buffer[66049],scratch[512];
static E wrs[9][256],wis[9][256];
static int planned;
static const uint64_t mantissas[9]={9223372036854775808ULL,9223372036854783436ULL,10805852496753549594ULL,11233398260283384687ULL,11342368475190395835ULL,11369742684536813208ULL,11376594487685018692ULL,11378307954497381402ULL,11378736353457518654ULL};
static const int powers[9]={-62,-63,-65,-67,-69,-71,-73,-75,-77};
static const double sines[9]={-0x1.dcb4p-50,0x1p+0,0x1.6a09e667f3bcfp-1,0x1.87de2a6aea966p-2,0x1.8f8b83c69a60ep-3,0x1.917a6bc29b43p-4,0x1.91f65f10dd818p-5,0x1.92155f7a36682p-6,0x1.921d1fcdec788p-7};
static E load(double d){union{double d;float64_t f;}u={.d=d};return f64_to_extF80(u.f);}
static double spill(E e){union{double d;float64_t f;}u={.f=extF80_to_f64(e)};return u.d;}
static void plan(void){
 if(planned)return;
 for(int level=0,half=1;level<9;level++,half*=2){
  E wpr={.signif=mantissas[level],.signExp=(uint16_t)(0x8000+16383+63+powers[level])};
  E wpi=load(sines[level]),wr=load(1),wi=load(0);
  for(int m=0;m<half;m++){
   wrs[level][m]=wr;wis[level][m]=wi;E old=wr;
   wr=extF80_add(extF80_sub(extF80_mul(wr,wpr),extF80_mul(wi,wpi)),wr);
   wi=extF80_add(extF80_add(extF80_mul(wi,wpr),extF80_mul(old,wpi)),wi);
  }
 }
 planned=1;
}
static void fft(C* a,int n){
 for(int i=0,j=0;i<n-1;i++){
  if(i<j){C t=a[j];a[j]=a[i];a[i]=t;}
  int k=n>>1;for(;k>1&&j>=k;k>>=1)j-=k;j+=k;
 }
 for(int half=1,level=0;half<n;half*=2,level++){
  for(int m=0;m<half;m++){
   E wr=wrs[level][m],wi=wis[level][m];
   for(int i=m;i<n;i+=half*2){
    E br=load(a[i+half].re),bi=load(a[i+half].im),ar=load(a[i].re),ai=load(a[i].im);
    E tr=extF80_sub(extF80_mul(wr,br),extF80_mul(wi,bi));
    E ti=extF80_add(extF80_mul(wr,bi),extF80_mul(wi,br));
    a[i+half]=(C){spill(extF80_sub(ar,tr)),spill(extF80_sub(ai,ti))};
    a[i]=(C){spill(extF80_add(tr,ar)),spill(extF80_add(ti,ai))};
   }
  }
 }
}
__attribute__((export_name("buffer"))) uintptr_t get_buffer(void){return (uintptr_t)buffer;}
__attribute__((export_name("fft"))) int run_fft(int n){if(n<0||n>512||(n&&(n&(n-1))))return -1;plan();fft(buffer,n);return 0;}
void retained_fft(C* values,int n){plan();fft(values,n);}
void retained_grid(C* values,int nx,int ny);
__attribute__((export_name("grid"))) int run_grid(int nx,int ny){
 if(nx<1||ny<1||nx>256||ny>256||(nx&(nx-1))||(ny&(ny-1)))return -1;
 retained_grid(buffer,nx,ny);return 0;
}
void retained_grid(C* values,int nx,int ny){
 plan();int stride=ny+1;
 for(int x=0;x<=nx;x++){
  for(int y=0;y<=ny;y++)scratch[y]=values[x*stride+y];
  for(int y=ny+1;y<2*ny;y++)scratch[y]=values[x*stride+2*ny-y];
  fft(scratch,2*ny);
  for(int y=0;y<=ny;y++)values[x*stride+y]=scratch[y];
 }
 for(int y=0;y<=ny;y++){
  for(int x=0;x<=nx;x++)scratch[x]=values[x*stride+y];
  for(int x=nx+1;x<2*nx;x++)scratch[x]=values[(2*nx-x)*stride+y];
  fft(scratch,2*nx);
  for(int x=0;x<=nx;x++)values[x*stride+y]=scratch[x];
 }
}

// Original x87 exponent reduction: FLDL2E, FRNDINT, F2XM1, FSCALE.
// Evaluate 2^fraction-1 in binary128 before its retained-80 store. Fractions
// are in [-0.5,0.5]; 25 terms leave truncation below binary128 precision.
static E negate(E x){x.signExp^=0x8000;return x;}
static E pow2(int n){E x={.signif=0x8000000000000000ULL,.signExp=(uint16_t)(16383+n)};return x;}
static E exp2m1(E x){
 static float128_t reciprocals[26];static int initialized;
 const float128_t one={{0,0x3fff000000000000ULL}};
 const float128_t ln2={{0xf35793c7673007e6ULL,0x3ffe62e42fefa39eULL}};
 if(!initialized){for(int i=2;i<=25;i++)reciprocals[i]=f128_div(one,i32_to_f128(i));initialized=1;}
 float128_t t=f128_mul(extF80_to_f128(x),ln2),q=one;
 for(int i=25;i>=2;i--)q=f128_add(one,f128_mul(f128_mul(t,reciprocals[i]),q));
 return f128_to_extF80(f128_mul(t,q));
}
static E argument(double k,double a,double b){return extF80_mul(load(k),extF80_sub(load(a),load(b)));}
static const E log2e={.signif=0xb8aa3b295c17f0bcULL,.signExp=0x3fff};
static E integral(E x){return extF80_roundToInt(x,softfloat_round_near_even,0);}
static int integer(E x){return extF80_to_i32(x,softfloat_round_near_even,0);}
E retained_exp(E x){
 E e=extF80_mul(x,log2e),i=integral(e),fraction=extF80_sub(e,i);
 if((e.signExp&0x7fff)==0x7fff)return extF80_add(fraction,fraction);
 if(extF80_lt(load(16384),i)){E infinity={.signif=0x8000000000000000ULL,.signExp=0x7fff};return infinity;}
 if(extF80_lt(i,load(-16446)))return load(0);
 int power=integer(i);E result=extF80_add(exp2m1(fraction),load(1));
 // Keep exponent adjustment exact until the final subnormal/overflow store.
 if(power<-16382){result=extF80_mul(result,pow2(power+16382));power=-16382;}
 if(power>16383){result=extF80_mul(result,load(2));power=16383;}
 return extF80_mul(result,pow2(power));
}
static double cosh80(E x,int rounded){
 if(extF80_lt(load(500),x))return 1e15;
 if(rounded)x=load(spill(x));
 if(extF80_lt(x,load(-800)))return spill(pow2(2000));
 E e=extF80_mul(x,log2e),i=integral(e);
 E exponential=extF80_mul(extF80_add(exp2m1(extF80_sub(e,i)),load(1)),pow2(integer(i)));
 return spill(extF80_mul(load(.5),extF80_add(extF80_div(load(1),exponential),exponential)));
}
__attribute__((export_name("cosh"))) double run_cosh(double x){return cosh80(load(x),0);}
double retained_cosh(E x,int rounded){return cosh80(x,rounded);}
__attribute__((export_name("cosh_argument"))) double run_cosh_argument(double k,double a,double b,int rounded){return cosh80(argument(k,a,b),rounded);}
double retained_tanh(E x){
 if((x.signExp&0x7fff)==0x7fff)return spill(extF80_sub(x,x));
 E absolute=x;absolute.signExp&=0x7fff;
 if(extF80_lt(load(25),absolute))return x.signExp&0x8000?-1:1;
 E doubled=extF80_add(x,x);doubled.signExp|=0x8000;
 E e=extF80_mul(doubled,log2e),i=integral(e),whole=pow2(integer(i));
 E part=extF80_mul(exp2m1(extF80_sub(e,i)),whole);
 E em1=extF80_add(extF80_sub(whole,load(1)),part);
 E fraction=extF80_div(em1,extF80_add(em1,load(2)));
 return spill(extF80_mul(fraction,load(extF80_le(x,load(0))?1:-1)));
}
__attribute__((export_name("tanh_argument"))) double run_tanh_argument(double k,double a,double b){return retained_tanh(argument(k,a,b));}

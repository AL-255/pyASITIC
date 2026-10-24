// Original RESIS / RESISHF from recomp_cpp/src/resistance.cpp.
#include "retained_math.hpp"
extern "C" extFloat80_t retained_exp2(extFloat80_t);
namespace {
using R=SoftReal;using asitic::x87::binary64;
constexpr int limit=20000,stride=12;
static double records[limit*stride],results[4];
// FISTPLL with truncation and the original integer-indefinite result. The
// bundled SoftFloat subset exposes only i32 conversions; inspect the exact
// extended significand/exponent here instead of narrowing through binary64.
int64_t truncate64(R x){
 const int exponent=int(x.value.signExp&0x7fff)-16383;
 if(exponent<0)return 0;
 if(exponent>=63)return -9223372036854775807LL-1;
 const int64_t magnitude=int64_t(x.value.signif>>(63-exponent));
 return x.value.signExp&0x8000?-magnitude:magnitude;
}
double power(R base,R exponent){
 const int64_t integer=truncate64(exponent);
 if(base==R(0.)&&exponent>R(0.))return 0.;
 const uint64_t magnitude=integer<0?uint64_t(0)-uint64_t(integer):uint64_t(integer);
 R integral=R(double(uint32_t(magnitude>>32)))*R(0x1p32)+R(double(uint32_t(magnitude)));
 if(integer<0)integral=-integral;
 if(integral==exponent){
  uint64_t remaining=uint64_t(integer);R result(1.);
  while(remaining){if(remaining&1)result=base*result;remaining>>=1;if(remaining)base=base*base;}
  return binary64(result);
 }
 return binary64(R(retained_exp2((exponent*asitic::x87::log2(base)).value)));
}
R high_factor(R u,R aspect){
 const double aspect64=binary64(aspect),first=power(aspect,R(0x1.30a3d70a3d70ap+0)),cube=power(u,R(3.)),last=power(R(aspect64)-R(1.),R(0x1.ccccccccccccdp+0));
 const R skin=(R(0x1.b945b6c3760bfp-2)*u)/(R(0x1.4fdf3b645a1cbp-5)*R(first)+R(1.));
 const R fraction=(R(0x1.496bb98c7e282p+0)*u+R(0x1.1d5cfaacd9e84p+0))/(R(0x1.4978d4fdf3b64p+0)*R(cube)+R(0x1.3ac710cb295eap+0));
 return (skin+fraction)+R(0x1.cac083126e979p-9)*R(last);
}
}
extern "C" __attribute__((export_name("conductor_resistance_buffer"))) unsigned conductor_resistance_buffer(){return reinterpret_cast<unsigned>(records);}
extern "C" __attribute__((export_name("conductor_resistance_result_buffer"))) unsigned conductor_resistance_result_buffer(){return reinterpret_cast<unsigned>(results);}
extern "C" __attribute__((export_name("conductor_resistance"))) int conductor_resistance(int count,int operation,double frequency){
 if(count<0||count>limit||operation<0||operation>1||!(frequency>=0.)||__builtin_isinf(frequency))return -1;
 R total(0.);
 for(int i=0;i<count;i++){
  const double* row=records+stride*i;R contribution;
  if(row[9]){
   const int32_t nx=int32_t(row[10]),ny=int32_t(row[11]);
   const int32_t cells=int32_t(uint32_t(nx)*uint32_t(ny));contribution=R(row[8])/R(cells);
  }else{
   const R dx=R(row[3])-R(row[0]),dy=R(row[4])-R(row[1]),dz=R(row[5])-R(row[2]),width(row[6]),sheet(row[8]);
   const R dc=(asitic::x87::sqrt((dz*dz+dy*dy)+dx*dx)/width)*sheet;
   if(!operation)contribution=dc;
   else{
    const R u=asitic::x87::sqrt(((((R(frequency)*R(0x1.921fb544418ecp+4))*R(0x1.12e0be826d695p-30))*width)*R(0x1.a36e2eb1c432dp-14))/sheet);
    R factor;
    if(u>=R(2.5))factor=high_factor(u,width/R(row[7]));
    else{const double p=power(u,R(3.)+(R(0x1.47ae147ae147bp-7)*u)*u);factor=R(0x1.8fc504816f007p-7)*R(p)+R(1.);}
    contribution=factor*dc;
   }
  }
  total=contribution+total;if(operation)total=R(binary64(total));
 }
 results[0]=binary64(total);results[1]=double(uint32_t(total.value.signif));results[2]=double(uint32_t(total.value.signif>>32));results[3]=total.value.signExp;
 return 0;
}

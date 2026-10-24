// Original geometry_reporting.cpp GEOM stores and METALAREA retained loop.
#include "soft_real.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
constexpr int limit=20000;
static double records[limit*7],results[6];
R memory_operand(double value){
 union{double d;uint64_t word;}bits={.d=value};
 if((bits.word&0x7ff0000000000000ULL)==0x7ff0000000000000ULL&&(bits.word&0xfffffffffffffULL))
  return R(extFloat80_t{.signif=0x8000000000000000ULL|((bits.word&0xfffffffffffffULL)<<11),.signExp=uint16_t(0x7fff|((bits.word>>48)&0x8000))});
 return R(value);
}
}
extern "C" __attribute__((export_name("geometry_metrics_buffer"))) unsigned geometry_metrics_buffer(){return reinterpret_cast<unsigned>(records);}
extern "C" __attribute__((export_name("geometry_metrics_result_buffer"))) unsigned geometry_metrics_result_buffer(){return reinterpret_cast<unsigned>(results);}
extern "C" __attribute__((export_name("geometry_metrics"))) int geometry_metrics(int count){
 if(count<0||count>limit)return -1;
 double total_length=0.,total_area=0.;R metal_area(0.);const R epsilon(0x1.b7cdfd9d7bdbbp-34);
 for(int i=0;i<count;i++){
  const double* p=records+7*i;const R dx=R(p[3])-memory_operand(p[0]),dy=R(p[4])-memory_operand(p[1]),dz=R(p[5])-memory_operand(p[2]);
  const R length=asitic::x87::sqrt((dx*dx+dy*dy)+dz*dz),width(p[6]),area=length*width;
  total_length=binary64(R(total_length)+length);total_area=binary64(area+R(total_area));
  if(length>epsilon)metal_area=area+metal_area;
 }
 results[0]=total_length;results[1]=total_area;results[2]=binary64(metal_area);results[3]=double(uint32_t(metal_area.value.signif));results[4]=double(uint32_t(metal_area.value.signif>>32));results[5]=metal_area.value.signExp;return 0;
}

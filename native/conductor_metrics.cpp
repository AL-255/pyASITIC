// Original analysis_commands.cpp INDUCTANCE and retained resistance_dc input.
#include "mutual_port.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
constexpr int limit=2000,stride=16;
static double records[limit*stride],geometry[limit*8],results[9];
void save(int i,R x){results[i]=binary64(x);results[i+1]=double(uint32_t(x.value.signif));results[i+2]=double(uint32_t(x.value.signif>>32));results[i+3]=x.value.signExp;}
}
extern "C" __attribute__((export_name("conductor_metrics_buffer"))) unsigned conductor_metrics_buffer(){return reinterpret_cast<unsigned>(records);}
extern "C" __attribute__((export_name("conductor_metrics_result_buffer"))) unsigned conductor_metrics_result_buffer(){return reinterpret_cast<unsigned>(results);}
extern "C" __attribute__((export_name("conductor_metrics"))) int conductor_metrics(int count){
 if(count<0||count>limit)return -1;
 const R scale(0x1.a36e2eb1c432dp-14),epsilon(0x1.b7cdfd9d7bdbbp-34);
 R self(0.),mutual(0.),dc(0.);int warnings=0;bool failed=false;
 for(int i=0;i<count;i++){
  const double* p=records+stride*i;const R dx=R(p[3])-R(p[0]),dy=R(p[4])-R(p[1]),dz=R(p[5])-R(p[2]);R length,width,thickness,contribution;
  if(p[9]){
   length=asitic::x87::abs(dz)*scale;width=(scale*R(p[10]))*R(p[12]);thickness=(scale*R(p[11]))*R(p[13]);
   const int32_t cells=int32_t(uint32_t(int32_t(p[10]))*uint32_t(int32_t(p[11])));contribution=R(p[8])/R(cells);
  }else{
   length=asitic::x87::sqrt((dx*dx+dy*dy)+dz*dz)*scale;width=R(p[6])*scale;thickness=R(p[7])*scale;
   contribution=(asitic::x87::sqrt((dz*dz+dy*dy)+dx*dx)/R(p[6]))*R(p[8]);
   double* g=geometry+8*i;for(int k=0;k<6;k++)g[k]=p[k];g[6]=p[14];g[7]=p[15];
  }
  dc=contribution+dc;
  if(length>epsilon){const R twice=length+length,sum=width+thickness;const R logarithm=asitic::x87::log(twice/sum)+R(0x1.004039abf3387p-1);const R term=twice*(sum/(R(3.)*length)+logarithm);self=term+self;}
 }
 for(int i=0;i<count&&!failed;i++)if(!records[stride*i+9])for(int j=i+1;j<count;j++)if(!records[stride*j+9]){
  double pair=0.;int warning=0;const int status=asitic::segment_mutual_value(geometry+8*i,geometry+8*j,&pair,warning);
  if(warning)warnings|=1<<warning;
  if(status==-1){failed=true;break;}mutual=mutual+R(pair);
 }
 save(0,failed?R(0.):(mutual+mutual)+self);save(4,dc);results[8]=warnings;return 0;
}

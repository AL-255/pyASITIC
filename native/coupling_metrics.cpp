// Original analysis_commands.cpp shape_coupling_estimate: F64 mutable history.
#include "mutual_port.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
constexpr int limit=2000,capacity=2*limit*8+6;
static double inputs[capacity],outputs[capacity];
void translate(double* p,const double* origin,bool subtract){
 const int indices[]={0,1,3,4};for(int k:indices)p[k]=binary64(subtract?R(p[k])-R(origin[k%3]):R(p[k])+R(origin[k%3]));
}
}
extern "C" __attribute__((export_name("coupling_metrics_buffer"))) unsigned coupling_metrics_buffer(){return reinterpret_cast<unsigned>(inputs);}
extern "C" __attribute__((export_name("coupling_metrics_result_buffer"))) unsigned coupling_metrics_result_buffer(){return reinterpret_cast<unsigned>(outputs);}
extern "C" __attribute__((export_name("coupling_metrics"))) int coupling_metrics(int na,int nb){
 if(na<0||nb<0||na>limit||nb>limit||na*nb>1000000)return -1;
 const int size=8*(na+nb);const double* config=inputs+size;
 for(int i=0;i<size;i++)outputs[i]=inputs[i];
 double sum=0.;int warnings=0;
 for(int i=0;i<na;i++)for(int j=0;j<nb;j++){
  double* a=outputs+8*i;double* b=outputs+8*(na+j);translate(a,config,false);translate(b,config+2,false);
  double pair=0.;int warning=0;const int status=asitic::segment_mutual_value(a,b,&pair,warning);
  if(warning)warnings|=1<<warning;
  if(status==-1)return -2;
  sum=binary64(R(sum)+R(pair));translate(a,config,true);translate(b,config+2,true);
 }
 const R l1(config[4]),l2(config[5]),epsilon(0x1.b7cdfd9d7bdbbp-34);
 const R coefficient=epsilon<l1&&epsilon<l2?R(sum)/asitic::x87::sqrt(l1*l2):R(0.);
 outputs[size]=sum;outputs[size+1]=binary64(coefficient);outputs[size+2]=double(uint32_t(coefficient.value.signif));outputs[size+3]=double(uint32_t(coefficient.value.signif>>32));outputs[size+4]=coefficient.value.signExp;outputs[size+5]=warnings;return 0;
}

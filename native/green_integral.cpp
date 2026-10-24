// Original Green reflection integration, with complete retained QUADPACK flow.
#include "green_integral_port.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
static double left[1000],right[1000],areas[1000],errors[1000],moments[1250];
static double cycle_integrals[1000],cycle_errors[1000];
static int order[1000],levels[1000],cycle_statuses[1000];
static double active_height;static asitic::GreenStats* active_stats;
static double trace[65536];
static extFloat80_t cutoff;static bool planned;
R reflection(const double* point){
 auto& stats=*active_stats;if(!stats.observations)stats.first=*point;
 if(stats.observations<65536)trace[stats.observations]=*point;
 stats.last=*point;stats.observations++;
 const R kh=R(*point)*R(active_height);
 if(kh>=R(cutoff))return R(0.);
 return asitic::x87::exp(-kh);
}
}
namespace asitic {
SoftReal integrate_reflection(double frequency,double separation,double height,GreenState& state,GreenStats& stats){
 if(!planned){cutoff=x87::log(R(0x1.fffffep127)).value;planned=true;}
 stats={};active_height=height;active_stats=&stats;
 const quadpack::InfiniteWorkspace intervals{left,right,areas,errors,order,500};
 if(x87::abs(R(separation))<R(0x1.b7cdfd9d7bdbbp-34)){
  double sample=0.;
  for(;;){reflection(&sample);const R next=R(sample)+R(0x1.a36e2eb1c432dp-14);sample=binary64(next);if(!(next<R(0x1.47ae147ae147bp-7)))break;}
  auto w=intervals;w.limit=200;
  const auto value=quadpack::integrate_infinite(reflection,0.,1,0.,0x1.0c6f7a0b5ed8dp-20,w);
  stats.integral=value.integral;stats.error=value.error;stats.status=value.status;stats.evaluations=value.evaluations;stats.intervals=value.intervals;
 }else{
  const quadpack::FourierWorkspace w{{intervals,levels},cycle_integrals,cycle_errors,cycle_statuses,1000,moments,50,state.history};
  const auto value=quadpack::integrate_fourier(reflection,0.,separation,1,0x1.47ae147ae147bp-7,w,{x87::libm_sin,x87::libm_cos});
  stats.integral=value.integral;stats.error=value.error;stats.status=value.status;stats.evaluations=value.evaluations;stats.cycles=value.cycles;
 }
 return (-R(stats.integral)*R(0x1.515370f99f6cbp-20))*R(frequency);
}
}
static double config[8],result[32+3000];
extern "C" __attribute__((export_name("green_config_buffer"))) unsigned green_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("green_trace_buffer"))) unsigned green_trace_buffer(){return reinterpret_cast<unsigned>(trace);}
extern "C" __attribute__((export_name("green_result_buffer"))) unsigned green_result_buffer(){return reinterpret_cast<unsigned>(result);}
extern "C" __attribute__((export_name("green_reflection_integral"))) int green_reflection_integral(){
 asitic::GreenState state{{config[4],config[5],config[6]}};asitic::GreenStats stats;
 const R value=asitic::integrate_reflection(config[0],config[1],config[2],state,stats);
 const double values[]={binary64(value),stats.integral,stats.error,double(stats.status),double(stats.evaluations),double(stats.observations),stats.first,stats.last,double(stats.intervals),double(stats.cycles),state.history[0],state.history[1],state.history[2],double(unsigned(value.value.signif)),double(unsigned(value.value.signif>>32)),double(value.value.signExp)};
 for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++)result[i]=values[i];
 for(int i=0;i<stats.cycles;i++){result[32+i]=cycle_integrals[i];result[1032+i]=cycle_errors[i];result[2032+i]=cycle_statuses[i];}
 return 0;
}

#include "green_port.hpp"
namespace {static double input[256*9],output[256*6];}
extern "C" __attribute__((export_name("layered_green_buffer"))) unsigned layered_green_buffer(){return reinterpret_cast<unsigned>(input);}
extern "C" __attribute__((export_name("layered_green_result_buffer"))) unsigned layered_green_result_buffer(){return reinterpret_cast<unsigned>(output);}
extern "C" __attribute__((export_name("layered_green_probe"))) int layered_green_probe(int count){
 if(count<1||count>256)return -1;
 using namespace asitic;using R=SoftReal;
 for(int i=0;i<count;i++){
  const double* p=input+9*i+1;const int mode=int(input[9*i]);if(mode<0||mode>13)return -1;
  const GreenLayers layers{p[2],p[3],p[4]};ComplexValue z{0,0};R scalar(0.);
  if(mode==0||mode==1)z=green_propagation_constant(p[0],p[1],mode?p[3]:p[2]);
  if(mode==2)z=green_complex_tanh({p[0],p[1]});
  if(mode==3)scalar=green_reflection_imag(p[0],p[1],p[2]);
  if(mode==4)scalar=green_oscillating_integrand(p[0],p[1],layers);
  if(mode==5)scalar=green_propagation_integrand(p[1],layers);
  if(mode==6)scalar=green_oscillating_kernel(p[0],p[1],layers,p[5],p[6]);
  if(mode==7)scalar=green_reflection_kernel(p[0],p[5]);
  if(mode==8)z=legacy::square_root({p[0],p[1]});
  if(mode==9)z=legacy::exp({p[0],p[1]});
  if(mode==10)z=legacy::sinh({p[0],p[1]});
  if(mode==11)z=legacy::cosh({p[0],p[1]});
  if(mode>=12){R x(p[0]);if(p[7]==3)x*=R(p[1]);scalar=mode==12?x87::wide_cos(x):x87::wide_sin(x);}
  if((mode>=3&&mode<=7)||mode>=12)z.real=x87::binary64(scalar);
  double* r=output+6*i;r[0]=0.;r[1]=z.real;r[2]=z.imag;
  r[3]=double(unsigned(scalar.value.signif));r[4]=double(unsigned(scalar.value.signif>>32));r[5]=scalar.value.signExp;
 }
 return 0;
}

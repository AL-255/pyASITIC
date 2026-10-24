#include "network_port.hpp"
namespace {static double input[256*26],output[256*42];}
extern "C" __attribute__((export_name("network_metric_buffer"))) unsigned network_metric_buffer(){return reinterpret_cast<unsigned>(input);}
extern "C" __attribute__((export_name("network_metric_result_buffer"))) unsigned network_metric_result_buffer(){return reinterpret_cast<unsigned>(output);}
extern "C" __attribute__((export_name("network_metrics"))) int network_metrics(int count,int operation){
 if(count<1||count>256||operation<0||operation>3)return -1;
 using namespace asitic;
 for(int i=0;i<count;i++){
  const double* p=input+26*i;double* r=output+42*i;
  if((p[0]!=0.&&p[0]!=1.)||(p[2]!=0.&&p[2]!=1.&&p[2]!=2.)||(p[3]!=0.&&p[3]!=1.))return -1;
  for(int k=0;k<42;k++)r[k]=0.;
  const TwoPortAdmittance y{{p[6],p[7]},{p[8],p[9]},{p[10],p[11]},{p[12],p[13]}};
  if(operation==0||operation==3){
  const PiEquivalent model=p[0]==0.?extract_pi_equivalent(y,p[1]):PiEquivalent{p[14],p[15],p[16],p[17],p[18],p[19],p[20],p[21],p[22],p[23],p[24],p[25]};
  const double* values=reinterpret_cast<const double*>(&model);r[0]=0.;for(int k=0;k<12;k++)r[k+1]=values[k];
  const SoftReal scalars[]={pi_shunt_resistance(model,0),pi_shunt_resistance(model,1),pi_resonant_frequency(model)};
  for(int k=0;k<3;k++){
   r[13+k]=x87::binary64(scalars[k]);r[29+3*k]=double(unsigned(scalars[k].value.signif));r[30+3*k]=double(unsigned(scalars[k].value.signif>>32));r[31+3*k]=scalars[k].value.signExp;
  }
  }
  if(operation==1||operation==3){
  const auto z=two_port_impedance(y,p[3]!=0.,int(p[2]));r[16]=z.real;r[17]=z.imag;
  const auto imag=two_port_imaginary_impedance(y,int(p[3]));r[18]=x87::binary64(imag);
  const auto terminated=terminated_two_port_impedance(y,{p[4],p[5]},int(p[2]));r[19]=terminated.real;r[20]=terminated.imag;
  r[38]=double(unsigned(imag.value.signif));r[39]=double(unsigned(imag.value.signif>>32));r[40]=imag.value.signExp;
  }
  if(operation==2||operation==3){
  const auto s=convert_two_port_scattering(y);const ComplexValue cells[]={s.s11,s.s12,s.s21,s.s22};
  for(int k=0;k<4;k++){r[21+2*k]=cells[k].real;r[22+2*k]=cells[k].imag;}
  }
 }
 return 0;
}

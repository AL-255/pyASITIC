// Original transformer reciprocal conversion and narrowband extraction.
#include "contact_port.hpp"
namespace asitic {
struct TwoPortAdmittance{ComplexValue y11,y12,y21,y22;};
struct LaterTwoPortImpedance{ComplexValue z11,z12,z21,z22;};
struct TransformerEquivalent{double first_inductance,second_inductance,first_resistance,second_resistance,ground_resistance,mutual,coupling;};
namespace {
SoftReal load(const double& value){return SoftReal(value);}
void raw_copy(ComplexValue& out,const ComplexValue& in){out=in;}
}
LaterTwoPortImpedance invert_transformer_admittance(const TwoPortAdmittance& y) {
    const SoftReal ar=load(y.y11.real),ai=load(y.y11.imag),br=load(y.y22.real),bi=load(y.y22.imag);
    const SoftReal pr=br*ar-bi*ai,pi=ar*bi+br*ai;
    // These native stores round a discarded copy while the live products
    // remain extended. Retain the stores for their floating-point effects.
    volatile double dead_pr=x87::binary64(pr),dead_pi=x87::binary64(pi);(void)dead_pr;(void)dead_pi;
    const SoftReal cr=load(y.y21.real),ci=load(y.y21.imag);
    const SoftReal sr=cr*cr-ci*ci,si=(cr*ci)+(cr*ci);
    volatile double dead_sr=x87::binary64(sr),dead_si=x87::binary64(si);(void)dead_sr;(void)dead_si;
    const ComplexValue determinant{x87::binary64(pr-sr),x87::binary64(pi-si)};
    LaterTwoPortImpedance out;
    // The original labels use y11 for z11, rather than swapping diagonals.
    out.z11=legacy::divide(y.y11,determinant);out.z22=legacy::divide(y.y22,determinant);
    const ComplexValue negative{x87::binary64(-load(y.y21.real)),x87::binary64(-load(y.y21.imag))};
    out.z12=legacy::divide(negative,determinant);raw_copy(out.z21,out.z12);return out;
}
TransformerEquivalent extract_transformer_equivalent(const TwoPortAdmittance& y,double frequency,LaterTwoPortImpedance& z) {
    const SoftReal f=load(frequency);z=invert_transformer_admittance(y);
    const SoftReal ai=load(z.z11.imag),ci=load(z.z12.imag);
    volatile double dead_first=x87::binary64(ai-ci);(void)dead_first;
    const SoftReal cr=load(z.z12.real),ar=load(z.z11.real);
    const SoftReal omega=f*SoftReal(0x1.921fb54442d18p+2);
    const SoftReal l1=ai/omega,r1=ar-cr;
    volatile double dead_r1=x87::binary64(r1);(void)dead_r1;
    const SoftReal bi=load(z.z22.imag),l2=bi/omega,m=-ci/omega;
    const SoftReal r2=load(z.z22.real)-cr;
    volatile double dead_r2=x87::binary64(r2),dead_second=x87::binary64(bi-ci);(void)dead_r2;(void)dead_second;
    // Coupling uses the live extended inductances, before their output spills.
    const SoftReal coupling=m/x87::sqrt(l1*l2);
    return {x87::binary64(l1),x87::binary64(l2),x87::binary64(r1),x87::binary64(r2),x87::binary64(cr),x87::binary64(m),x87::binary64(coupling)};
}

}
static double data[24];
extern "C" __attribute__((export_name("transformer_buffer"))) unsigned transformer_buffer(){return reinterpret_cast<unsigned>(data);}
extern "C" __attribute__((export_name("transformer_model"))) int transformer_model(int operation){
 if(operation<0||operation>1)return -1;
 using namespace asitic;
 const TwoPortAdmittance y{{data[1],data[2]},{data[3],data[4]},{data[5],data[6]},{data[7],data[8]}};
 LaterTwoPortImpedance z;
 if(operation){
  const auto m=extract_transformer_equivalent(y,data[0],z);
  const double values[]={m.first_inductance,m.second_inductance,m.first_resistance,m.second_resistance,m.ground_resistance,m.mutual,m.coupling};
  for(int i=0;i<7;i++)data[17+i]=values[i];
 }else z=invert_transformer_admittance(y);
 const ComplexValue values[]={z.z11,z.z12,z.z21,z.z22};
 for(int i=0;i<4;i++){data[9+2*i]=values[i].real;data[10+2*i]=values[i].imag;}
 return 0;
}

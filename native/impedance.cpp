// Retained assembly formulas from recomp_cpp/src/impedance.cpp.
// Filament construction and unscaled mutual terms keep their existing exact
// kernels/caches; this stage retains self terms and frequency weighting.
#include "contact_port.hpp"
#include "retained_math.hpp"
namespace {
using R=SoftReal;using C=asitic::ComplexValue;using asitic::x87::binary64;
static double wires[256*10],mutual[256*255/2];static C matrix[256*256];
C self(const double* p,double omega){
 const double* a=p+2;
 const R dx=R(a[3])-a[0],dy=R(a[4])-a[1],dz=R(a[5])-a[2];
 const R length=asitic::x87::sqrt((dx*dx+dy*dy)+dz*dz);
 double inductance=0.;R resistance(0.);
 if(R(0x1.b7cdfd9d7bdbbp-34)<length){
  const R width=a[6],thickness=a[7],sum=width+thickness;
  inductance=binary64((length*R(0x1.a36e2eb1c432dp-13))*((asitic::x87::log((length+length)/sum)+R(0x1.004039abf3387p-1))+sum/(length*R(3.))));
  resistance=((length/width)*R(p[0]))*R(p[1]);
 }
 return {binary64(resistance),binary64(R(omega)*R(inductance))};
}
}
extern "C" __attribute__((export_name("impedance_wire_buffer"))) unsigned impedance_wire_buffer(){return reinterpret_cast<unsigned>(wires);}
extern "C" __attribute__((export_name("impedance_mutual_buffer"))) unsigned impedance_mutual_buffer(){return reinterpret_cast<unsigned>(mutual);}
extern "C" __attribute__((export_name("impedance_matrix_buffer"))) unsigned impedance_matrix_buffer(){return reinterpret_cast<unsigned>(matrix);}
extern "C" __attribute__((export_name("impedance_assemble"))) int impedance_assemble(int n,double frequency){
 if(n<1||n>256)return -1;
 const double omega=binary64(R(0x1.12e0be826d695p-30)*R(binary64(R(0x1.921fb54442d18p+2)*R(frequency))));
 int pair=0;
 for(int i=0;i<n;i++){
  matrix[i*n+i]=self(wires+10*i,omega);
  for(int j=i+1;j<n;j++){
   const C value{0.,binary64(R(omega)*R(mutual[pair++]))};
   matrix[j*n+i]=matrix[i*n+j]=value;
  }
 }
 return 0;
}

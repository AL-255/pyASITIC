// Retained-arithmetic port of vias.cpp, original entry 0x080657b8.
#include "retained_math.hpp"

static double input[256*9],output[256*2];
extern "C" __attribute__((export_name("via_buffer"))) unsigned via_buffer(){return reinterpret_cast<unsigned>(input);}
extern "C" __attribute__((export_name("via_result_buffer"))) unsigned via_result_buffer(){return reinterpret_cast<unsigned>(output);}
extern "C" __attribute__((export_name("via_stamp"))) int via_stamp(int count){
 if(count<1||count>256)return -1;
 using R=SoftReal;using asitic::x87::binary64;
 for(int i=0;i<count;i++){
  const double* p=input+9*i;double* z=output+2*i;
  // frequency, start/end Z, perimeter step, resistance, width/thickness
  // counts, existing matrix real/imaginary. Preserve the original stores.
  const R height=R(p[2])-R(p[1]);z[0]=p[7];z[1]=p[8];
  if(!(height>R(0x1.b7cdfd9d7bdbbp-34)))continue;
  const int nx=static_cast<int>(p[5]),ny=static_cast<int>(p[6]);
  const int cells=static_cast<int>(static_cast<unsigned>(nx)*static_cast<unsigned>(ny));
  const R perimeter=R(p[3])*R(ny)+R(p[3])*R(nx);
  const R resistance=R(p[4])/R(cells);
  const double omega=binary64(R(0x1.921fb54442d18p+2)*R(p[0]));
  const R inductance=(height*R(0x1.a36e2eb1c432dp-13))*
   ((asitic::x87::log((height+height)/perimeter)+R(0x1.004039abf3387p-1))+perimeter/(height*R(3.)));
  const double reactance=binary64((inductance*R(omega))*R(0x1.12e0be826d695p-30));
  z[0]=binary64(R(p[7])+resistance);z[1]=binary64(R(p[8])+R(reactance));
 }
 return 0;
}

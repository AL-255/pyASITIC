// Polygon spiral arithmetic/stores from recomp_cpp/src/spiral_construction.cpp.
#include "retained_math.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
static double config[6],vertices[20000*12];
void vertex(double* p,R theta,R radius,double ribbon,bool initial){
 const R cosine=asitic::x87::wide_cos(theta),sine=asitic::x87::wide_sin(theta);
 const R half=initial?R(binary64(R(ribbon)*R(.5))):R(ribbon)*R(.5);
 p[0]=binary64(cosine*(radius-half));p[1]=binary64(sine*(radius-half));
 p[2]=binary64(cosine*radius);p[3]=binary64(sine*radius);
 p[4]=binary64(cosine*(radius-R(ribbon)));p[5]=binary64(sine*(radius-R(ribbon)));
}
}
extern "C" __attribute__((export_name("polygon_config_buffer"))) unsigned polygon_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("polygon_vertex_buffer"))) unsigned polygon_vertex_buffer(){return reinterpret_cast<unsigned>(vertices);}
extern "C" __attribute__((export_name("polygon_spiral"))) int polygon_spiral(){
 const double sides=config[1],turns=config[4];
 if(sides<3||sides>1024||sides!=int(sides)||!(turns>0.)||!(config[0]>0.)||!(config[2]>0.)||config[3]<0.)return -1;
 const R angle=config[5],initial=config[0],n=sides;
 const R sector=R(0x1.921fb54442d18p+1)/n;
 const double ribbon=binary64(R(config[2])/asitic::x87::wide_cos(sector));
 const double shrink=binary64(((R(config[2])+R(config[3]))*R(turns))/asitic::x87::wide_cos(R(binary64(sector))));
 const double decrement=binary64((initial-(initial-R(shrink)))/(R(turns)*n));
 const int last=extF80_to_i32((R(turns)+R(1.)).value,softfloat_round_minMag,false);
 const double floor_turns=binary64(R(extF80_roundToInt(R(turns).value,softfloat_round_min,false)));
 R radius=initial;int used=0;
 for(int turn=1;turn<=last;turn++){
  double first[6];vertex(first,angle,radius,ribbon,true);
  const int count=turn==last?extF80_to_i32(((R(turns)-R(floor_turns))*n+R(1.)/(n+n)).value,softfloat_round_minMag,false):int(sides);
  for(int side=1;side<=count;side++){
   if(used>=20000)return -1;
   radius-=R(decrement);if(radius<R(0x1.b7cdfd9d7bdbbp-34))return -2;
   const R theta=(R(0x1.921fb54442d18p+2)*R(side))/n+angle;
   double next[6];vertex(next,theta,radius,ribbon,false);double* out=vertices+12*used++;
   for(int k=0;k<3;k++)for(int axis=0;axis<2;axis++){out[4*k+axis]=first[2*k+axis];out[4*k+2+axis]=next[2*k+axis];}
   for(int k=0;k<6;k++)first[k]=next[k];
  }
 }
 if(!used)return -1;
 double x0=1e15,y0=1e15,x1=-1e15,y1=-1e15;
 const int offsets[]={4,6,8,10,0,2};
 for(int row=0;row<used;row++)for(int k:offsets){const double x=vertices[12*row+k],y=vertices[12*row+k+1];if(x<x0)x0=x;if(x1<x)x1=x;if(y<y0)y0=y;if(y1<y)y1=y;}
 const double dx=binary64((R(x1)-R(x0))*R(.5)),dy=binary64((R(y1)-R(y0))*R(.5));
 for(int row=0;row<used;row++)for(int k:offsets){vertices[12*row+k]=binary64(R(vertices[12*row+k])+R(dx));vertices[12*row+k+1]=binary64(R(vertices[12*row+k+1])+R(dy));}
 return used;
}

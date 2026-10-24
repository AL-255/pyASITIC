// Literal retained state machines from symmetric_construction.cpp. Output
// events preserve conductor/via ordering; Python resolves process metal/vias.
#include "retained_math.hpp"
namespace {
using R=SoftReal;using asitic::x87::binary64;
static double config[10],events[60000*14];
static int used;
struct Segment {double p[12]{};int metal;};
void collapse(Segment& s){for(int k=0;k<3;k++)for(int a=0;a<2;a++)s.p[4*k+a]=s.p[4*k+2+a];}
bool conductor(const Segment& s){
 if(used>=60000)return false;double* p=events+14*used++;p[0]=0;p[1]=s.metal;
 for(int i=0;i<12;i++)p[i+2]=s.p[i];return true;
}
bool via(const Segment& s,int metal,int dy){
 if(used>=60000)return false;double* p=events+14*used++;p[0]=1;p[1]=metal;p[2]=s.p[2];p[3]=s.p[3];p[4]=dy;
 for(int i=5;i<14;i++)p[i]=0;return true;
}
void extend(int direction,Segment& s,double length,double inset){
 collapse(s);R w=inset;if(direction>1)w+=w;
 const R sign=direction==0||direction==3?R(1):R(-1);const int axis=direction<2?1:0;
 s.p[6+axis]=binary64(sign*R(length)+R(s.p[6+axis]));
 s.p[10+axis]=binary64(sign*(R(length)-w)+R(s.p[10+axis]));
 s.p[2+axis]=binary64(sign*(R(length)-w*R(.5))+R(s.p[2+axis]));
}
void bridge(int direction,Segment& s,double height,double width,double spacing){
 collapse(s);const R sx=direction==4||direction==6?R(-1):R(1),sy=direction==6||direction==7?R(-1):R(1);
 const R dx=(R(spacing)+R(width))*sx,dy=(R(height)-R(0))*sy;
 const int ends[]={10,6,2};for(int k:ends){s.p[k]=binary64(R(s.p[k])+dx);s.p[k+1]=binary64(R(s.p[k+1])+dy);}
}
void endpoint(Segment& s,double angle,R outer_angle,double radius,double width,int sides,R half,bool initial){
 const R c=binary64(asitic::x87::wide_cos(R(0x1.921fb54442d18p+1)/R(sides)));
 const R cosine=asitic::x87::wide_cos(R(angle)),sine=asitic::x87::wide_sin(R(angle));
 s.p[10]=binary64(asitic::x87::wide_cos(outer_angle)*R(radius));
 const R y=sine*R(radius);s.p[11]=binary64((initial?R(binary64(y)):y)+half);
 const R center=R(radius)-R(width)/(c+c),outer=R(radius)-R(width)/c;
 s.p[2]=binary64(cosine*center);s.p[3]=binary64(center*sine+half);
 s.p[6]=binary64(cosine*outer);s.p[7]=binary64(sine*outer+half);
}
int square(){
 const int primary=int(config[1]),secondary=int(config[2]);double span=config[3];
 const double height=config[5],width=config[6],spacing=config[7],turns=config[8];
 Segment s{};s.metal=primary;s.p[2]=binary64(R(width)*R(.5));
 s.p[3]=binary64(R(span)*R(.5)+R(height));s.p[6]=0;s.p[10]=width;s.p[7]=s.p[11]=s.p[3];
 double vertical=binary64((R(span)-R(height))*R(.5)),progress=0;int state=0,side=0,bridge_metal=primary;
 while(R(progress)<=R(turns)-R(.5)){
  progress=binary64(R(progress)+R(.25));++side;s.metal=primary;
  if(state>3){bridge_metal=bridge_metal==primary?secondary:primary;s.metal=bridge_metal;}
  switch(state){
   case 0:extend(0,s,vertical,width);state=side<3?3:5;break;
   case 1:extend(1,s,vertical,width);state=side<3?2:6;break;
   case 2:extend(2,s,span,width);state=0;break;
   case 3:extend(3,s,span,width);state=1;break;
   default:{const int direction=state,dy=state==5?-1:1;
    if(!via(s,bridge_metal,dy))return -1;bridge(direction,s,height,width,spacing);if(!via(s,bridge_metal,-dy))return -1;
    const R pitch=R(width)+R(spacing);span=binary64(R(span)-(pitch+pitch));vertical=binary64(R(vertical)-pitch);state=direction==5?0:1;side=0;break;}
  }
  if(!conductor(s))return -1;
 }
 collapse(s);const bool down=state==6;const R center=R(height)*R(.5);
 for(int i=0;i<2;i++){
  const int ends[]={7,11,3};for(int k:ends)s.p[k]=binary64(down?R(s.p[k])-center:R(s.p[k])+center);
  if(!conductor(s))return -1;collapse(s);
 }
 state=down?1:0;side=0;
 while(R(0)<R(progress)){
  progress=binary64(R(progress)-R(.25));++side;s.metal=primary;
  if(state>3){bridge_metal=bridge_metal==primary?secondary:primary;s.metal=bridge_metal;}
  switch(state){
   case 0:extend(0,s,vertical,width);state=side<3?3:4;break;
   case 1:extend(1,s,vertical,width);state=side<3?2:7;break;
   case 2:extend(2,s,span,width);state=0;break;
   case 3:extend(3,s,span,width);state=1;break;
   default:{const int direction=state;
    if(!via(s,bridge_metal,-1))return -1;bridge(direction,s,height,width,spacing);if(!via(s,bridge_metal,1))return -1;
    const R pitch=R(width)+R(spacing);span=binary64((pitch+pitch)+R(span));vertical=binary64(pitch+R(vertical));state=direction==4?0:1;side=0;break;}
  }
  if(!conductor(s))return -1;
 }
 return used;
}
int polygon(){
 const int primary=int(config[1]),secondary=int(config[2]),sides=int(config[4]);double radius=config[3],angle=config[9];
 const double height=config[5],width=config[6],spacing=config[7],turns=config[8];
 const R initial_half=R(height)*R(.5);double half=binary64(initial_half);int bridge_metal=0;
 const R pi=0x1.921fb54442d18p+1;const double step=binary64((pi+pi)/R(sides)),limit=binary64(R(turns)+R(turns));
 Segment s{};s.metal=primary;endpoint(s,angle,R(angle),radius,width,sides,initial_half,true);
 for(int turn=1;R(turn)<=R(limit);turn++){
  for(int side=1;R(side)<=R(sides)*R(.5);side++){
   collapse(s);const R next=R(angle)+R(step);angle=binary64(next);endpoint(s,angle,next,radius,width,sides,R(half),false);
   if(!conductor(s))return -1;
  }
  half=-half;collapse(s);if(R(turn)==R(limit))break;
  if(R(turn)==R(turns)){
   const R shift=R(half)+R(half);const int ends[]={11,3,7};for(int k:ends)s.p[k]=binary64(R(s.p[k])+shift);
  }else{
   bridge_metal=bridge_metal==primary?secondary:primary;s.metal=bridge_metal;
   const R radial=(R(width)+R(spacing))/asitic::x87::wide_cos(pi/R(sides));const bool inward=R(turn)<R(turns);
   radius=binary64(inward?R(radius)-radial:radial+R(radius));const bool negative=half<0;
   const int direction=inward?(negative?7:4):(negative?6:5);
   if(!via(s,bridge_metal,negative?1:-1))return -1;bridge(direction,s,height,width,spacing);
   if(!via(s,bridge_metal,direction==4||direction==5?1:-1))return -1;
  }
  if(!conductor(s))return -1;s.metal=primary;
 }
 return used;
}
}
extern "C" __attribute__((export_name("symmetric_config_buffer"))) unsigned symmetric_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("symmetric_event_buffer"))) unsigned symmetric_event_buffer(){return reinterpret_cast<unsigned>(events);}
extern "C" __attribute__((export_name("symmetric_geometry"))) int symmetric_geometry(){
 used=0;const int kind=int(config[0]);const double sides=config[4],turns=config[8];
 if((kind!=0&&kind!=1)||sides<4||sides>1024||sides!=int(sides)||int(sides)%2||!(turns>=1)||turns!=int(turns)||sides*turns>20000||!(config[3]>0)||!(config[5]>0)||!(config[6]>0)||config[7]<0)return -1;
 return kind?polygon():square();
}

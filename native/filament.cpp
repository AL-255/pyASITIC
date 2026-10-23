// Original 0x0806597c: retained filament interpolation and adaptive edge cells.
#include "soft_real.hpp"
namespace {
using R=SoftReal;
using asitic::x87::binary64;
int integer(R x){return extF80_to_i32(x.value,softfloat_round_minMag,true);}
void build(const double* p,double* out){
 double a[3],b[3],c[3],d[3];
 for(int j=0;j<3;j++){a[j]=p[j];b[j]=p[j+3];c[j]=p[j+6];d[j]=p[j+9];}
 const double width=p[12],thickness=p[13],layer=p[14],cell=p[17];
 const int cap=p[18],xi=p[19],zi=p[21],nx=p[22],ny=p[23],nz=p[24];int yi=p[20];
 double count=ny;
 if(R(width)/cell>R(double(cap))){
  const int edges=integer(R(0.4)*double(ny)),middle=cap-2*edges;
  const auto blend=[&](const double* from,const double* to,double* dst){
   const R dot=(R(from[0])*to[0]+R(from[1])*to[1])+R(from[2])*to[2];
   const R ratio=(R(double(edges))*cell)/asitic::x87::sqrt(dot),inv=R(1.)-ratio;
   dst[0]=binary64(R(from[0])*inv+ratio*to[0]);
   dst[1]=binary64(inv*from[1]+R(binary64(ratio))*to[1]);
  };
  if(yi<edges){blend(a,c,c);blend(b,d,d);out[6]=cell;count=edges;}
  else if(yi>cap-edges-1){blend(c,a,a);blend(d,b,b);yi-=edges+middle;out[6]=cell;count=edges;}
  else{
   double ca[3],cb[3],cc[3],cd[3];for(int j=0;j<3;j++){ca[j]=a[j];cb[j]=b[j];cc[j]=c[j];cd[j]=d[j];}
   blend(ca,cc,a);blend(cb,cd,b);blend(cc,ca,c);blend(cd,cb,d);yi-=edges;
   out[6]=binary64((R(width)-(R(cell)+cell)*double(edges))/double(edges));count=middle;
  }
 }else out[6]=binary64(R(width)/double(ny));
 out[7]=binary64(R(thickness)/double(nz));out[8]=p[25];
 const double u=binary64(R(double(xi))/double(nx)),v=binary64((R(double(yi))+0.5)/count);
 const double vm=binary64(R(1.)-v),um=binary64(R(1.)-u);
 const R weight=((R(u)*v+1.)-u)-v;
 const double vcx=binary64(R(v)*c[0]);const R vcy=R(v)*c[1];
 out[0]=binary64((((R(b[0])*u*(R(1.)-v)+R(a[0])*weight)+R(vcx)*(R(1.)-u))+R(d[0])*u*v)+p[15]);
 out[1]=binary64((((R(a[1])*weight+R(b[1])*u*vm)+vcy*um)+R(d[1])*u*v)+p[16]);
 const double z=binary64((R(layer)*0.5+a[2])-(R(double(zi))+1.)/(R(double(nz))+1.));out[2]=out[5]=z;
 const R raw_u1=R(double(xi+1))/double(nx);const double u1=binary64(raw_u1);
 const R weight1=((raw_u1*v+1.)-raw_u1)-v,um1=R(1.)-u1;
 out[3]=binary64((((R(b[0])*u1*vm+R(a[0])*weight1)+R(vcx)*um1)+R(d[0])*u1*v)+p[15]);
 out[4]=binary64((((R(a[1])*weight1+R(b[1])*u1*vm)+um1*binary64(vcy))+R(d[1])*u1*v)+p[16]);
}
double input[256*26],output[256*9];
}
extern "C" __attribute__((export_name("filament_buffer"))) unsigned filament_buffer(){return reinterpret_cast<unsigned>(input);}
extern "C" __attribute__((export_name("filament_result_buffer"))) unsigned filament_result_buffer(){return reinterpret_cast<unsigned>(output);}
extern "C" __attribute__((export_name("filaments"))) int filaments(int n){
 if(n<1||n>256)return -1;
 for(int i=0;i<n;i++)build(input+26*i,output+9*i);return 0;
}

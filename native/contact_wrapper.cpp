#include "contact_port.hpp"
using namespace asitic;
// Version, contact/grid/metal/layer counts, packed metal pair, chip dimensions;
// then five cells/contact, three/metal, two/coefficient, and layer depths.
static double config[4096];
static ComplexValue tables[66049+1024],coefficients[256];
static double depths[257];static ContactMetal metals[256];static PotentialContact contacts[256];
extern "C" unsigned matrix_buffer();
extern "C" __attribute__((export_name("contact_config_buffer"))) unsigned contact_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("contact_table_buffer"))) unsigned contact_table_buffer(){return reinterpret_cast<unsigned>(tables);}
static int integer(double d,int low,int high){return d>=low&&d<=high&&static_cast<int>(d)==d?static_cast<int>(d):-1;}
extern "C" __attribute__((export_name("contact_pair"))) int contact_pair(){
 if(config[0]!=1)return -1;
 const int n=integer(config[1],1,256),nx=integer(config[2],2,256),ny=integer(config[3],2,256),
  nm=integer(config[4],1,256),nl=integer(config[5],1,256);
 if(n<0||nx<0||ny<0||nm<0||nl<0||(nx&(nx-1))||(ny&(ny-1)))return -2;
 const int lo=integer(config[6],0,nm-1),hi=integer(config[7],0,nm-1);
 const double width=config[8],height=config[9];
 if(lo<0||hi<lo||!(width>0)||!(height>0)||!__builtin_isfinite(width)||!__builtin_isfinite(height))return -3;
 int offset=16;
 for(int i=0;i<n;i++){
  const int x0=integer(config[offset],0,nx-1),x1=integer(config[offset+1],1,nx),
   y0=integer(config[offset+2],0,ny-1),y1=integer(config[offset+3],1,ny),metal=integer(config[offset+4],0,nm-1);
  if(x0<0||x1<=x0||y0<0||y1<=y0||metal<0)return -4;
  contacts[i]={x0,x1,y0,y1,metal};offset+=5;
 }
 for(int i=0;i<nm;i++){
  const int layer=integer(config[offset],0,nl-1);if(layer<0)return -5;
  metals[i]={layer,config[offset+1],config[offset+2]};offset+=3;
 }
 for(int i=0;i<nl;i++){coefficients[i]={config[offset],config[offset+1]};offset+=2;}
 for(int i=0;i<=nl;i++)depths[i]=config[offset++];
 const PotentialGeometry geometry{nx,ny,width,height,metals,{coefficients,depths}};
 const PotentialTables view{tables,tables+2*nx,tables+2*nx+2*ny};
 const auto forward=contact_base(lo,hi,geometry),reverse=lo==hi?forward:contact_base(hi,lo,geometry);
 auto* output=reinterpret_cast<ComplexValue*>(matrix_buffer());
 for(int i=0;i<n;i++)for(int j=0;j<n;j++){
  const auto a=contacts[i],b=contacts[j];
  if(a.metal==lo&&b.metal==hi)output[i*n+j]=contact_potential(a,b,geometry,view,&forward);
  else if(a.metal==hi&&b.metal==lo)output[i*n+j]=contact_potential(a,b,geometry,view,&reverse);
 }
 return 0;
}

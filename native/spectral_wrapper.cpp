#include "spectral_port.hpp"
using namespace asitic;
static double config[2048],depths[257];
static ComplexValue coefficients[258],tables[66049+1024];
static ContactMetal metals[256];
static int integer(double v,int lo,int hi){return v>=lo&&v<=hi&&static_cast<int>(v)==v?static_cast<int>(v):-1;}
extern "C" __attribute__((export_name("spectral_config_buffer"))) unsigned spectral_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("spectral_table_buffer"))) unsigned spectral_table_buffer(){return reinterpret_cast<unsigned>(tables);}
extern "C" __attribute__((export_name("spectral_depth_buffer"))) unsigned spectral_depth_buffer(){return reinterpret_cast<unsigned>(depths);}
extern "C" __attribute__((export_name("layer_coefficients"))) int layer_coefficients(){
 if(config[0]!=1)return -1;
 const int n=integer(config[1],1,256);if(n<0)return -2;
 const SoftReal weight=((SoftReal(config[2])*0x1.921fb54442d18p+2)*0x1.8ebfab864ade4p-44)*0x1.a36e2eb1c432dp-14;
 for(int i=0;i<n;i++){
  const auto z=legacy::divide(1.,{x87::binary64(SoftReal(1.)/config[3+2*i]),x87::binary64(weight*config[4+2*i])});
  config[3+2*n+2*i]=z.real;config[4+2*n+2*i]=z.imag;
 }
 return 0;
}
static int load_config(){
 if(config[0]!=1)return -1;
 const int nx=integer(config[1],2,256),ny=integer(config[2],2,256),nm=integer(config[3],1,256),nl=integer(config[4],1,256);
 if(nx<0||ny<0||nm<0||nl<0||(nx&(nx-1))||(ny&(ny-1)))return -2;
 if(integer(config[5],0,nm-1)<0||integer(config[6],0,nm-1)<0||!(config[7]>0)||!(config[8]>0)||!__builtin_isfinite(config[7])||!__builtin_isfinite(config[8]))return -3;
 int offset=9;
 for(int i=0;i<nm;i++){
  const int layer=integer(config[offset],0,nl-1);if(layer<0)return -4;
  metals[i]={layer,config[offset+1],config[offset+2]};offset+=3;
 }
 coefficients[0]=coefficients[nl+1]={0,0};
 for(int i=0;i<nl;i++){coefficients[i+1]={config[offset],config[offset+1]};offset+=2;}
 for(int i=0;i<=nl;i++)depths[i]=config[offset++];
 return 0;
}
extern "C" __attribute__((export_name("spectral_tables"))) int spectral_tables(){
 int status=load_config();if(status)return status;
 const int nx=config[1],ny=config[2],nl=config[4];
 const int count=2*nx+2*ny+((nx+1)*(ny+1)>nx*(nx+1)+ny+1?(nx+1)*(ny+1):nx*(nx+1)+ny+1);
 for(int i=0;i<count;i++)tables[i]={0,0};
 const PotentialTableGeometry geometry{nx,ny,config[7],config[8],metals,{coefficients+1,depths},nl};
 generate_potential_tables(config[5],config[6],geometry,{tables,tables+2*nx,tables+2*nx+2*ny});
 return 0;
}
extern "C" __attribute__((export_name("spectral_probe"))) int spectral_probe(int kind,int source,int target,int last,double k,double sh,double th){
 int status=load_config();if(status)return status;
 const int nl=config[4];
 if(kind<0||kind>5||source<((kind==0)?-1:0)||source>=nl||target<0||target>=nl||last<0||last>=nl)return -5;
 const PotentialTableLayers layers{coefficients+1,depths};
 switch(kind){
  case 0:tables[0]=potential_transfer_up(source,k,layers.view());break;
  case 1:tables[0]=potential_transfer_down(source,last,k,layers.view());break;
  case 2:tables[0]=potential_source_up(source,k,sh,layers);break;
  case 3:tables[0]=potential_source_down(source,last,k,sh,layers);break;
  case 4:tables[0]=potential_spectral_a(source,target,last,k,sh,th,layers);break;
  default:tables[0]=potential_spectral_b(source,target,last,k,sh,th,layers);
 }
 return 0;
}

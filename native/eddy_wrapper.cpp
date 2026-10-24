#include "eddy_port.hpp"
namespace {
using C=asitic::ComplexValue;using R=SoftReal;using asitic::x87::binary64;
static double config[24],wires[2048*8],info[32],square[256*256];
static asitic::EddySegment segments[2048];static C matrix[256*256];
}
extern "C" __attribute__((export_name("eddy_config_buffer"))) unsigned eddy_config_buffer(){return reinterpret_cast<unsigned>(config);}
extern "C" __attribute__((export_name("eddy_wire_buffer"))) unsigned eddy_wire_buffer(){return reinterpret_cast<unsigned>(wires);}
extern "C" __attribute__((export_name("eddy_matrix_buffer"))) unsigned eddy_matrix_buffer(){return reinterpret_cast<unsigned>(matrix);}
extern "C" __attribute__((export_name("eddy_info_buffer"))) unsigned eddy_info_buffer(){return reinterpret_cast<unsigned>(info);}
extern "C" __attribute__((export_name("eddy_square_buffer"))) unsigned eddy_square_buffer(){return reinterpret_cast<unsigned>(square);}
extern "C" __attribute__((export_name("eddy_stamp"))) int eddy_stamp(){
 if(config[0]!=1.)return -1;
 const int count=int(config[1]),rows=int(config[2]),metals=int(config[3]),mode=int(config[4]);
 if(count<1||count>2048||rows<1||rows>256||metals<1||metals>256||mode<1||mode>255)return -1;
 int conductors=0;
 for(int i=0;i<count;i++){
  for(int j=0;j<7;j++)segments[i].wire[j]=wires[8*i+j];
  segments[i].metal=int(wires[8*i+7]);if(segments[i].metal<metals)conductors++;
  segments[i].next_address=i+1<count?reinterpret_cast<unsigned>(segments+i+1):0;
 }
 if(conductors!=rows)return -2;
 unsigned calls=0,statuses[16]={};
 asitic::GreenState state{{config[13],config[14],config[15]}};
 const asitic::EddyEnvironment env{config[7],&state,&calls,statuses};
 int size=0;
 if(config[5]&&mode==1){
  const asitic::SquareSpiralGeometry g{config[8],config[9],config[10],config[11]};
  const int turns=extF80_to_i32(extF80_roundToInt(R(g.turns).value,softfloat_round_max,false),softfloat_round_minMag,false);size=2*turns;
  if(size<1||size>256)return -3;
  asitic::assemble_eddy_matrix({square,size},g,config[6],binary64(R(0x1.0c6f7a0b5ed8dp-19)*R(config[12])),env);
  const int limit=extF80_to_i32(extF80_roundToInt((R(g.turns)*R(4.)).value,softfloat_round_min,false),softfloat_round_minMag,false);
  for(int i=1;i<size;i++)for(int j=1;j<size;j++){
   const int row=asitic::eddy_packed_index(i,turns)-1,column=asitic::eddy_packed_index(j,turns)-1;
   for(int offset=0;offset<2;offset++)if(row+offset<limit&&column+offset<limit){
    if(row+offset<0||column+offset<0||row+offset>=rows||column+offset>=rows)return -3;
    auto& value=matrix[(column+offset)*rows+row+offset];
    value.real=binary64(R(square[(j-1)*size+i-1])+R(value.real));value.imag=binary64(R(value.imag)+R(0.));
   }
  }
 }else asitic::fold_eddy_segments({segments},{matrix,rows},rows,config[6],metals,env);
 for(int i=0;i<32;i++)info[i]=0.;
 info[0]=calls;for(int i=0;i<16;i++)info[i+1]=statuses[i];
 for(int i=0;i<3;i++)info[17+i]=state.history[i];info[20]=size;
 return 0;
}

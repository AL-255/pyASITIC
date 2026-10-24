#pragma once
#include "contact_port.hpp"
#include "green_integral_port.hpp"
namespace asitic {
struct EddySegment { double wire[7];int metal;unsigned next_address; };
using ConductorSegment=EddySegment;
struct ShapeFilamentList { const EddySegment* first; };
struct SquareSpiralGeometry { double dimension,width,spacing,turns; };
struct RealMatrixView { double* data;int stride;double& at(int i,int j)const{return data[j*stride+i];} };
struct EddyEnvironment {
 double coordinate_scale;GreenState* state;
 unsigned* calls;unsigned* statuses;
};
SoftReal distance(const double*,const double*);
void assemble_eddy_matrix(RealMatrixView,const SquareSpiralGeometry&,double,double,const EddyEnvironment&);
void fold_eddy_segments(const ShapeFilamentList&,ComplexMatrixView,unsigned,double,int,const EddyEnvironment&);
int eddy_packed_index(int,int);
}

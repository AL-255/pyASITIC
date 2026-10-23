#pragma once
#include "contact_port.hpp"
extern "C" {
double retained_cosh(extFloat80_t,int);
double retained_tanh(extFloat80_t);
void retained_fft(asitic::ComplexValue*,int);
void retained_grid(asitic::ComplexValue*,int,int);
}
namespace asitic {
struct PotentialTableLayers {
 const ComplexValue* coefficients;double* depths;
 PotentialLayers view()const{return {coefficients,depths};}
};
struct PotentialTableGeometry {
 int nx,ny;double width,height;const ContactMetal* metals;
 PotentialTableLayers layers;int layer_count;
};
struct PotentialTableOutput {ComplexValue* x;ComplexValue* y;ComplexValue* xy;};
ComplexValue potential_transfer_up(int,double,const PotentialLayers&);
ComplexValue potential_transfer_down(int,int,double,const PotentialLayers&);
ComplexValue potential_source_up(int,double,double,const PotentialTableLayers&);
ComplexValue potential_source_down(int,int,double,double,const PotentialTableLayers&);
ComplexValue potential_spectral_a(int,int,int,double,double,double,const PotentialTableLayers&);
ComplexValue potential_spectral_b(int,int,int,double,double,double,const PotentialTableLayers&);
void generate_potential_tables(int,int,const PotentialTableGeometry&,PotentialTableOutput);
}

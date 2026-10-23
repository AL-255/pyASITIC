#pragma once
#include "soft_real.hpp"
namespace asitic{
struct ComplexValue{double real,imag;};
struct ComplexMatrixView{ComplexValue* data;int stride;ComplexValue& at(int r,int c)const{return data[c*stride+r];}};
namespace lapack{
[[noreturn]] void fatal_error(const char*);
[[noreturn]] void application_fatal_error(const char*);
void argument_error(const char*,int);
SoftReal magnitude(const ComplexValue&);
SoftReal abs1(const ComplexValue&);
void divide(ComplexValue&,const ComplexValue&,const ComplexValue&);
void square_root(ComplexValue&,const ComplexValue&);
void integer_power(ComplexValue&,const ComplexValue&,int);
void eigen2(const ComplexValue&,const ComplexValue&,const ComplexValue&,ComplexValue&,ComplexValue&,ComplexValue&,ComplexValue&,ComplexValue&);
int factor_symmetric_upper(int,ComplexMatrixView,int*);
int invert_symmetric_upper(int,ComplexMatrixView,const int*,ComplexValue*);
int max_index(int,const ComplexValue*,int);
void scale(int,const ComplexValue&,ComplexValue*,int);
void swap(int,ComplexValue*,int,ComplexValue*,int);
int factor_general(int,int,ComplexMatrixView,int*);
int invert_general(int,ComplexMatrixView,const int*,ComplexValue*,int);
int solve_general(int,int,ComplexMatrixView,const int*,ComplexMatrixView);
}}

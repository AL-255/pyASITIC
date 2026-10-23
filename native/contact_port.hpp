#pragma once
#include "matrix_port.hpp"
namespace asitic {
struct ContactMetal { int layer;double height,thickness; };
struct PotentialLayers { const ComplexValue* coefficients;const double* depths; };
struct PotentialContact { int x0,x1,y0,y1,metal; };
struct PotentialGeometry { int nx,ny;double width,height;const ContactMetal* metals;PotentialLayers layers; };
struct PotentialTables { const ComplexValue* x;const ComplexValue* y;const ComplexValue* xy; };
ComplexValue contact_base(int,int,const PotentialGeometry&);
ComplexValue contact_potential(const PotentialContact&,const PotentialContact&,const PotentialGeometry&,const PotentialTables&,const ComplexValue* base=nullptr);
namespace legacy { ComplexValue divide(const ComplexValue&,const ComplexValue&);ComplexValue divide(double,const ComplexValue&); }
}

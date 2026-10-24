#pragma once
#include "quadrature_port.hpp"
namespace asitic {
struct GreenState { double history[3]; };
struct GreenStats {
 double integral,error,first,last;
 int status,evaluations,observations,intervals,cycles;
};
// Reflection callback, original wrapper selector and retained physical scaling.
SoftReal integrate_reflection(double frequency,double separation,double height,GreenState&,GreenStats&);
}

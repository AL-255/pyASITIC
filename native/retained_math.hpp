#pragma once
#include "soft_real.hpp"
namespace asitic::x87 {
SoftReal log(SoftReal);
SoftReal atan(SoftReal);
SoftReal atan2(SoftReal,SoftReal);
SoftReal atanh(SoftReal);
// Mutual-kernel angle domain [-4,4]; not arbitrary Green-integrand arguments.
SoftReal cos(SoftReal);
SoftReal sin(SoftReal);
SoftReal exp(SoftReal);
SoftReal log2(SoftReal);
double error_power(double);
// Imported binary64 libm boundary, distinct from FSIN/FCOS above.
SoftReal libm_cos(double);
SoftReal libm_sin(double);
inline int truncate_int(SoftReal x){return extF80_to_i32(x.value,softfloat_round_minMag,false);}
}

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
}

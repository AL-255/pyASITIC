#pragma once
extern "C" {
#include "platform.h"
#include "softfloat.h"
}
struct SoftReal {
 extFloat80_t value;
 SoftReal():SoftReal(0.){}
 SoftReal(double x){union{double d;float64_t f;}u={.d=x};value=f64_to_extF80(u.f);}
 explicit SoftReal(extFloat80_t x):value(x){}
 explicit operator double()const{union{double d;float64_t f;}u;u.f=extF80_to_f64(value);return u.d;}
 SoftReal operator-()const{auto x=value;x.signExp^=0x8000;return SoftReal(x);}
 SoftReal& operator+=(SoftReal x){value=extF80_add(value,x.value);return *this;}
 SoftReal& operator-=(SoftReal x){value=extF80_sub(value,x.value);return *this;}
 SoftReal& operator*=(SoftReal x){value=extF80_mul(value,x.value);return *this;}
 SoftReal& operator/=(SoftReal x){value=extF80_div(value,x.value);return *this;}
};
inline SoftReal operator+(SoftReal a,SoftReal b){return SoftReal(extF80_add(a.value,b.value));}
inline SoftReal operator-(SoftReal a,SoftReal b){return SoftReal(extF80_sub(a.value,b.value));}
inline SoftReal operator*(SoftReal a,SoftReal b){return SoftReal(extF80_mul(a.value,b.value));}
inline SoftReal operator/(SoftReal a,SoftReal b){return SoftReal(extF80_div(a.value,b.value));}
inline bool operator<(SoftReal a,SoftReal b){return extF80_lt(a.value,b.value);}
inline bool operator<=(SoftReal a,SoftReal b){return extF80_le(a.value,b.value);}
inline bool operator==(SoftReal a,SoftReal b){return extF80_eq(a.value,b.value);}
inline bool operator>(SoftReal a,SoftReal b){return b<a;}
inline bool operator>=(SoftReal a,SoftReal b){return b<=a;}
inline bool operator!=(SoftReal a,SoftReal b){return !(a==b);}
namespace asitic::x87{
inline double binary64(SoftReal a){return static_cast<double>(a);}
inline SoftReal abs(SoftReal a){a.value.signExp&=0x7fff;return a;}
inline SoftReal sqrt(SoftReal a){return SoftReal(extF80_sqrt(a.value));}
}

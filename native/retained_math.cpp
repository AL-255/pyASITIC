// Guard-precision elementary evaluation around the original x87 operations.
#include "retained_math.hpp"
namespace {
using Q=float128_t;using R=SoftReal;
const Q one={{0,0x3fff000000000000ULL}},ln2={{0xf35793c7673007e6ULL,0x3ffe62e42fefa39eULL}};
const Q pi={{0x8469898cc51701b8ULL,0x4000921fb54442d1ULL}};
// Intel's internal trigonometric Pi approximation (distinct from FLDPI).
const Q trig_pi={{0x8469800000000000ULL,0x4000921fb54442d1ULL}};
Q neg(Q x){x.v[1]^=0x8000000000000000ULL;return x;}
Q sub(Q a,Q b){return f128_add(a,neg(b));}
Q integer(int n){return i32_to_f128(n);}
Q inverse_odd[65];bool planned;
void plan(){if(planned)return;for(int i=0;i<65;i++)inverse_odd[i]=f128_div(one,integer(2*i+1));planned=true;}
R nan(){return asitic::x87::sqrt(R(-1.));}
Q atan_positive(Q value,bool reciprocal){
 if(reciprocal)value=f128_div(one,value);
 const bool shifted=R(f128_to_extF80(value))>R(0.41421356237309503);
 const Q z=shifted?f128_div(sub(value,one),f128_add(value,one)):value;
 const Q square=neg(f128_mul(z,z));Q sum=inverse_odd[64];
 for(int i=63;i>=0;i--)sum=f128_add(inverse_odd[i],f128_mul(square,sum));
 Q result=f128_mul(z,sum);
 if(shifted)result=f128_add(f128_div(pi,integer(4)),result);
 return reciprocal?sub(f128_div(pi,integer(2)),result):result;
}
R trig(R input,bool cosine){
 // Native mutual formulas only pass a stored atan2 angle in [0, pi/2].
 // This guarded polynomial covers [-4,4]; no arbitrary-angle claim is made.
 if(asitic::x87::abs(input)>R(4.)||(input.value.signExp&0x7fff)==0x7fff)return nan();
 if(!input.value.signif)return cosine?R(1.):input;
 const bool negative=input.value.signExp&0x8000;const Q magnitude=extF80_to_f128(asitic::x87::abs(input).value);
 const Q half=f128_div(trig_pi,integer(2));
 const int quadrant=extF80_to_i32(f128_to_extF80(f128_div(magnitude,half)),softfloat_round_near_even,false);
 const Q reduced=sub(magnitude,f128_mul(integer(quadrant),half));
 // FSIN/FCOS approximate sin/cos(x*pi/P), with P the internal Pi above.
 // Reduce before scaling so cancellation near pi/2 preserves guard precision.
 const Q x=f128_div(f128_mul(reduced,pi),trig_pi),square=neg(f128_mul(x,x));
 const bool evaluate_cosine=cosine?!(quadrant&1):quadrant&1;
 Q term=evaluate_cosine?one:x,sum=term;
 for(int i=1;i<=40;i++){
  term=f128_div(f128_mul(term,square),integer(evaluate_cosine?(2*i-1)*(2*i):(2*i)*(2*i+1)));sum=f128_add(sum,term);
 }
 const bool negate_result=cosine?(quadrant==1||quadrant==2):(quadrant==2||quadrant==3);
 if(negate_result!=(!cosine&&negative))sum=neg(sum);
 return R(f128_to_extF80(sum));
}
R wide_trig(R input,bool cosine){
 if(asitic::x87::abs(input)<=R(4.))return trig(input,cosine);
 if((input.value.signExp&0x7fff)==0x7fff)return nan();
 // FSIN/FCOS leave a finite operand unchanged when its magnitude is >=2^63.
 if(asitic::x87::abs(input)>=R(0x1p63))return input;
 const bool negative=input.value.signExp&0x8000;
 const Q magnitude=extF80_to_f128(asitic::x87::abs(input).value),half=f128_div(trig_pi,integer(2));
 const auto count=extF80_roundToInt(f128_to_extF80(f128_div(magnitude,half)),softfloat_round_near_even,false);
 const int power=(count.signExp&0x7fff)-16383;
 const uint64_t turns=count.signif>>(63-power);const int quadrant=turns&3;
 const Q q=extF80_to_f128(count);
 // Split the 69-bit native Pi constant so both integer products are exact
 // in binary128, including large operands close to the instruction limit.
 Q high=half;high.v[0]=0;high.v[1]&=~uint64_t(1);
 const Q low=sub(half,high),reduced=sub(sub(magnitude,f128_mul(q,high)),f128_mul(q,low));
 const Q x=f128_div(f128_mul(reduced,pi),trig_pi),square=neg(f128_mul(x,x));
 const bool evaluate_cosine=cosine?!(quadrant&1):quadrant&1;
 Q term=evaluate_cosine?one:x,sum=term;
 for(int i=1;i<=40;i++){
  term=f128_div(f128_mul(term,square),integer(evaluate_cosine?(2*i-1)*(2*i):(2*i)*(2*i+1)));sum=f128_add(sum,term);
 }
 const bool negative_result=cosine?(quadrant==1||quadrant==2):(quadrant==2||quadrant==3);
 if(negative_result!=(!cosine&&negative))sum=neg(sum);
 return R(f128_to_extF80(sum));
}
}
namespace asitic::x87 {
SoftReal log2(SoftReal input){
 const int exponent=input.value.signExp&0x7fff;
 if(!input.value.signif)return R(extF80_div(R(-1.).value,R(0.).value));
 if(input.value.signExp&0x8000)return nan();
 if(exponent==0x7fff)return input;
 plan();R normalized=input;int power=exponent-16383;
 if(!exponent){power=-16382;while(!(normalized.value.signif&0x8000000000000000ULL)){normalized.value.signif<<=1;power--;}}
 normalized.value.signExp=0x3fff;
 const Q m=extF80_to_f128(normalized.value),z=f128_div(sub(m,one),f128_add(m,one)),square=f128_mul(z,z);
 Q sum=inverse_odd[64];for(int i=63;i>=0;i--)sum=f128_add(inverse_odd[i],f128_mul(square,sum));
 return R(f128_to_extF80(f128_add(integer(power),f128_div(f128_mul(integer(2),f128_mul(z,sum)),ln2))));
}
SoftReal log(SoftReal input){
 const int exponent=input.value.signExp&0x7fff;
 if(!input.value.signif)return R(extF80_div(R(-1.).value,R(0.).value));
 if(input.value.signExp&0x8000)return nan();
 if(exponent==0x7fff)return input;
 plan();R normalized=input;int power=exponent-16383;
 // Normalize an extended subnormal without narrowing its significand.
 if(!exponent){power=-16382;while(!(normalized.value.signif&0x8000000000000000ULL)){normalized.value.signif<<=1;power--;}}
 normalized.value.signExp=0x3fff;
 const Q m=extF80_to_f128(normalized.value),z=f128_div(sub(m,one),f128_add(m,one)),square=f128_mul(z,z);
 Q sum=inverse_odd[64];for(int i=63;i>=0;i--)sum=f128_add(inverse_odd[i],f128_mul(square,sum));
 const Q fraction=f128_div(f128_mul(integer(2),f128_mul(z,sum)),ln2);
 const Q logarithm=f128_add(integer(power),fraction);
 // FLDLN2 supplies an 80-bit constant to FYL2X, not an exact ln(2).
 const R native_ln2(extFloat80_t{.signif=0xb17217f7d1cf79acULL,.signExp=0x3ffe});
 return R(f128_to_extF80(f128_mul(extF80_to_f128(native_ln2.value),logarithm)));
}
SoftReal atan(SoftReal input){
 if((input.value.signExp&0x7fff)==0x7fff&&(input.value.signif&0x7fffffffffffffffULL))return input;
 const bool negative=input.value.signExp&0x8000;const R absolute=abs(input);plan();
 Q result=atan_positive(extF80_to_f128(absolute.value),absolute>R(1.));
 if(negative)result=neg(result);return R(f128_to_extF80(result));
}
SoftReal atan2(SoftReal y,SoftReal x){
 const R ax=abs(x),ay=abs(y);const bool negative_y=y.value.signExp&0x8000,negative_x=x.value.signExp&0x8000;
 const auto is_nan=[](R a){return (a.value.signExp&0x7fff)==0x7fff&&(a.value.signif&0x7fffffffffffffffULL);};
 if(is_nan(x)||is_nan(y))return nan();plan();Q angle;
 if(!ay.value.signif)angle=negative_x?pi:integer(0);
 else if(!ax.value.signif)angle=f128_div(pi,integer(2));
 else if((ax.value.signExp&0x7fff)==0x7fff&&(ay.value.signExp&0x7fff)==0x7fff){angle=f128_div(pi,integer(4));if(negative_x)angle=sub(pi,angle);}
 else{
  const bool reciprocal=ay>ax;
  const Q ratio=f128_div(extF80_to_f128(reciprocal?ax.value:ay.value),extF80_to_f128(reciprocal?ay.value:ax.value));
  angle=atan_positive(ratio,false);if(reciprocal)angle=sub(f128_div(pi,integer(2)),angle);if(negative_x)angle=sub(pi,angle);
 }
 if(negative_y)angle=neg(angle);return R(f128_to_extF80(angle));
}
SoftReal atanh(SoftReal x){
 const R a=abs(x),u=-(a+a)/(a+1.);
 const R crossover(extFloat80_t{.signif=0x95f619980c4336f8ULL,.signExp=0x3ffd});R logarithm;
 if(abs(u)>=crossover)logarithm=log(R(1.)+u);
 else{
  plan();const Q value=extF80_to_f128(u.value),z=f128_div(value,f128_add(integer(2),value)),square=f128_mul(z,z);
  Q sum=inverse_odd[64];for(int i=63;i>=0;i--)sum=f128_add(inverse_odd[i],f128_mul(square,sum));
  const R native_ln2(extFloat80_t{.signif=0xb17217f7d1cf79acULL,.signExp=0x3ffe});
  logarithm=R(f128_to_extF80(f128_mul(f128_div(f128_mul(integer(2),f128_mul(z,sum)),ln2),extF80_to_f128(native_ln2.value))));
 }
 return (R(-.5)*logarithm)*(x>=R(0.)?R(1.):R(-1.));
}
SoftReal cos(SoftReal x){return trig(x,true);}
SoftReal sin(SoftReal x){return trig(x,false);}
SoftReal wide_cos(SoftReal x){return wide_trig(x,true);}
SoftReal wide_sin(SoftReal x){return wide_trig(x,false);}
}
extern "C" extFloat80_t retained_exp(extFloat80_t);
extern "C" extFloat80_t retained_sinh(extFloat80_t);
namespace asitic::x87 {SoftReal exp(SoftReal x){return SoftReal(retained_exp(x.value));}}
namespace asitic::x87 {
SoftReal sinh_real(SoftReal x){return SoftReal(retained_sinh(x.value));}
SoftReal cosh_real(SoftReal x){const auto e=exp(x);return (e+SoftReal(1.)/e)*SoftReal(.5);}
}
extern "C" extFloat80_t retained_exp2(extFloat80_t);
namespace asitic::x87 {
double error_power(double x){
 if(x==0)return 0.;
 if(__builtin_isinf(x))return binary64(abs(R(x)));
 if(x<0||__builtin_isnan(x))return binary64(sqrt(R(x)));
 return binary64(R(retained_exp2((log2(R(x))*R(1.5)).value)));
}
}

extern "C" __attribute__((export_name("binary64_trig_probe"))) double binary64_trig_probe(int operation,double x){
 return operation==0?asitic::x87::binary64(asitic::x87::libm_cos(x)):operation==1?asitic::x87::binary64(asitic::x87::libm_sin(x)):operation==2?asitic::x87::error_power(x):__builtin_nan("");
}
static double results[4];
extern "C" __attribute__((export_name("retained_math_buffer"))) unsigned retained_math_buffer(){return reinterpret_cast<unsigned>(results);}
extern "C" __attribute__((export_name("retained_math_probe"))) int retained_math_probe(int operation,double a,double b,int rule){
 if(operation<0||operation>6||rule<0||rule>3)return -1;
 R value(a);if(rule==1)value=value/R(b);if(rule==2)value=value+R(b);if(rule==3)value=value*R(b);
 const R out=operation==0?asitic::x87::log(value):operation==1?asitic::x87::atan(value):operation==2?asitic::x87::exp(value):operation==3?asitic::x87::atan2(R(a),R(b)):operation==4?asitic::x87::cos(value):operation==5?asitic::x87::sin(value):asitic::x87::atanh(value);
 results[0]=asitic::x87::binary64(out);results[1]=double(unsigned(out.value.signif));results[2]=double(unsigned(out.value.signif>>32));results[3]=out.value.signExp;return 0;
}

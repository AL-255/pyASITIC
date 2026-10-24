// Retained SoftFloat port of recomp_cpp/src/two_port_output.cpp conversion.
#include "network_port.hpp"
namespace asitic {
namespace {
void store(double& destination,SoftReal value) {destination=x87::binary64(value);}
SoftReal load(const volatile double& value) {return (SoftReal)value;}
// Same bundled division arithmetic, with direct stores to the return record.
// Re-loading a rounded subnormal through a double-return helper would add a
// denormal exception that the original stores do not raise.
ComplexValue divide(const ComplexValue& numerator,const ComplexValue& denominator) {
    const SoftReal c=load(denominator.real),d=load(denominator.imag);
    const SoftReal real=load(numerator.real),imag=load(numerator.imag);ComplexValue out;
    if(x87::abs(d)>=x87::abs(c)) {
        const SoftReal ratio=c/d,divisor=ratio*ratio*d+d;
        const SoftReal first=(real*ratio+imag)/divisor,second=(imag*ratio-real)/divisor;
        store(out.real,first);store(out.imag,second);
    } else {
        const SoftReal ratio=d/c,divisor=ratio*ratio*c+c;
        const SoftReal first=(imag*ratio+real)/divisor,second=(imag-real*ratio)/divisor;
        store(out.real,first);store(out.imag,second);
    }
    return out;
}
}
TwoPortScattering convert_two_port_scattering(const TwoPortAdmittance& y) {
    const double reference=0x1.47ae147ae147bp-6,negative_two=-2.;
    TwoPortScattering result;
    // Retain the native extended arithmetic and its otherwise discarded
    // binary64 copies. The first diagonal uses y22 in both factors.
    const SoftReal t0=load(y.y22.real);
    const SoftReal t1=load(reference);
    const SoftReal t2=t0+t1;
    [[maybe_unused]] double s40_3;store(s40_3,t2);
    const SoftReal t4=load(y.y22.imag);
    [[maybe_unused]] double s38_5;store(s38_5,t4);
    const SoftReal t6=load(y.y11.real);
    const SoftReal t7=load(reference);
    const SoftReal t8=t6+t7;
    const SoftReal t9=load(y.y11.imag);
    const SoftReal t10=t4*t9;
    const SoftReal t11=t2*t8;
    const SoftReal t12=t11-t10;
    const SoftReal t13=t2*t9;
    const SoftReal t14=t4*t8;
    const SoftReal t15=t13+t14;
    [[maybe_unused]] double s48_16;store(s48_16,t9);
    [[maybe_unused]] double s50_17;store(s50_17,t8);
    [[maybe_unused]] double s30_18;store(s30_18,t12);
    [[maybe_unused]] double s28_19;store(s28_19,t15);
    const SoftReal t20=load(y.y21.real);
    const SoftReal t21=load(y.y12.real);
    const SoftReal t22=t20*t21;
    const SoftReal t23=load(y.y21.imag);
    const SoftReal t24=load(y.y12.imag);
    const SoftReal t25=t23*t24;
    const SoftReal t26=t22-t25;
    const SoftReal t27=load(y.y12.imag);
    const SoftReal t28=t20*t27;
    const SoftReal t29=load(y.y12.real);
    const SoftReal t30=t23*t29;
    const SoftReal t31=t28+t30;
    const SoftReal t32=t12-t26;
    const SoftReal t33=t15-t31;
    [[maybe_unused]] double s60_34;store(s60_34,t26);
    [[maybe_unused]] double s58_35;store(s58_35,t31);
    [[maybe_unused]] double s20_36;store(s20_36,t32);
    [[maybe_unused]] double s18_37;store(s18_37,t33);
    const ComplexValue denominator{s20_36,s18_37};
    const SoftReal t38=load(reference);
    const SoftReal t39=load(y.y22.real);
    const SoftReal t40=t38-t39;
    const SoftReal t41=-t4;
    const SoftReal t42=t41*t4;
    const SoftReal t43=t40*t2;
    const SoftReal t44=t43-t42;
    [[maybe_unused]] double s28_45;store(s28_45,t41);
    const SoftReal t46=t41*t2;
    [[maybe_unused]] double s20_47;store(s20_47,t2);
    [[maybe_unused]] double s18_48;store(s18_48,t4);
    [[maybe_unused]] double s30_49;store(s30_49,t40);
    const SoftReal t50=t4*t40;
    const SoftReal t51=t46+t50;
    [[maybe_unused]] double s40_52;store(s40_52,t44);
    const SoftReal t53=t44+t26;
    [[maybe_unused]] double s38_54;store(s38_54,t51);
    const SoftReal t55=t51+t31;
    [[maybe_unused]] double s70_56;store(s70_56,t26);
    [[maybe_unused]] double s68_57;store(s68_57,t31);
    [[maybe_unused]] double s50_58;store(s50_58,t53);
    [[maybe_unused]] double s48_59;store(s48_59,t55);
    result.s11=divide({s50_58,s48_59},denominator);
    const SoftReal t60=load(y.y22.real);
    const SoftReal t61=load(reference);
    const SoftReal t62=t60+t61;
    const SoftReal t63=load(y.y22.imag);
    [[maybe_unused]] double s38_64;store(s38_64,t63);
    const SoftReal t65=load(reference);
    [[maybe_unused]] double s40_66;store(s40_66,t62);
    const SoftReal t67=load(y.y11.real);
    const SoftReal t68=t65-t67;
    const SoftReal t69=load(y.y11.imag);
    const SoftReal t70=-t69;
    const SoftReal t71=t63*t70;
    const SoftReal t72=t62*t68;
    const SoftReal t73=t72-t71;
    const SoftReal t74=t62*t70;
    const SoftReal t75=t63*t68;
    const SoftReal t76=t74+t75;
    [[maybe_unused]] double s28_77;store(s28_77,t70);
    [[maybe_unused]] double s30_78;store(s30_78,t68);
    [[maybe_unused]] double s50_79;store(s50_79,t73);
    [[maybe_unused]] double s48_80;store(s48_80,t76);
    const SoftReal t81=load(y.y21.real);
    const SoftReal t82=load(y.y12.real);
    const SoftReal t83=t81*t82;
    const SoftReal t84=load(y.y21.imag);
    const SoftReal t85=load(y.y12.imag);
    const SoftReal t86=t84*t85;
    const SoftReal t87=t83-t86;
    const SoftReal t88=load(y.y12.imag);
    const SoftReal t89=t81*t88;
    const SoftReal t90=t82*t84;
    const SoftReal t91=t90+t89;
    const SoftReal t92=t73+t87;
    const SoftReal t93=t76+t91;
    [[maybe_unused]] double s20_94;store(s20_94,t87);
    [[maybe_unused]] double s18_95;store(s18_95,t91);
    [[maybe_unused]] double s60_96;store(s60_96,t92);
    [[maybe_unused]] double s58_97;store(s58_97,t93);
    result.s22=divide({s60_96,s58_97},denominator);
    const SoftReal t98=load(negative_two);
    const SoftReal t99=load(y.y21.real);
    const SoftReal t100=t99*t98;
    const SoftReal t101=load(y.y21.imag);
    const SoftReal t102=t101*t98;
    [[maybe_unused]] double s50_103;store(s50_103,t100);
    const SoftReal t104=load(reference);
    const SoftReal t105=t100*t104;
    [[maybe_unused]] double s48_106;store(s48_106,t102);
    const SoftReal t107=load(reference);
    const SoftReal t108=t102*t107;
    [[maybe_unused]] double s60_109;store(s60_109,t105);
    [[maybe_unused]] double s58_110;store(s58_110,t108);
    const SoftReal s80_111=t98;
    result.s21=divide({s60_109,s58_110},denominator);
    const SoftReal t112=(s80_111);
    const SoftReal t113=load(y.y12.real);
    const SoftReal t114=t113*t112;
    const SoftReal t115=load(y.y12.imag);
    const SoftReal t116=t112*t115;
    [[maybe_unused]] double s50_117;store(s50_117,t114);
    const SoftReal t118=load(reference);
    const SoftReal t119=t114*t118;
    [[maybe_unused]] double s48_120;store(s48_120,t116);
    const SoftReal t121=load(reference);
    const SoftReal t122=t116*t121;
    [[maybe_unused]] double s60_123;store(s60_123,t119);
    [[maybe_unused]] double s58_124;store(s58_124,t122);
    result.s12=divide({s60_123,s58_124},denominator);
    return result;
}
}

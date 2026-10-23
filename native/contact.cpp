// Port of potential.cpp: original retained arithmetic and every binary64 store.
// The position-independent zero term is factored for exact per-pair reuse.
#include "contact_port.hpp"



namespace asitic {
namespace legacy {
ComplexValue divide(const ComplexValue& a,const ComplexValue& b) {
 const SoftReal c=b.real,d=b.imag;
 if(x87::abs(d)>=x87::abs(c)) {
  const SoftReal ratio=c/d,denominator=ratio*ratio*d+d;
  return {x87::binary64(((SoftReal)a.real*ratio+a.imag)/denominator),x87::binary64(((SoftReal)a.imag*ratio-a.real)/denominator)};
 }
 const SoftReal ratio=d/c,denominator=ratio*ratio*c+c;
 return {x87::binary64(((SoftReal)a.imag*ratio+a.real)/denominator),x87::binary64(((SoftReal)a.imag-(SoftReal)a.real*ratio)/denominator)};
}
}

namespace {
using x87::binary64;
struct Transfer { ComplexValue slope,offset; };
Transfer transfer(int layer,const PotentialLayers& layers) {
    ComplexValue slope{1,0},offset{layers.depths[0],0};
    for(int k=1;k<=layer;++k) {
        const auto ratio=legacy::divide(layers.coefficients[k],layers.coefficients[k-1]);
        const SoftReal real=((SoftReal)ratio.real-1.0)*layers.depths[k],imag=(SoftReal)ratio.imag*layers.depths[k];
        const ComplexValue next{binary64((SoftReal)ratio.real*slope.real-(SoftReal)ratio.imag*slope.imag),
                                binary64((SoftReal)ratio.imag*slope.real+(SoftReal)ratio.real*slope.imag)};
        offset={binary64((real*slope.real-imag*slope.imag)+offset.real),
                binary64((real*slope.imag+imag*slope.real)+offset.imag)};
        slope=next;
    }
    return {slope,offset};
}
ComplexValue slope_to(int layer,const PotentialLayers& layers) {
    ComplexValue result{1,0};
    for(int k=1;k<=layer;++k) {
        const auto ratio=legacy::divide(layers.coefficients[k],layers.coefficients[k-1]);
        result={binary64((SoftReal)ratio.real*result.real-(SoftReal)ratio.imag*result.imag),
                binary64((SoftReal)result.imag*ratio.real+(SoftReal)ratio.imag*result.real)};
    }
    return result;
}
ComplexValue finish(const Transfer& t,int layer,double height,const ComplexValue& denominator,const PotentialLayers& layers) {
    const SoftReal real=(SoftReal)t.offset.real-(SoftReal)height*t.slope.real,
        imag=(SoftReal)t.offset.imag-(SoftReal)height*t.slope.imag;
    const auto& coefficient=layers.coefficients[layer];
    const ComplexValue numerator{binary64(real*coefficient.real-imag*coefficient.imag),
                                 binary64(imag*coefficient.real+(SoftReal)coefficient.imag*real)};
    return legacy::divide(numerator,denominator);
}
}
ComplexValue potential_zero_a(int source_layer,int target_layer,double height,const PotentialLayers& layers) {
    const auto t=transfer(source_layer,layers);
    return finish(t,target_layer,height,slope_to(target_layer,layers),layers);
}
ComplexValue potential_zero_b(int,int target_layer,double,double target_height,const PotentialLayers& layers) {
    const auto t=transfer(target_layer,layers);
    return finish(t,target_layer,target_height,t.slope,layers);
}
namespace {
int wrap_add(int a,int b) { return static_cast<int>(static_cast<unsigned>(a)+static_cast<unsigned>(b)); }
int wrap_sub(int a,int b) { return static_cast<int>(static_cast<unsigned>(a)-static_cast<unsigned>(b)); }
int wrap_mul(int a,int b) { return static_cast<int>(static_cast<unsigned>(a)*static_cast<unsigned>(b)); }
int distance_index(int a,int b) { const int d=wrap_sub(a,b);return d>0?d:wrap_sub(0,d); }
int folded_index(int a,int b,int limit) { const int sum=wrap_add(a,b);return sum<limit?sum:wrap_sub(wrap_add(limit,limit),sum); }
struct AxisIndices { int d00,d01,d10,d11,s00,s01,s10,s11; };
AxisIndices indices(int a0,int a1,int b0,int b1,int limit) {
    return {distance_index(a0,b0),distance_index(a0,b1),distance_index(a1,b0),distance_index(a1,b1),
            folded_index(a0,b0,limit),folded_index(a0,b1,limit),folded_index(a1,b0,limit),folded_index(a1,b1,limit)};
}
struct ExtendedValue { SoftReal real,imag; };
ExtendedValue difference(const ComplexValue& a,const ComplexValue& b) { return {(SoftReal)a.real-b.real,(SoftReal)a.imag-b.imag}; }
ExtendedValue axis_sum(const ComplexValue* table,const AxisIndices& i) {
    const auto first=difference(table[i.d11],table[i.s11]),second=difference(table[i.d00],table[i.s00]),
        third=difference(table[i.s10],table[i.d10]),fourth=difference(table[i.s01],table[i.d01]);
    return {((second.real+binary64(first.real))+third.real)+fourth.real,
            ((second.imag+binary64(first.imag))+third.imag)+fourth.imag};
}
ExtendedValue complex_scale(ExtendedValue a,int factor) {
    return {a.real*factor-a.imag*0.0,a.imag*factor+a.real*0.0};
}
ComplexValue rounded(ExtendedValue a) { return {binary64(a.real),binary64(a.imag)}; }
ComplexValue divide_real(const ComplexValue& a,double b) { return legacy::divide(a,ComplexValue{b,0}); }
ComplexValue add(const ComplexValue& a,const ComplexValue& b) { return {binary64((SoftReal)a.real+b.real),binary64((SoftReal)a.imag+b.imag)}; }
}
ComplexValue contact_base(int source,int target,const PotentialGeometry& g) {
    int source_layer,target_layer;double source_height,target_height;
    source_layer=g.metals[source].layer;
    target_layer=g.metals[target].layer;
    source_height=g.metals[source].height;
    target_height=g.metals[target].height;
    const SoftReal source_half=source==target?0:(SoftReal)g.metals[source].thickness*0.5,
        target_half=source==target?0:(SoftReal)g.metals[target].thickness*0.5;
    ComplexValue term=source_height<target_height?
        potential_zero_b(source_layer,target_layer,binary64((SoftReal)source_height+source_half),binary64((SoftReal)target_height-target_half),g.layers):
        potential_zero_a(source_layer,target_layer,binary64((SoftReal)source_height-source_half),g.layers);
    term=divide_real(divide_real(term,g.width),g.height);
    return {binary64(SoftReal(0.0)+term.real),binary64(SoftReal(0.0)+term.imag)};
}
ComplexValue contact_potential(const PotentialContact& a,const PotentialContact& b,const PotentialGeometry& g,const PotentialTables& tables,const ComplexValue* base) {
    const auto x=indices(a.x0,a.x1,b.x0,b.x1,g.nx),y=indices(a.y0,a.y1,b.y0,b.y1,g.ny);
    ComplexValue total=base?*base:contact_base(a.metal,b.metal,g);
    ComplexValue term;
    constexpr double factor=0x1.3bd3cc9be45dep+4;
    const int area_x=wrap_mul(wrap_sub(b.x1,b.x0),wrap_sub(a.x1,a.x0)),
        area_y=wrap_mul(wrap_sub(b.y1,b.y0),wrap_sub(a.y1,a.y0));
    term=rounded(complex_scale(axis_sum(tables.x,x),wrap_mul(g.nx,g.nx)));
    term=divide_real(divide_real(divide_real(divide_real(term,g.width),g.height),factor),area_x);
    total=add(total,term);
    term=rounded(complex_scale(axis_sum(tables.y,y),wrap_mul(g.ny,g.ny)));
    term=divide_real(divide_real(divide_real(divide_real(term,g.width),g.height),factor),area_y);
    total=add(total,term);
    const int rows[]={x.d11,x.d00,x.s10,x.s01,x.s11,x.s00,x.d10,x.d01};
    const int positive[]={y.d00,y.d11,y.s10,y.s01},negative[]={y.s00,y.s11,y.d10,y.d01};
    ExtendedValue combined{};
    for(int row=0;row<8;++row)for(int column=0;column<4;++column) {
        const int j=column<2?1-column:column;
        const int offset=wrap_mul(rows[row],wrap_add(g.nx,1));
        const auto delta=difference(tables.xy[wrap_add(offset,positive[j])],tables.xy[wrap_add(offset,negative[j])]);
        if(row==0 && column==0)combined={binary64(delta.real),binary64(delta.imag)};
        else if(row<4) { combined.real+=delta.real;combined.imag+=delta.imag; }
        else { combined.real-=delta.real;combined.imag-=delta.imag; }
    }
    term=rounded(complex_scale(complex_scale(combined,wrap_mul(g.nx,g.nx)),wrap_mul(g.ny,g.ny)));
    term=divide_real(divide_real(divide_real(divide_real(divide_real(divide_real(term,area_x),area_y),g.width),g.height),factor),factor);
    return add(total,term);
}
}

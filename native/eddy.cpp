// Retained SoftFloat port of recomp_cpp/src/eddy.cpp.
#include "eddy_port.hpp"




namespace asitic {
namespace {
using x87::binary64;
int reflected(int index,int turns) {
    while(index>turns)index=static_cast<int>(2u*static_cast<unsigned>(turns)-static_cast<unsigned>(index)+1u);
    return index;
}
SoftReal wire_length(const double* a) {
    const SoftReal dx=(SoftReal)a[3]-a[0],dy=(SoftReal)a[4]-a[1],dz=(SoftReal)a[5]-a[2];
    return x87::sqrt((dx*dx+dy*dy)+dz*dz);
}
SoftReal integral(double frequency,double separation,double height,double width,const EddyEnvironment& e) {
    GreenStats stats;const auto result=integrate_reflection(frequency,separation,height,*e.state,stats);
    ++*e.calls;if(stats.status>=0&&stats.status<8)++e.statuses[(stats.cycles?8:0)+stats.status];return result;
}
int rounded_integer(SoftReal value,unsigned short mode) {
    return extF80_to_i32(extF80_roundToInt(value.value,mode==0x0800u?softfloat_round_max:softfloat_round_min,false),softfloat_round_minMag,false);
}
const ConductorSegment* next_segment(const ConductorSegment* segment) {
    return reinterpret_cast<const ConductorSegment*>(segment->next_address);
}
void read_wire(const ConductorSegment* segment,double* wire) {
    __builtin_memcpy(wire,segment,7*sizeof(double));
}
}
int eddy_packed_index(int index,int turns) {
    const unsigned i=static_cast<unsigned>(index),n=static_cast<unsigned>(turns);
    return static_cast<int>(index<=turns?4u*i-3u:4u*n-(4u*(i-1u-n)+1u));
}
SoftReal eddy_folded_position(int index,double dimension,double width,double spacing,int turns) {
    index=reflected(index,turns);
    const int offset=static_cast<int>(static_cast<unsigned>(index)-1u);
    return ((SoftReal)dimension-width)-((SoftReal)width+spacing)*((SoftReal)offset+offset);
}
SoftReal eddy_signed_half_position(int index,double dimension,double width,double spacing,int turns) {
    if(index>turns) {
        const int folded=static_cast<int>(2u*static_cast<unsigned>(turns)-static_cast<unsigned>(index)+1u);
        return -eddy_signed_half_position(folded,dimension,width,spacing,turns);
    }
    const int offset=static_cast<int>(static_cast<unsigned>(index)-1u);
    return ((SoftReal)dimension-width)*SoftReal(0.5)-((SoftReal)width+spacing)*offset;
}
SoftReal eddy_signed_separation(int i,int j,double dimension,double width,double spacing,int turns) {
    const int a=static_cast<int>(static_cast<unsigned>(reflected(i,turns))-1u),
              b=static_cast<int>(static_cast<unsigned>(reflected(j,turns))-1u);
    const SoftReal step=(SoftReal)width+spacing,base=(SoftReal)dimension-width;
    const SoftReal result=x87::sqrt((base-((SoftReal)a+a)*step)*(base-((SoftReal)b+b)*step));
    return (i>turns)!=(j>turns)?-result:result;
}
SoftReal eddy_axial_length(const double* wire) {
    return wire_length(wire)-((SoftReal)wire[6]+wire[6]);
}
int eddy_classify_pair(const double* a,const double* b,double* product) {
    const SoftReal ax=(SoftReal)a[3]-a[0],ay=(SoftReal)a[4]-a[1],az=(SoftReal)a[5]-a[2],
        bx=(SoftReal)b[3]-b[0],by=(SoftReal)b[4]-b[1],bz=(SoftReal)b[5]-b[2];
    const SoftReal dot=(ax*bx+by*ay)+az*bz;
    *product=binary64(dot);
    if(0x1.b7cdfd9d7bdbbp-34>x87::abs(dot))return 7;
    const double al=binary64(wire_length(a)),bl=binary64(wire_length(b)),
        d1=binary64(distance(a,b)),d2=binary64(distance(a,b+3)),d3=binary64(distance(a+3,b));
    const SoftReal d4=distance(a+3,b+3);
    SoftReal nearest=d1<d2?d1:d2;
    if(!(nearest<d3))nearest=d3;
    if(!(nearest<d4))nearest=d4;
    const double shorter=al<bl?al:bl;
    if((SoftReal)shorter*SoftReal(0.5)<nearest)return 9;
    const SoftReal cosine=(SoftReal)*product/((SoftReal)al*bl);
    *product=binary64(cosine);
    return 0x1.fe0ded288ce70p-1<=x87::abs(cosine)?0:9;
}
SoftReal eddy_axial_term(const double* wire,double frequency,const EddyEnvironment& e) {
    const SoftReal length=eddy_axial_length(wire);
    const double height=binary64(((SoftReal)e.coordinate_scale+e.coordinate_scale)*wire[2]),
        width=binary64((SoftReal)e.coordinate_scale*wire[6]);
    const SoftReal value=integral(frequency,0,height,width,e);
    return (length*e.coordinate_scale)*value;
}
SoftReal eddy_pair_term(const double* a,const double* b,double frequency,const EddyEnvironment& e) {
    double product;
    if(eddy_classify_pair(a,b,&product)!=0)return 0;
    const SoftReal dx=(SoftReal)a[0]-b[0],dz=x87::abs((SoftReal)a[2]-b[2]);
    constexpr double threshold=0x1.b7cdfd9d7bdbbp-34,scale=0x1.0c6f7a0b5ed8dp-20;
    if(x87::abs(dx)<threshold && x87::abs(dz)<threshold)return 0;
    const SoftReal distance_ab=distance(a,b),square=(distance_ab*distance_ab-dx*dx)-dz*dz;
    const SoftReal separation=threshold>x87::abs(square)?0:x87::sqrt(square)*scale;
    const double al=binary64(eddy_axial_length(a)),bl=binary64(eddy_axial_length(b));
    const SoftReal length=x87::sqrt((SoftReal)al*bl)*scale;
    const double height=binary64(((SoftReal)a[2]+b[2])*scale),
        width=binary64((SoftReal)a[6]*e.coordinate_scale);
    const SoftReal value=integral(frequency,binary64(separation),height,width,e);
    return (length*product)*value;
}
void assemble_eddy_matrix(RealMatrixView out,const SquareSpiralGeometry& g,double frequency,double height,const EddyEnvironment& e) {
    const int n=rounded_integer(g.turns,0x0800u),size=2*n;
    const double dimension=binary64((SoftReal)e.coordinate_scale*g.dimension),
        width=binary64((SoftReal)e.coordinate_scale*g.width);
    const SoftReal spacing_extended=(SoftReal)e.coordinate_scale*g.spacing,
        pitch_extended=spacing_extended+width;
    const double spacing=binary64(spacing_extended),pitch=binary64(pitch_extended),
        inner=binary64((SoftReal)binary64((SoftReal)dimension-((SoftReal)(n-1)+(n-1))*pitch_extended)
            -((SoftReal)width+width));
    const double diagonal=binary64(integral(frequency,0,height,width,e));
    for(int i=1;i<=size;++i)out.at(i-1,i-1)=binary64(eddy_folded_position(i,dimension,width,spacing,n)*diagonal);
    for(int i=1;i<=n;++i)for(int j=i+1;j<=n;++j) {
        const SoftReal factor=eddy_signed_separation(i,j,dimension,width,spacing,n);
        if(i==1)out.at(0,j-1)=binary64(factor*integral(frequency,binary64((SoftReal)pitch*(j-1)),height,width,e));
        else {
            const SoftReal previous=eddy_signed_separation(i-1,j-1,dimension,width,spacing,n);
            out.at(i-1,j-1)=binary64((factor*out.at(i-2,j-2))/previous);
        }
    }
    for(int i=1;i<=n;++i) {
        const SoftReal factor=eddy_signed_separation(i,n+1,dimension,width,spacing,n);
        out.at(i-1,n)=binary64(factor*integral(frequency,binary64((SoftReal)pitch*(n-i)+inner),height,width,e));
    }
    for(int i=1;i<=n;++i)for(int j=n+2;j<=size;++j) {
        const SoftReal factor=eddy_signed_separation(i,j,dimension,width,spacing,n);
        if(i==1)out.at(0,j-1)=binary64(factor*integral(frequency,binary64((SoftReal)pitch*(j-2)+inner),height,width,e));
        else {
            const SoftReal previous=eddy_signed_separation(i-1,j-1,dimension,width,spacing,n);
            out.at(i-1,j-1)=binary64((factor*out.at(i-2,j-2))/previous);
        }
    }
    for(int i=n+1;i<=size;++i)for(int j=n+2;j<=size;++j) {
        const SoftReal factor=eddy_signed_separation(i,j,dimension,width,spacing,n),
            previous=eddy_signed_separation(i-n,j-n,dimension,width,spacing,n);
        out.at(i-1,j-1)=binary64((factor*out.at(i-n-1,j-n-1))/previous);
    }
    for(int i=1;i<=size;++i)for(int j=1;j<i;++j)out.at(i-1,j-1)=out.at(j-1,i-1);
}
void fold_eddy_segments(const ShapeFilamentList& shape,ComplexMatrixView out,unsigned rows,
    double frequency,int metal_count,const EddyEnvironment& e) {
    unsigned row=0;
    for(auto* segment=shape.first;segment;segment=next_segment(segment))if(segment->metal<metal_count) {
        double wire[7];read_wire(segment,wire);
        const SoftReal term=eddy_axial_term(wire,frequency,e);
        auto& value=out.at(row,row);
        value.real=binary64((SoftReal)value.real+term);
        value.imag=binary64((SoftReal)value.imag+SoftReal(0.0));++row;
    }
    row=0;
    for(auto* a=shape.first;a;a=next_segment(a))if(a->metal<metal_count) {
        unsigned column=row+1;
        for(auto* b=next_segment(a);b && column<rows;b=next_segment(b),++column) {
            double aw[7],bw[7];read_wire(a,aw);read_wire(b,bw);
            const SoftReal term=eddy_pair_term(aw,bw,frequency,e);
            auto& upper=out.at(row,column);
            upper.real=binary64((SoftReal)upper.real+term);
            upper.imag=binary64((SoftReal)upper.imag+SoftReal(0.0));
            auto& lower=out.at(column,row);
            lower.real=binary64((SoftReal)lower.real+term);
            lower.imag=binary64((SoftReal)lower.imag+SoftReal(0.0));
        }
        ++row;
    }
}
}

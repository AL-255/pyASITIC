#pragma once
#include "retained_math.hpp"
namespace asitic {
SoftReal dot(const double*,const double*);
SoftReal norm(const double*);
SoftReal distance(const double*,const double*);
void cross(const double*,const double*,double*);
SoftReal segment_self_inductance(double,double);
SoftReal cross_section_log_integral(double,double);
SoftReal effective_separation(double,double,double,double,double,double);
int parallel_segment_mutual(const double*,const double*,double*,double);
struct IntersectionHistory {double delta[3],v[3],u[3];};
int segments_intersect_parametric(const double*,const double*,const double*,const double*,double,double,IntersectionHistory&);
int canonicalize_segment_pair(double*,double*,IntersectionHistory&);
void planar_segment_mutual(const double*,const double*,double*);
void spatial_segment_mutual(const double*,const double*,double*);
int segment_mutual_value(const double*,const double*,double*,int&);
}

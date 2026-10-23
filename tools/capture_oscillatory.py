"""Probe native weighted/Chebyshev rules, moment caches and Fourier drivers."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/quadrature.hpp"
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
extern "C" double exp(double);
extern "C" double cos(double);
extern "C" double sin(double);
using namespace asitic::quadpack;
int kind;
long double callback(const double* point) {
    const double x=*point;
    if(kind==0)return double(1./double(1.+double(x*x)));
    if(kind==1)return exp(-x);
    if(kind==2)return double(1./double(1.+x));
    if(kind==3)return 1.;
    if(kind==4)return double(double(x*x)*x);
    const double t=x-.37;return t<0?-t:t;
}
long double sine(double x) { return sin(x); }
long double cosine(double x) { return cos(x); }
long double weight(const double* x,const double* f,const double*,const double*,const double*,const int* selector) {
    const double argument=double(*x**f);return *selector==2?sin(argument):cos(argument);
}
void value(double x) {
    if(__builtin_isnan(x))printf("nan ");
    else if(__builtin_isinf(x))printf(x>0?"inf ":"-inf ");
    else printf("%.17g ",x);
}
void vector(const double* x,int n) { for(int i=0;i<n;++i)value(x[i]);printf("\n"); }
void rule(const RuleResult& r) { value(r.integral);value(r.error);value(r.absolute);value(r.ascendant); }
extern "C" int probe_main(int,char** argv) {
    const int mode=atoi(argv[1]);
    if(mode==3) {
        const double c[]={0x1.fb9ea92ec689bp-1,0x1.ee8dd4748bf15p-1,0x1.d906bcf328d46p-1,0x1.bb67ae8584caap-1,0x1.963268b572492p-1,0x1.6a09e667f3bcdp-1,0x1.37af93f9513eap-1,0x1.0000000000000p-1,0x1.87de2a6aea963p-2,0x1.0907dc1930690p-2,0x1.0b5150f6da2d1p-3};
        double f[25],y[13],z[25];for(int i=0;i<25;++i)f[i]=atof(argv[i+2]);
        chebyshev_transform(c,f,y,z);vector(f,25);vector(y,13);vector(z,25);return 0;
    }
    if(mode==4) {
        const int n=atoi(argv[2]);double c[100],d[100],e[100],rhs[100];
        for(int i=0;i<n;++i) { c[i]=atof(argv[3+i]);d[i]=atof(argv[3+n+i]);e[i]=atof(argv[3+2*n+i]);rhs[i]=atof(argv[3+3*n+i]); }
        printf("%d\n",solve_tridiagonal(n,c,d,e,rhs));vector(c,n);vector(d,n);vector(e,n);vector(rhs,n);return 0;
    }
    kind=atoi(argv[2]);const double a=atof(argv[3]),b=atof(argv[4]),frequency=atof(argv[5]);
    const int selector=atoi(argv[6]),limit=atoi(argv[9]),rows=atoi(argv[10]),sequence=atoi(argv[11]);
    const double epsabs=atof(argv[7]),epsrel=atof(argv[8]);
    double moments[25000]{};MomentCache cache{moments,rows,0};
    if(mode==1) {
        const auto r=oscillatory_rule(callback,a,b,frequency,selector,0,false,cache,{sine,cosine});
        rule(r.value);printf("%d %d\n",r.evaluations,cache.computed);
        for(int j=0;j<25;++j)value(moments[j*rows]);printf("\n");return 0;
    }
    if(mode==2) { rule(weighted_rule(callback,weight,&frequency,nullptr,nullptr,nullptr,&selector,a,b));printf("\n");return 0; }
    double left[1000]{},right[1000]{},areas[1000]{},errors[1000]{};int order[1000]{},levels[1000]{};
    OscillatoryWorkspace workspace{{left,right,areas,errors,order,limit},levels};
    if(mode==5) {
        const auto r=integrate_oscillatory(callback,a,b,frequency,selector,epsabs,epsrel,sequence,workspace,cache,{sine,cosine});
        value(r.integral);value(r.error);printf("%d %d %d %d\n",r.evaluations,r.status,r.intervals,cache.computed);return 0;
    }
    const int cycles=atoi(argv[12]);double integrals[1000]{},cycle_errors[1000]{},history[3]{};int statuses[1000]{};
    FourierWorkspace fourier{workspace,integrals,cycle_errors,statuses,cycles,moments,rows,history};
    const auto r=integrate_fourier(callback,a,frequency,selector,epsabs,fourier,{sine,cosine});
    value(r.integral);value(r.error);printf("%d %d %d\n",r.evaluations,r.status,r.cycles);
    vector(integrals,r.cycles);vector(cycle_errors,r.cycles);
    for(int i=0;i<r.cycles;++i)printf("%d ",statuses[i]);printf("\n");vector(history,3);return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def number(value):
    v=float(value)
    return v if math.isfinite(v) else "nan" if math.isnan(v) else "inf" if v>0 else "-inf"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    reference=args.reference.resolve()
    objects=[reference/f"recomp_cpp/build/{name}.o" for name in ("oscillatory","quadrature")]
    fixture=dict(rules=[],weighted=[],chebyshev=[],tridiagonal=[],oscillatory=[],fourier=[])
    with tempfile.TemporaryDirectory(prefix="reasitic-oscillatory-reference-") as directory:
        source=Path(directory,"probe.cpp");source.write_text(SOURCE)
        binary=Path(directory,"probe")
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),*map(str,objects),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        def probe(*values):
            return [[number(v) for v in line.split()] for line in subprocess.check_output([str(binary),*map(str,values)],text=True).splitlines()]
        for kind in (0,1,3,4):
            for frequency in (-100,-24,-4,-1,0,1,4,math.nextafter(4,math.inf),24,48,100):
                for selector in (1,2):
                    for rows in (1,4):
                        values=probe(1,kind,0,1,frequency,selector,1e-10,1e-10,100,rows,1)
                        fixture["rules"].append(dict(kind=kind,a=0,b=1,frequency=frequency,selector=selector,rows=rows,
                                                     result=dict(zip(("integral","error","absolute","ascendant","evaluations","computed"),values[0])),moments=values[1]))
                    values=probe(2,kind,-.5,1,frequency,selector,1e-10,1e-10,100,4,1)
                    fixture["weighted"].append(dict(kind=kind,a=-.5,b=1,frequency=frequency,selector=selector,result=dict(zip(("integral","error","absolute","ascendant"),values[0]))))
        for samples in ([1.0]*25,[i/24 for i in range(25)],[(i%7-3)+i*i/1000 for i in range(25)],[(i/24)**4 for i in range(25)]):
            samples=list(samples);samples[0]/=2;samples[24]/=2
            values=probe(3,*samples)
            fixture["chebyshev"].append(dict(samples=samples,overwritten=values[0],degree12=values[1],degree24=values[2]))
        for n in (1,2,5,25):
            for singular in (False,True):
                c=[0.0]+[-1.0]*(n-1);d=[3.+i/10 for i in range(n)];e=[-.5]*(n-1)+[0.0];rhs=[i+1.0 for i in range(n)]
                if singular:c,d,e=[0.0]*n,[0.0]*n,[0.0]*n
                values=probe(4,n,*c,*d,*e,*rhs)
                fixture["tridiagonal"].append(dict(c=c,d=d,e=e,rhs=rhs,status=int(values[0][0]),overwritten=values[1:]))
        for kind in (0,1,4,5):
            for frequency in (-25,-1,0,1,4,25,100):
                for selector in (1,2):
                    for limit in (1,5,100):
                        values=probe(5,kind,0,10,frequency,selector,1e-10,1e-10,limit,4,1)
                        fixture["oscillatory"].append(dict(kind=kind,a=0,b=10,frequency=frequency,selector=selector,absolute_tolerance=1e-10,relative_tolerance=1e-10,limit=limit,rows=4,
                                                           result=dict(zip(("integral","error","evaluations","status","intervals","computed"),values[0]))))
        for kind in (0,1,2,3):
            for frequency in (-1,0,.1,1,25):
                for selector in (1,2):
                    for cycles in (3,50):
                        values=probe(6,kind,0,1,frequency,selector,1e-8,0,100,25,1,cycles)
                        fixture["fourier"].append(dict(kind=kind,start=0,frequency=frequency,selector=selector,absolute_tolerance=1e-8,limit=100,moment_rows=25,cycle_limit=cycles,
                                                       result=dict(zip(("integral","error","evaluations","status","cycles"),values[0])),cycle_integrals=values[1],cycle_errors=values[2],cycle_statuses=values[3],history=values[4]))
    output=ROOT/"tests/fixtures/oscillatory.json"
    output.write_text(json.dumps(dict(reference="Direct probes of unmodified 32-bit C++ oscillatory/QUADPACK objects",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),object_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objects},probe=SOURCE,**fixture),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":
    main()

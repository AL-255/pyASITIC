"""Build an independent C++ QUADPACK probe and save native numerical records."""
import argparse
import hashlib
import json
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
extern "C" double sin(double);
extern "C" double sqrt(double);
using namespace asitic::quadpack;
int kind;
double scale;
long double callback(const double* x) {
    // Explicit binary64 leaf operations make probe callback precision the same
    // as the standalone Python fixture callbacks, independently of QUADPACK.
    const double t=*x;
    if(kind==0) { const double a=1.+t;return double(1./double(a*a)); }
    if(kind==1)return double(1./double(1.+double(t*t)));
    if(kind==2)return double(exp(double(-scale*t)));
    if(kind==3)return double(exp(double(-double(t*t))));
    if(kind==4)return double(sin(t)/double(1.+double(t*t)));
    if(kind==5)return 1.;
    return double(exp(-t)/sqrt(t));
}
extern "C" int probe_main(int argc,char** argv) {
    kind=atoi(argv[1]);scale=atof(argv[2]);
    const double bound=atof(argv[3]);const int direction=atoi(argv[4]);
    const double epsabs=atof(argv[5]),epsrel=atof(argv[6]);const int limit=atoi(argv[7]);
    if(argc==10) {
        const auto r=infinite_rule(callback,bound,direction,atof(argv[8]),atof(argv[9]));
        printf("%.17g %.17g %.17g %.17g\n",r.integral,r.error,r.absolute,r.ascendant);
    } else {
        double left[1000]{},right[1000]{},areas[1000]{},errors[1000]{};int order[1000]{};
        const auto r=integrate_infinite(callback,bound,direction,epsabs,epsrel,{left,right,areas,errors,order,limit});
        printf("%.17g %.17g %d %d %d\n",r.integral,r.error,r.evaluations,r.status,r.intervals);
    }
    return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    reference=args.reference.resolve()
    obj=reference/"recomp_cpp/build/quadrature.o"
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-quadpack-reference-") as directory:
        source=Path(directory,"probe.cpp");source.write_text(SOURCE)
        binary=Path(directory,"probe")
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),str(obj),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        configs=[(0,1,0,1),(1,1,0,1),(1,1,0,-1),(1,1,0,2),(1,1,2,1),(2,1,0,1),(2,.001,0,1),(2,1000,0,1),(3,1,0,2),(4,1,0,1),(5,1,0,1),(6,1,0,1)]
        for kind,scale,bound,direction in configs:
            for epsabs,epsrel,limit in [(0,1e-6,200),(1e-10,1e-10,200),(0,1e-6,1),(0,1e-6,5),(0,0,200)]:
                args=list(map(str,(kind,scale,bound,direction,epsabs,epsrel,limit)))
                values=subprocess.check_output([str(binary),*args],text=True).split()
                result=dict(zip(("integral","error","evaluations","status","intervals"),[float(v) if i<2 else int(v) for i,v in enumerate(values)]))
                case=dict(kind=kind,scale=scale,bound=bound,direction=direction,absolute_tolerance=epsabs,relative_tolerance=epsrel,limit=limit,result=result)
                cases.append(case)
        rules=[]
        for kind,scale,bound,direction in configs:
            for a,b in [(0,1),(.25,.5),(.0001,.001)]:
                args=list(map(str,(kind,scale,bound,direction,0,1e-6,200,a,b)))
                values=list(map(float,subprocess.check_output([str(binary),*args],text=True).split()))
                rules.append(dict(kind=kind,scale=scale,bound=bound,direction=direction,a=a,b=b,
                                  result=dict(zip(("integral","error","absolute","ascendant"),values))))
    output=ROOT/"tests/fixtures/quadrature.json"
    output.write_text(json.dumps(dict(reference="Direct probe of the unmodified C++ quadrature object",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),probe=SOURCE,cases=cases,rules=rules),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":
    main()

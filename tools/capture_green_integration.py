"""Probe the complete original Green integration wrapper and evaluation trace."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/green_integration.hpp"
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
extern "C" double sin(double);
extern "C" double cos(double);
long double sine(double x) { return sin(x); }
long double cosine(double x) { return cos(x); }
struct Trace { int calls,status;double first,last; };
void observe(void* context,double k) { auto& t=*static_cast<Trace*>(context);if(t.calls++==0)t.first=k;t.last=k; }
void diagnostic(void* context,const char*,int,int status,int) { static_cast<Trace*>(context)->status=status; }
void value(double x) { if(__builtin_isnan(x))printf("nan ");else if(__builtin_isinf(x))printf(x>0?"inf ":"-inf ");else printf("%.17g ",x); }
extern "C" int probe_main(int,char** argv) {
    asitic::GreenIntegrationState state{{atof(argv[1]),atof(argv[2]),atof(argv[3])},0,0,0,0,
        atoi(argv[4])?asitic::GreenKernel::reflection:asitic::GreenKernel::oscillating};
    asitic::GreenIntegrationWorkspace workspace{};Trace trace{};
    asitic::GreenIntegrationRuntime runtime{{sine,cosine},{diagnostic,&trace},nullptr,observe,&trace,nullptr};
    const double frequency=atof(argv[5]),separation=atof(argv[6]),height=atof(argv[7]),width=atof(argv[8]);
    const auto integral=asitic::green_integral(frequency,separation,height,width,state,workspace,runtime);
    value(double(integral));printf("%d %d ",trace.status,trace.calls);value(trace.first);value(trace.last);
    value(state.frequency);value(state.separation);value(state.height);value(state.z_offset);
    for(double v:workspace.history)value(v);printf("\n");return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    objects=[reference/f"recomp_cpp/build/{name}.o" for name in ("green_integration","green","legacy_complex","quadrature_wrappers","quadrature","oscillatory")]
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-green-integral-reference-") as directory:
        source=Path(directory,"probe.cpp");source.write_text(SOURCE);binary=Path(directory,"probe")
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),*map(str,objects),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        configs=[(*layers,frequency,separation,height,5e-6)
                 for layers in ((1e5,0,0,"reflection"),(1e-8,1e5,5e-5,"oscillating"),(1e4,1e5,5e-5,"oscillating"))
                 for frequency in (1e6,1e9,20e9) for height in (2.6e-6,1e-4) for separation in (0,5e-6,5e-4)]
        configs.extend((1e5,0,0,"reflection",1e9,separation,2.6e-6,5e-6)
                       for separation in (math.nextafter(1e-10,0),1e-10,math.nextafter(1e-10,math.inf),-1e-10))
        for layer1,layer2,depth,kernel,frequency,separation,height,width in configs:
            args=list(map(str,(layer1,layer2,depth,int(kernel=="reflection"),frequency,separation,height,width)))
            raw=subprocess.check_output([str(binary),*args],text=True).split()
            vals=[float(v) if math.isfinite(float(v)) else "nan" if math.isnan(float(v)) else "inf" if float(v)>0 else "-inf" for v in raw]
            cases.append(dict(layer1=layer1,layer2=layer2,depth=depth,kernel=kernel,frequency=frequency,separation=separation,height=height,z_offset=width,
                              value=vals[0],status=int(vals[1]),observations=int(vals[2]),first_point=vals[3],last_point=vals[4],state=vals[5:9],history=vals[9:]))
    output=ROOT/"tests/fixtures/green_integration.json"
    output.write_text(json.dumps(dict(reference="Direct unmodified 32-bit C++ Green integration wrapper and callback trace",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),object_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objects},probe=SOURCE,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":main()

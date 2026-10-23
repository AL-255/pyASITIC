"""Capture the unmodified native SELFRES search with controlled Y callbacks."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/analysis_commands.hpp"
extern "C" int printf(const char*,...);
extern "C" int sprintf(char*,const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
using namespace asitic;
TwoPortAdmittance ports{};int kind,calls;double target,scale,fixed;
void value(double x) { if(__builtin_isnan(x))printf("nan ");else if(__builtin_isinf(x))printf(x>0?"inf ":"-inf ");else printf("%.17g ",x); }
void analyze(const GeometryShape&,double f,int fast,const GeometryShape&,void*) {
    ++calls;printf("A ");value(f);printf("%d\n",fast);
    double imag=kind==0?double(double(f-target)*scale):fixed;
    ports={{1.,.5},{.01,.02},{.01,.02},{kind==2?0.:1.,imag}};
}
int progress(const char* format,...) {
    __builtin_va_list args;__builtin_va_start(args,format);printf("P ");
    for(int i=0;i<4;++i)value(__builtin_va_arg(args,double));
    __builtin_va_end(args);printf("\n");return 0;
}
int flush(void*) { return 0; }
void warning(const char* text,void*) { printf("W %s\n",text); }
extern "C" int probe_main(int,char** argv) {
    kind=atoi(argv[1]);target=atof(argv[2]);scale=atof(argv[3]);fixed=atof(argv[4]);
    GeometryShape shape{};char buffer[1024];
    SelfResonanceRuntime runtime{analyze,nullptr,&ports,progress,flush,nullptr,{buffer,sprintf,{warning,nullptr},nullptr,nullptr,nullptr,nullptr}};
    const long double result=find_self_resonant_frequency(shape,atof(argv[5]),atof(argv[6]),atof(argv[7]),atoi(argv[8]),atoi(argv[9]),atoi(argv[10]),shape,runtime);
    printf("R ");value(double(result));printf("%d\n",calls);return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();native=reference/"recomp_cpp"
    flags=["-m32","-O2","-mfpmath=387","-fno-fast-math","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-fno-builtin","-std=c++17"]
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-resonance-reference-") as directory:
        path=Path(directory);source=path/"probe.cpp";source.write_text(SOURCE)
        # Function sections let the linker discard unrelated console commands;
        # the native search source itself is compiled without modification.
        subprocess.run(["g++",*flags,"-ffunction-sections","-fdata-sections","-I",str(native/"include"),"-c",str(native/"src/analysis_commands.cpp"),"-o",str(path/"search.o")],check=True)
        objects=[native/"build/network.o",native/"build/legacy_complex.o"]
        binary=path/"probe"
        subprocess.run(["g++",*flags,"-nostdlib","-no-pie","-I",str(native/"include"),str(source),str(path/"search.o"),*map(str,objects),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--gc-sections","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        bounds=[(1e9,20e9,1e7),(20e9,1e9,1e7),(1e9+3.25,1e9+57.75,7.7),(1.,math.nextafter(1.,2.),1.),(1e9,1e9,1e8),(1e9,2e9,0.),(1e9,2e9,-1.),(1e9,2e9,1e12)]
        for differential in (False,True):
            for fast in (False,True):
                for first,second,step in bounds:
                    if fast and step==0:continue
                    callbacks=((0,0.),(1,0.),(1,2.),(1,-.009),(1,.01),(1,math.nan),(2,100.),(2,-100.),(2,-math.nextafter(100.,0.)),(2,-math.nextafter(100.,math.inf)))
                    for kind,fixed in callbacks:
                        if kind==2 and (differential or fast or (first,second,step)!=bounds[0]):continue
                        case=dict(kind=kind,target=7.13579e9,scale=1e-9,fixed="nan" if math.isnan(fixed) else fixed,
                                  first=first,second=second,step=step,differential=differential,fast=fast,iteration_limit=1)
                        raw=subprocess.check_output([str(binary),*map(str,(kind,case["target"],case["scale"],case["fixed"],first,second,step,int(differential),int(fast),1))],text=True)
                        analyses=[];progress=[];warnings=[]
                        for line in raw.splitlines():
                            tag,*tokens=line.split()
                            if tag=="A":analyses.append([float(tokens[0]),int(tokens[1])])
                            elif tag=="P":progress.append(["nan" if math.isnan(float(v)) else float(v) for v in tokens])
                            elif tag=="W":warnings.append(" ".join(tokens))
                            elif tag=="R":case.update(native_result_hz=float(tokens[0]),evaluations=int(tokens[1]))
                        case.update(analyses=analyses,progress=progress,warnings=warnings);cases.append(case)
    output=ROOT/"tests/fixtures/resonance_search.json"
    output.write_text(json.dumps(dict(reference="Unmodified native SELFRES source with controlled admittance callbacks",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),source_sha256=hashlib.sha256((native/"src/analysis_commands.cpp").read_bytes()).hexdigest(),object_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objects},compile_flags=flags,probe=SOURCE,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases))


if __name__=="__main__":main()

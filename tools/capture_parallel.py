"""Probe retained native self, cross-section, separation and parallel kernels."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/numerics.hpp"
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
using namespace asitic;
extern "C" int probe_main(int,char** argv) {
    int mode=atoi(argv[1]);double p[17]{};for(int i=0;i<(mode<2?2:mode==2?6:17);++i)p[i]=atof(argv[i+2]);
    if(mode==0)printf("%.17g\n",double(segment_self_inductance(p[0],p[1])));
    else if(mode==1)printf("%.17g\n",double(cross_section_log_integral(p[0],p[1])));
    else if(mode==2)printf("%.17g\n",double(effective_separation(p[0],p[1],p[2],p[3],p[4],p[5])));
    else {
        double result=423.;int status=mode==3?parallel_segment_mutual(p,p+8,&result,p[16]):segment_mutual(p,p+8,&result);
        printf("%d %.17g\n",status,result);
    }
    return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();archive=reference/"recomp_cpp/build/libasitic_numerics.a"
    configs=[]
    for length in (0.,1e-11,.001,1.,1000.):
        for radius in (.0001,.01,1.):configs.append((0,[length,radius]))
    for x in (0.,1e-11,1e-4,-1e-4,.1):
        for y in (0.,1e-11,5e-5,-5e-5,.1):configs.append((1,[x,y]))
    for widths in ((.00025,.00025,.00005,.00005),(.01,.02,.001,.002)):
        for dx in (0.,.0001,.00025,.03):
            for dy in (0.,.0001,.03):configs.append((2,[*widths,dx,dy]))
    positions=[(-2.,-1.),(2.,3.),(-.5,.5),(.5,1.5),(-.5,1.5),(.25,.75),(0.,1.),(1.,0.),(.5,.5)]
    for scale in (1.,.002):
        for lo,hi in positions:
            for y in (0.,.125*scale,2*scale):
                for sep in (0.,.1*scale):
                    a=[0.,0.,0.,scale,0.,0.,.125*scale,.025*scale]
                    b=[lo*scale,y,0.,hi*scale,y,0.,.125*scale,.025*scale]
                    configs.append((3,[*a,*b,sep]))
    a=[10.,21.25,4.35,30.,21.25,4.35,2.5,.5]
    for b in ([10.,23.75,4.35,30.,23.75,4.35,2.5,.5],[30.,21.25,4.35,50.,21.25,4.35,2.5,.5],[30.,23.75,4.35,50.,23.75,4.35,2.5,.5]):configs.append((4,[*a,*b,0.]))
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-parallel-reference-") as directory:
        path=Path(directory);source=path/"probe.cpp";source.write_text(SOURCE);binary=path/"probe"
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),str(archive),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        for mode,values in configs:
            raw=subprocess.check_output([str(binary),str(mode),*map(str,values)],text=True).split();result=float(raw[-1])
            cases.append(dict(mode=mode,input=values,value=result if math.isfinite(result) else "nan" if math.isnan(result) else "inf" if result>0 else "-inf",status=int(raw[0]) if mode>=3 else 0))
    output=ROOT/"tests/fixtures/parallel.json"
    output.write_text(json.dumps(dict(reference="Direct unmodified native self/separation/parallel and full segment kernels",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),probe=SOURCE,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases))


if __name__=="__main__":main()

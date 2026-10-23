"""Probe native symmetric factor/inverse and complex two-by-two eigen helpers."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/lapack.hpp"
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
using namespace asitic;
void value(const ComplexValue& z) { printf("%.17g %.17g ",z.real,z.imag); }
void matrix(const char* tag,int n,ComplexMatrixView a) {
    printf("%s ",tag);for(int i=0;i<n;++i)for(int j=0;j<n;++j)value(a.at(i,j));printf("\n");
}
extern "C" int probe_main(int,char** argv) {
    if(atoi(argv[1])) {
        ComplexValue a{atof(argv[2]),atof(argv[3])},b{atof(argv[4]),atof(argv[5])},c{atof(argv[6]),atof(argv[7])};
        ComplexValue r1{},r2{},ev{},cs{},sn{};lapack::eigen2(a,b,c,r1,r2,ev,cs,sn);
        printf("E ");value(r1);value(r2);value(ev);value(cs);value(sn);printf("\n");return 0;
    }
    int n=atoi(argv[2]),stride=atoi(argv[3]),argument=4;ComplexValue data[5000]{},work[256]{};int pivots[128]{};
    for(int i=0;i<n;++i)for(int j=0;j<n;++j) { data[j*stride+i]={atof(argv[argument]),atof(argv[argument+1])};argument+=2; }
    ComplexMatrixView a{data,stride};int status=lapack::factor_symmetric_upper_workspace(n,a,pivots,work,n);
    printf("S %d\n",status);matrix("F",n,a);printf("P ");for(int i=0;i<n;++i)printf("%d ",pivots[i]);printf("\n");
    if(status)return 0;
    status=lapack::invert_symmetric_upper(n,a,pivots,work);printf("T %d\n",status);matrix("I",n,a);return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def number(v):
    value=float(v)
    return value if math.isfinite(value) else "nan" if math.isnan(value) else "inf" if value>0 else "-inf"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();archive=reference/"recomp_cpp/build/libasitic_numerics.a"
    rng=random.Random(535);configs=[]
    for n in (1,2,3,5,8,17):
        for kind in range(3):
            a=[[0j]*n for _ in range(n)]
            for i in range(n):
                for j in range(i,n):
                    z=complex((3 if i==j else .1)*rng.uniform(.8,1.2),(2 if i==j else .3)*rng.uniform(.8,1.2))
                    if kind==1:z=complex(.001*(i+1),.003) if i==j else complex(rng.uniform(.5,1),rng.uniform(.1,.4))
                    elif kind==2:z=complex(rng.uniform(-1,1),rng.uniform(-1,1))
                    a[i][j]=a[j][i]=z
            for stride in (n,n+2):configs.append((a,stride))
    n=65;a=[[complex(3+i*.01,2) if i==j else complex(.01/(i+j+1),.02/(abs(i-j)+1)) for j in range(n)] for i in range(n)]
    configs.append((a,n+2));configs.append(([[0j,0j],[0j,0j]],2))
    configs.extend([
        ([[complex(1e-300,2e-300)]],1),
        ([[complex(1e300,2e300)]],1),
        ([[complex(2,-0.),complex(-0.,-0.)],[complex(-0.,-0.),complex(3,0.)]],2),
        ([[1+2j,.2+.1j],[13+17j,3+4j]],4),
        ([[1+0j,1j],[1j,-1+1e-4j]],2),
        ([[1+0j,0j],[0j,0j]],2),
    ])
    eigen=[(1+0j,0j,2+0j),(1+1j,2+3j,4-2j),(1+0j,1j,-1+1e-4j),(1+0j,1j,-1+0j),
           (1e-200+2e-200j,3e-200+1e-200j,-1e-200+0j),(1e100+1e100j,3e100-1e100j,-2e100+4e100j)]
    cases=[];eigen_cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-symmetric-reference-") as directory:
        path=Path(directory);source=path/"probe.cpp";source.write_text(SOURCE);binary=path/"probe"
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),str(archive),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        for matrix,stride in configs:
            n=len(matrix);arguments=[0,n,stride]+[v for row in matrix for z in row for v in (z.real,z.imag)]
            case=dict(matrix=[[[z.real,z.imag] for z in row] for row in matrix],stride=stride)
            for line in subprocess.check_output([str(binary),*map(str,arguments)],text=True).splitlines():
                tag,*values=line.split()
                if tag in ("S","T"):case[tag]=int(values[0])
                elif tag=="P":case[tag]=list(map(int,values))
                else:
                    values=list(map(number,values));pairs=[values[i:i+2] for i in range(0,len(values),2)]
                    case[tag]=[pairs[i:i+n] for i in range(0,len(pairs),n)]
            cases.append(case)
        for values in eigen:
            args=[v for z in values for v in (z.real,z.imag)]
            raw=subprocess.check_output([str(binary),"1",*map(str,args)],text=True).split()[1:]
            raw=list(map(number,raw));eigen_cases.append(dict(input=[[z.real,z.imag] for z in values],result=[raw[i:i+2] for i in range(0,len(raw),2)]))
    output=ROOT/"tests/fixtures/symmetric.json"
    output.write_text(json.dumps(dict(reference="Direct unmodified native n-workspace symmetric factor/inverse and complex eigen2",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),probe=SOURCE,cases=cases,eigen=eigen_cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases),len(eigen_cases))
    subprocess.run([sys.executable,str(ROOT/"tools/capture_original_symmetric.py"),"--reference",str(reference)],check=True)


if __name__=="__main__":main()

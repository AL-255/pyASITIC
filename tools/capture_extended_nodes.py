"""Probe native PiX node stamps and solves, including noncontiguous inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/extended_node.hpp"
extern "C" int printf(const char*,...);
extern "C" int sprintf(char*,const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
extern "C" void* malloc(unsigned);
extern "C" void free(void*);
using namespace asitic;
void* allocate(unsigned n,void*) { return malloc(n); }
void release(void* p,void*) { free(p); }
void value(const ComplexValue& z) { printf("%.17g %.17g ",z.real,z.imag); }
void matrix(const char* tag,const ComplexMatrix& m) {
    printf("%s ",tag);for(int i=0;i<m.rows;++i)for(int j=0;j<m.columns;++j)value(m.view().at(i,j));printf("\n");
}
void snapshot(const char* name,const ComplexMatrix& m,void*) { matrix(name[0]=='c'?"I":"V",m); }
extern "C" int probe_main(int,char** argv) {
    const int n=atoi(argv[1]),stride=atoi(argv[2]),stamp_only=atoi(argv[3]);int argument=4;
    ComplexValue c[8192],z[8192],sc[8192],sz[8192];
    ComplexValue* all[]={c,z,sc,sz};ComplexValue* inputs[]={c,z};ComplexValue* stamps[]={sc,sz};
    for(auto* data:all)for(int i=0;i<8192;++i)data[i]={999.,111.};
    for(auto* data:inputs)for(int i=0;i<n;++i)for(int j=0;j<n;++j) { data[j*stride+i]={atof(argv[argument]),atof(argv[argument+1])};argument+=2; }
    ComplexMatrix cap{c,stride*n,1,n,n,stride,1},ind{z,stride*n,1,n,n,stride,1};
    ComplexMatrix cap_stamp{sc,(n+4)*(n+1),1,n,n+1,n+4,1},ind_stamp{sz,(n+4)*(n+1),1,n,n+1,n+4,1};
    stamp_extended_node_columns(cap,cap_stamp);stamp_extended_node_columns(ind,ind_stamp);
    matrix("SC",cap_stamp);matrix("SZ",ind_stamp);
    bool padding=true;for(auto* data:stamps)for(int j=0;j<n+1;++j)for(int i=n;i<n+4;++i)if(data[j*(n+4)+i].real!=999. || data[j*(n+4)+i].imag!=111.)padding=false;
    printf("P %d\n",int(padding));if(stamp_only)return 0;
    TwoPortAdmittance output{};ExtendedNodeOptions options{};options.frequency=1e9;options.dump=true;options.format=sprintf;options.snapshot=snapshot;
    solve_extended_node_equations(cap,ind,output,{{allocate,nullptr},release},options);
    printf("Y ");value(output.y22);value(output.y21);value(output.y12);value(output.y11);printf("\n");return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();archive=reference/"recomp_cpp/build/libasitic_numerics.a"
    configs=[];rng=random.Random(48317)
    for n in (1,2,3,5,8,12,32,40):
        for scale in (1.,1e-6):
            for symmetric in (False,True):
                cap=[[complex((.03 if i==j else .001)*rng.uniform(.8,1.2),(.3 if i==j else -.01)*rng.uniform(.8,1.2))*scale for j in range(n)] for i in range(n)]
                ind=[[complex((2 if i==j else .03)*rng.uniform(.8,1.2),(10 if i==j else .5)*rng.uniform(.8,1.2))/scale for j in range(n)] for i in range(n)]
                if symmetric:
                    for i in range(n):
                        for j in range(i):cap[i][j]=cap[j][i];ind[i][j]=ind[j][i]
                for stride in (n,n+2):configs.append((cap,ind,stride,False))
    for a,b in ((2.**53,1.),(1e308,1e308),(1e-300,-1e-300),(float.fromhex('0x0.0000000000001p-1022'),0.)):
        cap=[[complex(a,b),complex(b,a)],[complex(-a,-b),complex(b,-a)]]
        configs.append((cap,cap,4,True))
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-extended-nodes-") as directory:
        path=Path(directory);source=path/"probe.cpp";source.write_text(SOURCE);binary=path/"probe"
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),str(archive),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        for cap,ind,stride,stamp_only in configs:
            n=len(cap);args=[str(n),str(stride),str(int(stamp_only))]
            for matrix in (cap,ind):
                args.extend(str(v) for row in matrix for z in row for v in (z.real,z.imag))
            raw=subprocess.check_output([str(binary),*args],text=True)
            case=dict(cap=[[[z.real,z.imag] for z in row] for row in cap],ind=[[[z.real,z.imag] for z in row] for row in ind],stride=stride,stamp_only=stamp_only)
            for line in raw.splitlines():
                tag,*values=line.split();values=list(map(float,values))
                if tag=="P":case["padding_untouched"]=bool(values[0]);continue
                pairs=[values[i:i+2] for i in range(0,len(values),2)]
                if tag in ("SC","SZ"):case[tag]=[pairs[i:i+n+1] for i in range(0,len(pairs),n+1)]
                else:case[tag]=pairs
            cases.append(case)
    output=ROOT/"tests/fixtures/extended_nodes.json"
    output.write_text(json.dumps(dict(reference="Direct unmodified native extended-node stamp and solve",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),probe=SOURCE,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases))


if __name__=="__main__":main()

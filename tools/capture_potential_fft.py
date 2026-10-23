"""Capture the original retained-precision potential FFT and reflected grids."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_SHA256="72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f"
SOURCE=r'''
#include "asitic/potential_tables.hpp"
extern "C" int printf(const char*,...);
extern "C" int atoi(const char*);
extern "C" double atof(const char*);
using namespace asitic;
namespace asitic_fft_trace { void potential_fft(ComplexValue*,int); }
namespace asitic_fft_trace {
void observe(int step,long double wpr,double wpi) {
    unsigned long long mantissa;unsigned short exponent;
    __builtin_memcpy(&mantissa,&wpr,8);__builtin_memcpy(&exponent,reinterpret_cast<char*>(&wpr)+8,2);
    printf("T %d %016llx %04x %a\n",step,mantissa,exponent,wpi);
}
}
extern "C" int probe_main(int,char** argv) {
    const int grid=atoi(argv[1]),nx=atoi(argv[2]),ny=atoi(argv[3]);
    const int n=grid==1?(nx+1)*(ny+1):nx;ComplexValue values[8192]{},scratch[2048]{};
    for(int i=0;i<n;++i)values[i]={atof(argv[4+2*i]),atof(argv[5+2*i])};
    if(grid==1)transform_potential_grid(values,nx,ny,scratch);
    else if(grid==2)asitic_fft_trace::potential_fft(values,nx);else potential_fft(values,nx);
    for(int i=0;i<n;++i)printf("%.17g %.17g\n",values[i].real,values[i].imag);
    return 0;
}
asm(".text\n.global _start\n_start:\n"
    "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
    "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
    "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();native=reference/"recomp_cpp"
    original=reference/"run/asitic.linux.2.2"
    if hashlib.sha256(original.read_bytes()).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError("Unexpected original ASITIC executable checksum")
    rng=random.Random(912);configs=[]
    for n in (0,1,2,4,8,16,32,64,128,256,512):
        for kind in range(7):
            values=[]
            for i in range(n):
                if kind==0:z=[rng.uniform(-1,1)*1e8,rng.uniform(-1,1)*1e-3]
                elif kind==1:z=[rng.uniform(-1,1)*1e-40,rng.uniform(-1,1)*1e-40]
                elif kind==2:z=[rng.uniform(-1,1)*1e40,rng.uniform(-1,1)*1e40]
                elif kind==3:z=[float(i==0),-0.0 if i%2 else 0.0]
                elif kind==4:z=[float((-1)**i),float((-1)**(i//2))]
                elif kind==5:z=[rng.uniform(-1,1)*1e-300,rng.uniform(-1,1)*1e-300]
                else:z=[math.ldexp(float(i%3-1),-1074),math.ldexp(float(i%5-2),-1074)]
                values.append(z)
            configs.append(dict(grid=False,nx=n,ny=0,input=values,scale=1e8 if kind==0 else 1e-40 if kind==1 else 1e40 if kind==2 else 1e-300 if kind==5 else 1e-323 if kind==6 else 1))
    for nx,ny in ((2,2),(4,4),(8,8),(8,16),(16,8),(32,32)):
        values=[[rng.uniform(-1,1)*1e8,rng.uniform(-1,1)*1e-3] for _ in range((nx+1)*(ny+1))]
        configs.append(dict(grid=True,nx=nx,ny=ny,input=values,scale=1e8))
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-std=c++17"]
    with tempfile.TemporaryDirectory(prefix="reasitic-fft-reference-") as directory:
        root=Path(directory);source=root/"probe.cpp";source.write_text(SOURCE);binary=root/"probe"
        subprocess.run(["g++",*flags,"-ffunction-sections","-fdata-sections","-I",str(native/"include"),"-c",str(native/"src/potential_tables.cpp"),"-o",str(root/"fft.o")],check=True)
        # Observe only the already computed retained wpr / binary64 wpi. The
        # instrumented copy has a separate namespace; compare its full FFT
        # output against the unmodified source to detect observer interference.
        trace=(native/"src/potential_tables.cpp").read_text().split("\nvoid transform_potential_grid(",1)[0]+"\n}\n"
        trace=trace.replace("namespace asitic {","using namespace asitic;\nnamespace asitic_fft_trace {\nvoid observe(int,long double,double);",1)
        anchor="const double wpi=x87::binary64(x87::sin(angle));"
        assert trace.count(anchor)==1
        trace=trace.replace(anchor,anchor+"\n        observe(step,wpr,wpi);")
        (root/"trace.cpp").write_text(trace)
        subprocess.run(["g++",*flags,"-ffunction-sections","-fdata-sections","-I",str(native/"include"),"-I",str(native/"src"),"-c",str(root/"trace.cpp"),"-o",str(root/"trace.o")],check=True)
        subprocess.run(["g++",*flags,"-nostdlib","-no-pie","-I",str(native/"include"),str(source),str(root/"fft.o"),str(root/"trace.o"),"/lib/i386-linux-gnu/libm.so.6","/lib/i386-linux-gnu/libc.so.6","-Wl,--gc-sections","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        for c in configs:
            arguments=[int(c["grid"]),c["nx"],c["ny"],*[v for pair in c["input"] for v in pair]]
            output=subprocess.check_output([str(binary),*map(str,arguments)],text=True)
            c["output"]=[list(map(float,line.split())) for line in output.splitlines()]
        # Execute the original instructions as a separate oracle. The loader
        # maps the intact ELF image and calls only its pure FFT routine.
        original_probe=ROOT/"tools/original_fft_probe.cpp"
        original_binary=root/"original-fft"
        subprocess.run(["g++",*flags,"-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000",str(original_probe),
                        "/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(original_binary)],check=True)
        for c in configs:
            arguments=[str(original),int(c["grid"]),c["nx"],c["ny"],*[v for pair in c["input"] for v in pair]]
            output=subprocess.check_output([str(original_binary),*map(str,arguments)],text=True,start_new_session=True)
            values=[list(map(float,line.split())) for line in output.splitlines()]
            assert len(values)==len(c["output"])
            for row,expected in zip(values,c["output"]):
                for a,b in zip(row,expected):assert struct.pack("d",a)==struct.pack("d",b),"Original/C++ FFT bits differ"
            c["output"]=values
        case=next(c for c in configs if c["nx"]==512 and not c["grid"])
        trace=subprocess.check_output([str(binary),*map(str,[2,512,0,*[v for pair in case["input"] for v in pair]])],text=True).splitlines()
        assert [list(map(float,line.split())) for line in trace if not line.startswith("T ")]==case["output"],"Observer changed native FFT output"
        twiddles=[]
        for line in trace:
            if not line.startswith("T "):continue
            _,step,mantissa,exponent,wpi=line.split()
            twiddles.append(dict(step=int(step),mantissa=mantissa,exponent=exponent,wpi=wpi))
    destination=ROOT/"tests/fixtures/potential_fft.json"
    destination.write_text(json.dumps(dict(reference="Original ASITIC machine-code FFT at 0x080912c0, independently matched to unmodified C++ FFT; reflected grids use explicit sufficient scratch storage. Retained wpr/wpi observed from a separate C++ copy, with identical complete FFT output verified.",original_executable_sha256=ORIGINAL_SHA256,original_probe_source=original_probe.read_text(),reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),source_sha256=hashlib.sha256((native/"src/potential_tables.cpp").read_bytes()).hexdigest(),probe=SOURCE,compile_flags=flags,twiddles=twiddles,cases=configs),separators=(",",":"),allow_nan=False)+"\n")
    constants=ROOT/"src/reasitic/fft_constants.py"
    lines=['"""Native potential FFT wpr (exact retained value) and binary64 wpi.',
           '', 'Generated by tools/capture_potential_fft.py from the original FSIN recurrence.',
           'Tuples are signed significand, binary exponent, binary64 sine.', '"""','TWIDDLES = {']
    for t in twiddles:
        word=int(t["exponent"],16);mantissa=int(t["mantissa"],16)*(-1 if word&0x8000 else 1)
        power=(word&0x7fff)-16383-63
        lines.append(f'    {t["step"]}: ({mantissa}, {power}, float.fromhex("{t["wpi"]}")),')
    constants.write_text("\n".join(lines+["}",""]))
    print(destination,len(configs))


if __name__=="__main__":main()

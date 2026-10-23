"""Probe the reference's unmodified 32-bit eddy Green and complex objects."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "asitic/green.hpp"
extern "C" int printf(const char*,...);
extern "C" double atof(const char*);
extern "C" int probe_main(int,char** argv) {
    const double k=atof(argv[1]),f=atof(argv[2]),height=atof(argv[6]),separation=atof(argv[7]);
    const asitic::GreenLayers layers{atof(argv[3]),atof(argv[4]),atof(argv[5])};
    const auto a=asitic::green_propagation_constant(k,f,layers.layer1),
               b=asitic::green_propagation_constant(k,f,layers.layer2),
               t=asitic::green_complex_tanh({double(layers.depth*a.real),double(layers.depth*a.imag)});
    printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n",
        a.real,a.imag,b.real,b.imag,t.real,t.imag,
        double(asitic::green_reflection_imag(k,f,layers.layer1)),
        double(asitic::green_oscillating_integrand(k,f,layers)),
        double(asitic::green_propagation_integrand(f,layers)),
        double(asitic::green_oscillating_kernel(k,f,layers,height,separation)),
        double(asitic::green_reflection_kernel(k,height)));
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
    objects=[reference/f"recomp_cpp/build/{name}.o" for name in ("green","legacy_complex")]
    cases=[]
    configs=[(k,f,*layers,2.6e-6,separation) for k in (0,1e-6,1,1e3,1e5,1e7) for f in (1e6,1e9,20e9)
             for layers in ((100,100,1e-4),(100,1,5e-5),(1e-8,100,1e-5),(1e5,1e5,7e-4),(1e4,1e5,5e-5)) for separation in (0,5e-6)]
    configs.extend((k,1e6,1,100,1e-4,1,1e-4) for k in (88.72283905206834,88.72283905206835,88.72283905206837))
    configs.extend((k,0,100,1,5e-5,2.6e-6,5e-6) for k in (0,1,1e5))
    with tempfile.TemporaryDirectory(prefix="reasitic-green-reference-") as directory:
        source=Path(directory,"probe.cpp");source.write_text(SOURCE)
        binary=Path(directory,"probe")
        subprocess.run(["g++","-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-std=c++17","-I",str(reference/"recomp_cpp/include"),str(source),*map(str,objects),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        for config in configs:
            raw=subprocess.check_output([str(binary),*map(str,config)],text=True).split()
            values=[float(v) if math.isfinite(float(v)) else "nan" if math.isnan(float(v)) else v for v in raw]
            k,f,l1,l2,depth,height,separation=config
            cases.append(dict(k=k,frequency=f,layer1=l1,layer2=l2,depth=depth,height=height,separation=separation,
                              gamma_first=values[:2],gamma_second=values[2:4],tanh=values[4:6],reflection_imag=values[6],
                              oscillating_integrand=values[7],propagation_integrand=values[8],oscillating_kernel=values[9],reflection_kernel=values[10]))
    output=ROOT/"tests/fixtures/green.json"
    output.write_text(json.dumps(dict(reference="Direct probes of unmodified C++ Green and legacy complex objects",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),object_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in objects},probe=SOURCE,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":
    main()

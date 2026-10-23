"""Capture retained cosh/tanh from the actual original executable."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_SHA256="72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f"
LEGACY_SHA256="bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    original=args.reference.resolve()/"run/asitic.linux.2.2"
    legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    rng=random.Random(521)
    coshes=[0.,-0.,1e-300,-1e-300,.1,-.1,500.,500.0000001,-710.,-800.]
    coshes.extend(rng.uniform(-710,500) for _ in range(10000))
    tanhs=[[0.,1.,0.],[.01,100.,99.9999999999],[1.,0.,0.],[1.,-0.,0.]]
    tanhs.extend([rng.uniform(-1,1),rng.uniform(-100,100),rng.uniform(-100,100)] for _ in range(10000))
    probe=ROOT/"tools/original_potential_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-potential-math-") as directory:
        binary=Path(directory)/"probe"
        subprocess.run(["g++",*flags,str(probe),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        def run(mode,values):
            result=subprocess.run([str(binary),str(original),str(legacy),str(mode),*map(str,values)],capture_output=True,text=True,start_new_session=True)
            if result.returncode:raise RuntimeError(f"Original scalar probe exited {result.returncode}: {result.stderr[:500]}")
            return [list(map(float,line.split())) for line in result.stdout.splitlines()]
        cosh_values=run(0,coshes);tanh_values=run(1,[v for row in tanhs for v in row])
    def number(value):
        return value if math.isfinite(value) else "Infinity" if value>0 else "-Infinity" if value<0 else "NaN"
    fixture=dict(reference="Original clipped cosh at 0x0809123c and tanh through transfer-up at 0x0808f004 with last=0; intact original legacy-complex DSO imports.",
                 original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,probe_source=probe.read_text(),compile_flags=flags,
                 cosh=[[x,number(row[0])] for x,row in zip(coshes,cosh_values)],tanh=[[x,number(row[0])] for x,row in zip(tanhs,tanh_values)])
    output=ROOT/"tests/fixtures/potential_math.json"
    output.write_text(json.dumps(fixture,separators=(",",":"),allow_nan=False)+"\n")
    print(output,len(cosh_values)+len(tanh_values),"original-binary cases")


if __name__=="__main__":main()

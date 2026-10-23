"""Capture the original CAP driver's intact coefficient-initialization loop."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]

def number(v):return v if math.isfinite(v) else "nan" if math.isnan(v) else "inf" if v>0 else "-inf"

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();original=args.reference.resolve()/"run/asitic.linux.2.2";legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum {path}")
    rng=random.Random(8052);cases=[]
    for frequency in (0.,-0.,1e-310,1e-100,1e6,1e9,5e9,20e9,1e100,1e300,-1e9,math.inf,math.nan):
        for records in ([[1e5,11.9],[1e16,3.9]],[[1e-300,1e-300],[1e300,1e300]],[[0.,0.],[math.inf,3.9]],[[math.nan,1.],[1.,math.nan]]):
            cases.append(dict(frequency=number(frequency),records=[[number(v) for v in r] for r in records]))
    for n in (1,2,3,5,12,256):
        for i in range(6):
            cases.append(dict(frequency=10**rng.uniform(-200,200),records=[[10**rng.uniform(-200,200),10**rng.uniform(-20,20)] for _ in range(n)]))
    source=ROOT/"tools/original_coefficients_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    components=0
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-coefficients-") as directory:
        work=Path(directory);probe=work/"probe";payload=work/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(probe)],check=True)
        for c in cases:
            n=len(c["records"]);values=[float(v) for row in c["records"] for v in row]
            payload.write_bytes(struct.pack("<Id",n,float(c["frequency"]))+struct.pack("<"+"d"*len(values),*values))
            run=subprocess.run([str(probe),str(original),str(legacy),str(payload)],capture_output=True,start_new_session=True,timeout=30)
            if run.returncode:raise RuntimeError(f"Original coefficient probe exited {run.returncode}: {run.stderr[:300]}")
            assert len(run.stdout)==16*n
            c["output"]=[number(v) for v in struct.unpack("<"+"d"*(2*n),run.stdout)];components+=2*n
    (ROOT/"tests/fixtures/layer_coefficients.json").write_text(json.dumps(dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference="Intact original CAP frequency-weight and coefficient loop, with empty-contact preparation and capture/exit at the following cache-load boundary. Inputs are already stored ohm-um resistivities; no numeric instructions or imports replaced.",probe_source=source.read_text(),compile_flags=flags,components=components,cases=cases),separators=(",",":"),allow_nan=False)+"\n")
    print(len(cases),"original coefficient groups",components,"output components")
if __name__=="__main__":main()

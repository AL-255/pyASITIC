"""Capture original transfer, spectral and complete table outputs without arithmetic substitutions."""
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

def num(v):return v if math.isfinite(v) else "nan" if math.isnan(v) else "inf" if v>0 else "-inf"
def tokens(values):return [num(v) for v in values]
def configuration(c):
    result=[1,c["nx"],c["ny"],len(c["metals"]),len(c["coefficients"]),c["source"],c["target"],c["width"],c["height"]]
    result.extend(v for m in c["metals"] for v in m)
    result.extend(float(v) for z in c["coefficients"] for v in z)
    result.extend(float(v) for v in c["depths"])
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();original=args.reference.resolve()/"run/asitic.linux.2.2";legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,sha in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError(f"Unexpected oracle checksum {path}")
    rng=random.Random(808350);scalar=[];tables=[]
    for nl in (1,2,3,5):
        for variant in range(6):
            c=dict(nx=2,ny=2,width=512.,height=320.,source=0,target=0,metals=[[0,95.,.5]],depths=[100.-i*3 for i in range(nl+1)])
            c["coefficients"]=[[1.+i*.4+rng.random(),rng.random()] for i in range(nl)]
            if variant==1:c["coefficients"]=[[v*1e-250 for v in z] for z in c["coefficients"]]
            if variant==2:c["coefficients"]=[[v*1e250 for v in z] for z in c["coefficients"]]
            if variant==3:c["coefficients"]=[[0.,-0.] for _ in range(nl)]
            if variant==4:c["coefficients"][0]=["nan",1.]
            if variant==5:c["depths"][0]="inf"
            c["requests"]=[]
            ks=[0.,-0.,1e-300,1e-8,.001,.1,1.,100.,-100.,1e300,"inf","nan"]
            for kind in range(6):
                for j,k in enumerate(ks):
                    source=-1 if kind==0 and j%3==0 else rng.randrange(nl)
                    target=rng.randrange(nl);sh=97.-source*3.+(j%5)*.25;th=97.-target*3.-(j%4)*.125
                    c["requests"].append([kind,source,target,nl-1,k,sh,th])
            scalar.append(c)
    for nx,ny in ((2,2),(4,8),(8,4),(8,8),(16,32),(32,16),(32,32),(64,64),(128,128),(256,256)):
        for source,target in ((0,0),(0,1),(1,0)):
            tables.append(dict(nx=nx,ny=ny,width=512.,height=320.,source=source,target=target,
                metals=[[1,48.7,.5],[1,47.6,.5],[0,700.,1.]],coefficients=[[10.,-6.6e-5],[.2124,-4.6e6]],depths=[750.,50.,0.]))
    tables.extend([
        dict(nx=8,ny=8,width=100.,height=120.,source=2,target=0,metals=[[0,97.,.5],[1,94.,.5],[2,91.,.7]],coefficients=[[1.,.1],[2.,.2],[3.,.3]],depths=[100.,97.,94.,0.]),
        dict(nx=8,ny=8,width=100.,height=120.,source=0,target=1,metals=[[0,97.,.5],[1,94.,.5]],coefficients=[[0.,-0.],[0.,0.]],depths=[100.,97.,0.]),
        dict(nx=8,ny=8,width=100.,height=120.,source=0,target=1,metals=[[0,97.,.5],[1,94.,.5]],coefficients=[["nan",0.],[2.,.2]],depths=[100.,97.,0.])])
    source=ROOT/"tools/original_spectral_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    components=0
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-spectral-") as directory:
        work=Path(directory);probe=work/"probe";input_path=work/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(probe)],check=True)
        for c in scalar+tables:
            config=configuration(c);requests=c.get("requests",[])
            raw=struct.pack("<"+"d"*len(config),*config);c["input_sha256"]=hashlib.sha256(raw).hexdigest()
            payload=struct.pack("<II",len(config),len(requests))+raw+b"".join(struct.pack("<7d",*(float(v) for v in r)) for r in requests)
            input_path.write_bytes(payload)
            run=subprocess.run([str(probe),str(original),str(legacy),str(input_path)],capture_output=True,start_new_session=True,timeout=120)
            if run.returncode:raise RuntimeError(f"Original spectral probe exited {run.returncode}: {run.stderr[:300]}")
            nl=len(c["coefficients"]);size=16*len(requests) if requests else 16*(2*c["nx"]+2*c["ny"]+max((c["nx"]+1)*(c["ny"]+1),c["nx"]*(c["nx"]+1)+c["ny"]+1))
            assert len(run.stdout)==size+8*(nl+1),(len(run.stdout),size)
            expected_depths=struct.pack("<"+"d"*(nl+1),*(float(v) for v in c["depths"]))
            assert run.stdout[size:]==expected_depths,"Native source helper did not restore depths"
            out=run.stdout[:size];values=struct.unpack("<"+"d"*(size//8),out);components+=len(values)
            if not requests and c["nx"]>=32 and all(math.isfinite(v) for v in values):c["output_sha256"]=hashlib.sha256(out).hexdigest()
            else:c["output"]=tokens(values)
    (ROOT/"tests/fixtures/spectral.json").write_text(json.dumps(dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference="Original numerical instructions and DSO; only allocation/deletion/status boundaries are replaced. Explicit zero backing including coefficient sentinels and rectangular table padding. Finite bits and nonfinite classifications; scalar source helpers must restore every depth byte.",probe_source=source.read_text(),compile_flags=flags,components=components,scalar=scalar,tables=tables),separators=(",",":"),allow_nan=False)+"\n")
    print(len(scalar),"scalar groups",sum(len(c["requests"]) for c in scalar),"regional/transfer calls",len(tables),"complete tables",components,"original output components")

if __name__=="__main__":main()

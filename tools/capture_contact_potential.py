"""Capture contact-potential matrices from intact original machine code."""
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
LEGACY_SHA256="bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34"


def table_values(case):
    nx,ny=case["nx"],case["ny"];seed=case["seed"]
    count=2*nx+2*ny+max((nx+1)*(ny+1),nx*(nx+1)+ny+1)
    def scaled(value,scale):return math.copysign(math.inf,value if value else 1) if scale=="inf" else value*scale
    return [complex(scaled((i*8191+seed*17)%65521-32760,case["scale"][0]),
                    scaled((i*257+seed*31)%4093-2046,case["scale"][1])) for i in range(count)]


def configuration(case,low,high):
    contacts,metals,coefficients=case["contacts"],case["metals"],case["coefficients"]
    values=[1,len(contacts),case["nx"],case["ny"],len(metals),len(coefficients),low,high,case["width"],case["height"],0,0,0,0,0,0]
    values.extend(v for c in contacts for v in c)
    values.extend(v for m in metals for v in m)
    values.extend(v for z in coefficients for v in z)
    values.extend(case["depths"])
    return values


def binary(values):return b"".join(struct.pack("<dd",z.real,z.imag) for z in values)
def number(value):return value if math.isfinite(value) else "nan" if math.isnan(value) else "inf" if value>0 else "-inf"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();original=args.reference.resolve()/"run/asitic.linux.2.2"
    legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    rng=random.Random(901);cases=[]
    for nx,ny in ((2,2),(4,4),(8,8),(16,8),(8,16),(32,32),(64,64),(128,128),(256,256)):
        for variant in range(4):
            normal=variant==0
            metals=[[1,48.7,.5],[1,47.6,.5],[0,700.,1.]] if normal else [[0,1.,0.],[0,1.,0.],[0,1.,0.]]
            contacts=[]
            for i in range(6):
                x0,x1=sorted(rng.sample(range(nx+1),2));y0,y1=sorted(rng.sample(range(ny+1),2))
                contacts.append([x0,x1,y0,y1,i%3])
            contacts[0][:4]=[0,nx,0,ny]
            cases.append(dict(nx=nx,ny=ny,width=512. if variant!=3 else 1.,height=320. if variant!=3 else 1.,
                metals=metals,coefficients=[[10.,-6.6e-5],[.2124,-4.6e6]] if normal else [[1.,0.]],depths=[750.,50.,0.] if normal else [1.,0.],
                contacts=contacts,seed=rng.randrange(10000),scale=([1e8,1e-3],[1e-40,1e-40],[-0.,-0.],[1e-320,1e-323])[variant]))
    for scale in ((1e40,1e40),("inf",1e-3)):
        cases.append(dict(nx=8,ny=8,width=100.,height=120.,metals=[[0,90.,.5]],coefficients=[[1.,.1]],depths=[100.,0.],
            contacts=[[0,1,0,1,0],[7,8,7,8,0],[0,8,0,8,0]],seed=901,scale=scale))
    cases.append(dict(nx=256,ny=2,width=512.,height=128.,metals=[[0,90.,.5]],coefficients=[[1.,.1]],depths=[100.,0.],
        contacts=[[i,i+1,0,1,0] for i in range(256)],seed=1901,scale=[1e8,1e-3],digest_only=True))
    cases.append(dict(nx=16,ny=32,width=100.,height=120.,metals=[[i%3,99.-i,.5+i*.1] for i in range(7)],
        coefficients=[[1.,.1],[2.,.2],[3.,.3]],depths=[100.,75.,50.,0.],
        contacts=[[0,1,0,1,0],[1,3,2,5,2],[7,9,4,8,6],[15,16,31,32,0],[0,16,0,32,2],[3,8,9,16,6]],seed=2901,scale=[1e8,1e-3]))
    cases.append(dict(nx=256,ny=256,width=512.,height=320.,metals=[[1,48.7,.5],[1,47.6,.5],[0,700.,1.]],
        coefficients=[[10.,-6.6e-5],[.2124,-4.6e6]],depths=[750.,50.,0.],
        contacts=[[i,i+1,0,1,i%3] for i in range(256)],seed=3901,scale=[1e8,1e-3],digest_only=True))
    source=ROOT/"tools/original_contact_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    components=0
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-contact-") as directory:
        work=Path(directory);probe=work/"probe";input_path=work/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(probe)],check=True)
        for case in cases:
            n=len(case["contacts"]);output=[[None]*n for _ in range(n)];case["pairs"]=[]
            metals=sorted({c[4] for c in case["contacts"]})
            for i,low in enumerate(metals):
                for high in metals[i:]:
                    pair=dict(low=low,high=high,seed=case["seed"]+17*low+31*high)
                    table=binary(table_values(dict(case,seed=pair["seed"])));config=configuration(case,low,high)
                    payload=struct.pack("<II",len(config),len(table)//16)+struct.pack("<"+"d"*len(config),*config)+table
                    input_path.write_bytes(payload);pair["input_sha256"]=hashlib.sha256(table).hexdigest();case["pairs"].append(pair)
                    run=subprocess.run([str(probe),str(original),str(legacy),str(input_path)],capture_output=True,text=True,start_new_session=True,timeout=60)
                    if run.returncode:raise RuntimeError(f"Original contact probe exited {run.returncode}: {run.stderr[:300]}")
                    for line in run.stdout.splitlines():
                        a,b,re,im=line.split();output[int(a)][int(b)]=complex(float(re),float(im));components+=2
            if any(z is None for row in output for z in row):raise AssertionError("Unfilled native contact matrix")
            if case.get("digest_only"):
                case["output_sha256"]=hashlib.sha256(binary(z for row in output for z in row)).hexdigest()
            else:case["output"]=[[[number(z.real),number(z.imag)] for z in row] for row in output]
    destination=ROOT/"tests/fixtures/contact_potential.json"
    destination.write_text(json.dumps(dict(reference="Original contact-potential routine 0x080901c0, intact legacy-complex DSO, explicit sufficient rectangular table backing. Finite output bits and nonfinite classifications; table input digests guard the deterministic recipe.",original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,probe_source=source.read_text(),compile_flags=flags,table_recipe="table_values in tools/capture_contact_potential.py",components=components,cases=cases),separators=(",",":"),allow_nan=False)+"\n")
    print(destination,len(cases),"cases",components,"original components")


if __name__=="__main__":main()

"""Capture intact original filament construction, including all edge branches."""
import argparse,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]


def configurations():
    rng=random.Random(6597);rows=[]
    for i in range(1024):
        points=[[rng.uniform(-150,150) for _ in range(3)] for _ in range(4)]
        if i%2==0:
            x,y=rng.uniform(10,100),rng.uniform(10,100);length,width=rng.uniform(1,100),rng.uniform(.1,10)
            points=[[x,y,3],[x+length,y,3],[x,y+width,3],[x+length,y+width,3]]
        else:width=rng.uniform(.1,10)
        nx,ny,nz=rng.randint(1,7),rng.randint(3,11),rng.randint(1,5)
        xi,yi,zi=rng.randrange(nx),rng.randrange(ny),rng.randrange(nz)
        prefix=[v for point in points for v in point]+[width,rng.uniform(.03,2),rng.uniform(.1,2),rng.uniform(-10,10),rng.uniform(-10,10)]
        for cell in (100.,width/(ny*2)):
            rows.append(prefix+[cell,ny,xi,yi,zi,nx,ny,nz,i%3])
    for scale in (1e-250,1e-100,1.,1e100,1e250):
        for ny in (3,5,9):
            for yi in range(ny):
                for edge in (False,True):
                    p=[2.,3.,.2,12.,3.,.2,2.,5.,.2,12.,5.,.2,2.,.5,.5,1.,-2.]
                    p=[v*scale for v in p]
                    rows.append(p+[scale*(.1 if edge else 100),ny,0,yi,0,1,ny,3,0])
    for sign in (0.,-0.):
        rows.append([sign]*12+[1.,.5,.5,sign,sign,100.,9,0,0,0,1,1,1,0])
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    reference=parser.parse_args().reference.resolve();original=reference/"run/asitic.linux.2.2";legacy=reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,sha in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError(f"Unexpected original checksum {path}")
    source=ROOT/"tools/original_filament_probe.cpp";rows=configurations()
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-filaments-") as directory:
        root=Path(directory);binary=root/"probe";payload=root/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        payload.write_bytes(struct.pack("<I",len(rows))+b"".join(struct.pack("<26d",*row) for row in rows))
        result=subprocess.run([str(binary),str(original),str(legacy),str(payload)],capture_output=True,start_new_session=True,timeout=60)
        if result.returncode or len(result.stdout)!=len(rows)*72:raise RuntimeError(f"Original filament probe failed {result.returncode}: {result.stderr[:300]}")
    cases=[dict(input=row,output_bits=[result.stdout[offset:offset+8].hex() for offset in range(i*72,(i+1)*72,8)]) for i,row in enumerate(rows)]
    output=ROOT/"tests/fixtures/filaments.json"
    output.write_text(json.dumps(dict(reference="Intact original build_filament at 0x0806597c; only mesh globals, metal thickness and input records supplied",original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,probe_source=source.read_text(),compile_flags=flags,cases=cases),separators=(",",":"),allow_nan=False)+"\n")
    print(len(cases),"original filament records captured",len(cases)*9,"output components")


if __name__=="__main__":main()

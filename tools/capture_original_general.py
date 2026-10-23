"""Capture general factors, n-workspace inverses and solves from original code."""
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


def generated_matrix(n,kind):
    if kind=="diagonal":return [[complex(2+i*.01,.5) if i==j else 0j for j in range(n)] for i in range(n)]
    return [[complex(3+i*.01,2) if j==(i+13)%n else complex(.01/(i+j+1),.02/(abs(i-j)+1)) for j in range(n)] for i in range(n)]


def right_sides(n):
    return [[complex(i==r,0) for i in range(n)] for r in (0,n-1)]+[[complex((i%7-3)*.125,(i%11-5)*.0625) for i in range(n)]]


def digest(matrix):return hashlib.sha256(b"".join(struct.pack("<dd",z.real,z.imag) for row in matrix for z in row)).hexdigest()
def number(v):return v if math.isfinite(v) else "nan" if math.isnan(v) else "inf" if v>0 else "-inf"
def pairs(matrix):return [[[number(z.real),number(z.imag)] for z in row] for row in matrix]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();original=args.reference.resolve()/"run/asitic.linux.2.2";legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    matrices=[[[3+0j,2j],[2+2j,4+1j]],[[0j]],[[1+0j,2+0j,1+0j],[0j,0j,3+0j],[0j,0j,0j]],
              [[complex(-0.,-0.),1+0j],[2+0j,complex(0.,-0.)]],[[complex(1e-300,0),0j],[0j,complex(2e-300,1e-300)]]]
    rng=random.Random(94094)
    for n in (1,2,3,4,8,17):
        for scale in (1.,1e-250,1e250):
            matrices.append([[complex((rng.randrange(2001)-1000)*scale,(rng.randrange(2001)-1000)*scale) for j in range(n)] for i in range(n)])
    matrices.extend([[[complex(math.nan,0),1+0j],[0j,1+0j]],[[complex(math.inf,0),1+0j],[1+0j,1+0j]]])
    cases=[dict(matrix=pairs(a),stride=len(a)+2) for a in matrices]
    cases.extend(dict(n=n,kind=kind,stride=n+2) for n,kind in ((32,"rotated"),(64,"rotated"),(65,"rotated"),(128,"rotated"),(129,"rotated"),(256,"rotated"),(514,"diagonal"),(514,"rotated")))
    source=ROOT/"tools/original_general_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    components=0
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-general-") as directory:
        work=Path(directory);probe=work/"probe";input_path=work/"matrix.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(probe)],check=True)
        for case in cases:
            a=[[complex(float(z[0]),float(z[1])) for z in row] for row in case["matrix"]] if "matrix" in case else generated_matrix(case["n"],case["kind"])
            n=len(a);stride=case["stride"];rhs=right_sides(n)
            packed=[z for j in range(n) for z in [*(a[i][j] for i in range(n)),*([complex(1e120,-1e120)]*(stride-n))]]
            input_path.write_bytes(b"".join(struct.pack("<dd",z.real,z.imag) for z in packed+[z for row in rhs for z in row]))
            run=subprocess.run([str(probe),str(original),str(legacy),str(n),str(stride),str(input_path)],capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode:raise RuntimeError(f"Original general probe exited {run.returncode}: {run.stderr[:300]}")
            record={}
            for line in run.stdout.splitlines():
                key,*values=line.split()
                if key in ("S","R","T","G"):record[key]=int(values[0])
                elif key=="P":record[key]=[int(v)-1 for v in values]
                else:
                    values=list(map(float,values));zs=[complex(values[i],values[i+1]) for i in range(0,len(values),2)]
                    record[key]=[zs[i:i+n] for i in range(0,len(zs),n)];components+=len(values)
            if record["G"]!=1:raise AssertionError("Original padding changed")
            case.update({key:record[key] for key in ("S","R","T","P","G") if key in record})
            case["input_sha256"]=digest(a)
            for key in ("F","I","B","V"):
                if key in record:
                    if "matrix" in case:case[key]=pairs(record[key])
                    else:case[key+"_sha256"]=digest(record[key])
    (ROOT/"tests/fixtures/general.json").write_text(json.dumps(dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference="Intact original ZGETRF/ZGETRI/ZGETRS with n-entry inverse workspace, three right-hand sides, network matrix-vector products and stride canaries. Finite bits and nonfinite classifications; full digests for large finite cases.",probe_source=source.read_text(),compile_flags=flags,components=components,cases=cases),separators=(",",":"),allow_nan=False)+"\n")
    print(len(cases),"original general matrix cases",components,"output components")


if __name__=="__main__":main()

"""Verify symmetric fixtures and capture large systems from original instructions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_SHA256="72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f"
LEGACY_SHA256="bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34"


def generated_matrix(n,kind):
    matrix=[]
    for i in range(n):
        row=[]
        for j in range(n):
            if i==j:z=complex(3+i*.01,2) if kind=="dominant" else complex(.001*(i+1),.003)
            elif kind=="paired" and j==(i^1):z=complex(1,.2)
            else:z=complex(.01/(i+j+1),.02/(abs(i-j)+1))
            row.append(z)
        matrix.append(row)
    return matrix


def upper_digest(matrix):
    return hashlib.sha256(b"".join(struct.pack("<dd",matrix[i][j].real,matrix[i][j].imag)
                                for i in range(len(matrix)) for j in range(i,len(matrix)))).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    original=args.reference.resolve()/"run/asitic.linux.2.2"
    legacy=args.reference.resolve()/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    source=ROOT/"tools/original_symmetric_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    fixture=json.loads((ROOT/"tests/fixtures/symmetric.json").read_text())
    components=0
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-symmetric-") as directory:
        work=Path(directory);binary=work/"probe";input_path=work/"matrix.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        def run(matrix,stride):
            n=len(matrix)
            input_path.write_bytes(b"".join(struct.pack("<dd",z.real,z.imag)
                for j in range(n) for z in [*(matrix[i][j] for i in range(n)),*([complex(1e120,-1e120)]*(stride-n))]))
            result=subprocess.run([str(binary),str(original),str(legacy),str(n),str(stride),str(input_path)],
                                  capture_output=True,text=True,start_new_session=True,timeout=60)
            if result.returncode:raise RuntimeError(f"Original matrix probe exited {result.returncode}: {result.stderr[:500]}")
            record={}
            for line in result.stdout.splitlines():
                key,*values=line.split()
                if key in ("S","T","G"):record[key]=int(values[0])
                elif key=="P":record[key]=list(map(int,values))
                else:
                    numbers=list(map(float,values));pairs=[complex(*numbers[i:i+2]) for i in range(0,len(numbers),2)]
                    record[key]=[pairs[i:i+n] for i in range(0,len(pairs),n)]
            if record["G"]!=1:raise AssertionError("Original matrix padding changed")
            return record
        for case in fixture["cases"]:
            matrix=[[complex(*z) for z in row] for row in case["matrix"]]
            record=run(matrix,case["stride"])
            for key in ("S","T","P"):
                if key in case and record[key]!=case[key]:raise AssertionError(f"Original {key} differs")
            for key in ("F","I"):
                if key not in case:continue
                for row,expected in zip(record[key],case[key]):
                    for value,target in zip(row,expected):
                        for actual,token in zip((value.real,value.imag),target):
                            reference=float(token);components+=1
                            if math.isnan(reference):
                                if not math.isnan(actual):raise AssertionError("Original NaN classification differs")
                            elif struct.pack("<d",actual)!=struct.pack("<d",reference):raise AssertionError("Original matrix component bits differ")
            case["original_padding_untouched"]=True
        large=[]
        for n,kind in ((128,"dominant"),(256,"dominant"),(256,"paired")):
            matrix=generated_matrix(n,kind);record=run(matrix,n+2)
            if record["S"] or record["T"]:raise AssertionError("Unexpected singular large reference")
            if kind=="paired" and not any(v<0 for v in record["P"]):raise AssertionError("Large fixture did not exercise two-entry pivots")
            large.append(dict(n=n,kind=kind,stride=n+2,input_sha256=upper_digest(matrix),P=record["P"],
                              factor_sha256=upper_digest(record["F"]),inverse_sha256=upper_digest(record["I"]),padding_untouched=True))
    fixture["original_verification"]=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,
        probe_source=source.read_text(),compile_flags=flags,cases=len(fixture["cases"]),components=components,
        reference="Direct original ZSYTF2/ZSYTRI instructions; equivalent to the native n-cell workspace unblocked path. Legacy DSO numerical imports are intact. Eigen-only fixtures retain the separately identified C++ reference.")
    (ROOT/"tests/fixtures/symmetric.json").write_text(json.dumps(fixture,indent=2,allow_nan=False)+"\n")
    output=ROOT/"tests/fixtures/symmetric_large.json"
    output.write_text(json.dumps(dict(reference=fixture["original_verification"],recipe="generated_matrix in tools/capture_original_symmetric.py; SHA256 of row-wise upper-triangle little-endian binary64 real/imag components.",cases=large),indent=2)+"\n")
    print(f"Verified {len(fixture['cases'])} cases / {components} original component bits; captured {len(large)} large full-triangle digests")


if __name__=="__main__":main()

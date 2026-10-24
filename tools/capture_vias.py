"""Capture bounded via stamps directly from the checksum-pinned ASITIC binary."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def cases():
    rng=random.Random(6578)
    rows=[]
    for _ in range(1024):
        lo=rng.uniform(-100,100)
        rows.append([10**rng.uniform(3,13),lo,lo+10**rng.uniform(-8,3),10**rng.uniform(-5,2),
                     10**rng.uniform(-7,3),rng.randint(1,100),rng.randint(1,100),
                     rng.uniform(-1e5,1e5),rng.uniform(-1e5,1e5)])
    threshold=float.fromhex("0x1.b7cdfd9d7bdbbp-34")
    for height,counts,frequency in itertools.product(
            [0.,-0.,-1.,math.nextafter(threshold,0.),threshold,math.nextafter(threshold,math.inf),1e-8,1.,100.],
            [(1,1),(1,9),(9,1),(17,23),(65535,65535),(-1,-1),(-1,1),(0,1),(1,0),(0,0)], [0.,1e9]):
        rows.append([frequency,0.,height,.8,.137,*counts,-0.,-0.])
    # Addition at a binary64 halfway value and resistance/imaginary cancellation.
    for z in [0.,-0.,1e-300,-1e-300,1e-16,-1e-16,1.,-1.,1e100,-1e100]:
        rows.append([1e9,3.5,4.5,.8,.137,3,7,z,z])
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    reference=parser.parse_args().reference.resolve()
    original=reference/"run/asitic.linux.2.2"
    legacy=reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    source=ROOT/"tools/original_via_probe.cpp";rows=cases()
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-vias-") as directory:
        work=Path(directory);binary=work/"probe";payload=work/"input.bin"
        subprocess.run(["g++",*flags,"-I",str(reference/"recomp_cpp/include"),str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        payload.write_bytes(struct.pack("<I",len(rows))+b"".join(struct.pack("<9d",*row) for row in rows))
        run=subprocess.run([str(binary),str(original),str(legacy),str(payload)],capture_output=True,start_new_session=True,timeout=120)
        if run.returncode or len(run.stdout)!=4+20*len(rows):raise RuntimeError(f"Original probe failed {run.returncode}, {len(run.stdout)} bytes: {run.stderr[:300]}")
    before,after=struct.unpack_from("<H",run.stdout)[0],struct.unpack_from("<H",run.stdout,len(run.stdout)-2)[0]
    if before!=after or before&0xf00!=0x300:raise RuntimeError("Unexpected native x87 control word")
    records=[]
    for i,row in enumerate(rows):
        raw=run.stdout[2+20*i:2+20*(i+1)]
        if struct.unpack_from("<I",raw)[0]!=1:raise RuntimeError("Original via stamp failed")
        records.append(dict(input=row,output_bits=[raw[4:12].hex(),raw[12:20].hex()]))
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,
                 reference="Intact original add_via_impedance at 0x080657b8. Allocation/release and warnings are runtime boundaries; no numerical code or constants are replaced. Matrix padding and descriptor bytes are checked on every call.",
                 control_word_before=before,control_word_after=after,probe_source=source.read_text(),compile_flags=flags,cases=records)
    (ROOT/"tests/fixtures/vias_original.json").write_text(json.dumps(fixture,separators=(",",":"),allow_nan=False)+"\n")
    print(f"Captured {len(records)} direct-original via stamps / {2*len(records)} components")


if __name__=="__main__":main()

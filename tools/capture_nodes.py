"""Capture complete folded-node boundaries from intact original instructions."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import zlib
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]


def generated(n,asymmetric=False):
    cap=[[complex(.0002*(i+1),.001*(i+1)) if i==j else complex(.000001,.00001)/(abs(i-j)+1) for j in range(n)] for i in range(n)]
    ind=[[complex(2+i*.1,-3) if i==j else complex(.01,.03)/(abs(i-j)+1) for j in range(n)] for i in range(n)]
    if asymmetric:
        for i in range(n):
            for j in range(i):ind[i][j]*=1.125
    return cap,ind


def packed(matrices):
    return b"".join(struct.pack("<dd",matrix[i][j].real,matrix[i][j].imag)
                    for matrix in matrices for j in range(len(matrix)) for i in range(len(matrix)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--library-path",help="i386 runtime library search path for original CLI snapshots")
    parser.add_argument("--gdb",default="gdb")
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/"run/asitic.linux.2.2";legacy=reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path,expected in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"Unexpected oracle checksum: {path}")
    sessions_path=ROOT/"tests/fixtures/transformer_network.json"
    sessions=json.loads(sessions_path.read_text())
    source=ROOT/"tools/original_transformer_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    records=[]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-nodes-") as directory:
        work=Path(directory);binary=work/"probe";payload=work/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        def capture(label,n,raw,target=None,**metadata):
            payload.write_bytes(struct.pack("<IId",1,n,1e9)+raw)
            run=subprocess.run([str(binary),str(original),str(legacy),str(payload)],capture_output=True,start_new_session=True,timeout=120)
            if run.returncode or len(run.stdout)!=4+16*n*n+31*8:raise RuntimeError(f"Original node probe failed {label}: {run.returncode}, {run.stderr[:300]}")
            if struct.unpack_from("<I",run.stdout)[0]!=1:raise RuntimeError(f"Original node solve failed {label}")
            folded=run.stdout[4:4+16*n*n];ports=run.stdout[4+16*n*n:4+16*n*n+64]
            bits=[ports[i:i+8].hex() for i in range(0,64,8)]
            if target is not None and bits!=target:raise AssertionError(f"Original session/probe Y mismatch: {label}")
            records.append(dict(label=label,n=n,input_zlib_base64=base64.b64encode(zlib.compress(raw,9)).decode(),
                                input_sha256=hashlib.sha256(raw).hexdigest(),cap_sha256=hashlib.sha256(folded).hexdigest(),Y=bits,**metadata))
            print(f"Captured {label}: {n} nodes",flush=True)
        for index,c in enumerate(sessions["rules"]):
            if "capacitance" not in c:continue
            matrices=[[[complex(*z) for z in row] for row in c[key]] for key in ("capacitance","inductance")]
            target=[struct.pack("<d",float(v)).hex() for v in c["Y"]]
            capture(f"existing rule {index}",len(matrices[0]),packed(matrices),target,rule_index=index)
        for n in (2,3,7,128,256):
            capture(f"asymmetric {n}",n,packed(generated(n,True)))
        rng=random.Random(8053)
        for trial in range(24):
            n=rng.choice([1,2,3,5,9,17]);cap,ind=generated(n,True)
            scale=10**rng.uniform(-80,80)
            for matrix in (cap,ind):
                for i in range(n):
                    for j in range(n):matrix[i][j]*=scale*rng.uniform(.75,1.25)
            capture(f"scaled {trial}",n,packed((cap,ind)))
        library_path=args.library_path or os.environ.get("LD_LIBRARY_PATH") or str(reference/"run/libs")
        for index,c in enumerate(sessions["cases"]):
            if c["nonfinite_model"]:continue
            session=work/str(index);session.mkdir()
            for filename,value in (("process.tek",c["technology"]),("input.asit",c["script"]),("answers.txt",c["stdin"])):
                (session/filename).write_text(value)
            commands=f'''set pagination off
set confirm off
set environment LD_LIBRARY_PATH {library_path}
set environment TERM dumb
set environment INPUTRC /dev/null
break *0x08053e00
run -g -t process.tek -x input.asit < answers.txt
python
import gdb,struct
stack=bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('$esp'))+4,12))
cap,ind,n=struct.unpack('<3I',stack)
assert 1<=n<=256
open('node-input.raw','wb').write(bytes(gdb.selected_inferior().read_memory(cap,n*n*16))+bytes(gdb.selected_inferior().read_memory(ind,n*n*16)))
open('node-size.txt','w').write(str(n))
end
kill
quit
'''
            (session/"capture.gdb").write_text(commands)
            run=subprocess.run([args.gdb,"-q","-batch","-x","capture.gdb",str(original)],cwd=session,capture_output=True,text=True,start_new_session=True,timeout=120)
            if run.returncode or not (session/"node-input.raw").exists():raise RuntimeError(f"Original session snapshot failed {index}: {run.stdout[-1000:]} {run.stderr[-1000:]}")
            capture(f"complete session {index}",int((session/"node-size.txt").read_text()),(session/"node-input.raw").read_bytes(),c["raw_output_bits"][:8],session_index=index)
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,
                 reference="Intact original folded-node driver 0x08053e00, including native LU/backsolve, matrix-vector products and legacy-complex divisions. Allocation/release and status boundaries only. Production CAP/inductive inputs are captured at original CLI entry under GDB and independently replayed; Y bits must also equal the complete original sessions.",
                 session_fixture_sha256=hashlib.sha256(sessions_path.read_bytes()).hexdigest(),probe_source=source.read_text(),compile_flags=flags,cases=records)
    (ROOT/"tests/fixtures/nodes_original.json").write_text(json.dumps(fixture,separators=(",",":"),allow_nan=False)+"\n")
    print(f"Captured {len(records)} original complete folded-node boundaries",flush=True)


if __name__=="__main__":main()

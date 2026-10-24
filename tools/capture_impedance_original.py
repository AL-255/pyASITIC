"""Observe original filament records and complete upper impedance assembly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import struct
from capture_original_symmetric import ORIGINAL_SHA256, LEGACY_SHA256

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = r'''
set pagination off
set confirm off
set environment TERM dumb
set environment INPUTRC /dev/null
python
import gdb,struct,json,base64,zlib
fill=0x80650d4;build=0x806597c
gdb.Breakpoint('*'+hex(fill),internal=True)
build_bp=gdb.Breakpoint('*'+hex(build),internal=True)
end
run -g -t process.tek -x input.asit < answers.txt
python
def memory(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u32(a):return struct.unpack('<I',memory(a,4))[0]
def i32(a):return struct.unpack('<i',memory(a,4))[0]
def f64(a):return struct.unpack('<d',memory(a,8))[0]
assert int(gdb.parse_and_eval('$pc'))==fill
control_before=int(gdb.parse_and_eval('$fctrl'))
esp=int(gdb.parse_and_eval('$esp'));finish=u32(esp);descriptor=u32(esp+4);ctx=u32(esp+8)
data=u32(descriptor);n=i32(descriptor+12);stride=i32(descriptor+20)
assert 1<=n<=256 and stride>=n
segments=[u32(u32(ctx+4)+4*i)for i in range(i32(ctx+32))]
width=[i32(u32(ctx+24)+4*i)for i in range(len(segments))]
thickness=[i32(u32(ctx+28)+4*i)for i in range(len(segments))]
base=[];total=0
for a,b in zip(width,thickness):base.append(total);total+=a*b
assert n==total
frequency=f64(ctx+8);metals=u32(0x80d8910)
records=[None]*n;pending={}
gdb.Breakpoint('*'+hex(finish),temporary=True,internal=True)
gdb.execute('continue',to_string=True)
while int(gdb.parse_and_eval('$pc'))!=finish:
 pc=int(gdb.parse_and_eval('$pc'))
 if pc==build:
  esp=int(gdb.parse_and_eval('$esp'));segment=u32(esp+4);target=u32(esp+8);args=[i32(esp+16+4*i)for i in range(6)]
  index=segments.index(segment);row=base[index]+args[1]*thickness[index]+args[2]
  ret=u32(esp)
  assert ret not in pending
  pending[ret]=(target,row,index,args);gdb.Breakpoint('*'+hex(ret),temporary=True,internal=True)
 else:
  target,row,index,args=pending.pop(pc)
  raw=memory(target,68);metal=i32(target+64)
  record=dict(wire_bits=raw[:64].hex(),metal=metal,sheet_resistance=f64(metals+236*metal+0xb8),thickness_count=thickness[index],input=dict(segment=memory(segments[index],0xf0).hex(),indices=args))
  if records[row] is not None:assert records[row]['wire_bits']==record['wire_bits']
  records[row]=record
  if all(c is not None for c in records):build_bp.enabled=False
 gdb.execute('continue',to_string=True)
assert not pending and all(c is not None for c in records)
upper=b''.join(memory(data+(j*stride+i)*16,16)for j in range(n)for i in range(j+1))
result=dict(n=n,frequency=frequency,records=records,upper_bits=upper.hex(),control_before=control_before,control_after=int(gdb.parse_and_eval('$fctrl')))
open('assembly.json','w').write(json.dumps(result))
end
kill
quit
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--library-path", required=True)
    args = parser.parse_args()
    original = args.reference / "run/asitic.linux.2.2"
    legacy = args.reference / "run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for path, sha in ((original, ORIGINAL_SHA256), (legacy, LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected oracle checksum: {path}")
    records = []
    jobs = []
    for name in ("network", "network_eddy"):
        cases = json.loads((ROOT / f"tests/fixtures/{name}.json").read_text())["cases"]
        jobs.extend((name, i, c) for i, c in enumerate(cases))
    for name in ("transformer_network",):
        cases = json.loads((ROOT / f"tests/fixtures/{name}.json").read_text())["cases"]
        jobs.extend((name, i, cases[i]) for i in (4, 5, 8, 11, 16))
    polygon=json.loads((ROOT/'tests/fixtures/network.json').read_text())['cases'][3]
    for cell in (20,10):
        refined=dict(polygon,script=polygon['script'].replace('CELL 1000 1000 1000',f'CELL {cell} 1000 1000',1),mesh=dict(polygon['mesh'],length_cell=cell))
        jobs.append(('network',3,refined))
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-assembly-") as directory:
        for ordinal,(name, index, c) in enumerate(jobs):
            work = Path(directory) / f"{ordinal}-{name}-{index}"
            work.mkdir()
            for filename, text in (("process.tek", c["technology"]), ("input.asit", c["script"]), ("answers.txt", c.get("stdin", "quit\n")), ("capture.gdb", COMMANDS)):
                (work / filename).write_text(text)
            run = subprocess.run(["gdb", "-q", "-batch", "-x", "capture.gdb", str(original.resolve())], cwd=work, env=dict(os.environ, LD_LIBRARY_PATH=args.library_path), capture_output=True, text=True, start_new_session=True, timeout=120)
            if run.returncode or not (work / "assembly.json").exists():
                raise RuntimeError(f"Original assembly capture failed {name}/{index}: {run.stdout[-1500:]} {run.stderr[-1000:]}")
            item = json.loads((work / "assembly.json").read_text())
            if item["control_before"] != 0x37f or item["control_after"] != 0x37f:
                raise RuntimeError("Unexpected original control word")
            item.update(fixture=name, index=index)
            if 'mesh' in c:item['mesh']=c['mesh']
            records.append(item)
            print(name, index, item["n"], "filaments / original upper matrix captured", flush=True)
    result = dict(original_sha256=ORIGINAL_SHA256, legacy_sha256=LEGACY_SHA256, reference="Actual original CLI fill_filament_impedance entry/actual return 0x080650d4, with unmodified filament builder 0x0806597c returns. Geometry, sheet resistance, thickness counts and full defined upper impedance entries are observed without numerical/runtime replacements. Filament observation stops after every unique mesh input has been recorded. Undefined lower triangle is excluded.", gdb_commands=COMMANDS, cases=records)
    # Independently execute the same original pair routine at the observed
    # filament inputs. These unscaled terms isolate assembly from geometry and
    # are test inputs only; production still computes/caches its own pairs.
    source = ROOT / "tools/original_mutual_probe.cpp"
    flags = ["-m32", "-O2", "-mfpmath=sse", "-msse2", "-fno-pie", "-fno-pic", "-fno-stack-protector", "-fno-exceptions", "-fno-rtti", "-nostdlib", "-no-pie", "-Wl,-Ttext-segment=0x10000000"]
    pairs = []
    for c in records:
        c["pair_start"] = len(pairs)
        wires = [struct.unpack('<8d', bytes.fromhex(r["wire_bits"])) for r in c["records"]]
        pairs.extend((*a, *wires[j], 0.) for i, a in enumerate(wires) for j in range(i + 1, len(wires)))
    with tempfile.TemporaryDirectory(prefix="pyasitic-assembly-mutual-") as directory:
        work = Path(directory);binary = work / "probe";payload = work / "input.bin"
        subprocess.run(["g++", *flags, str(source), "/lib/i386-linux-gnu/libc.so.6", "-Wl,--dynamic-linker=/lib/ld-linux.so.2", "-o", str(binary)], check=True)
        payload.write_bytes(struct.pack('<I', len(pairs)) + b''.join(struct.pack('<I17d', 4, *p) for p in pairs))
        run = subprocess.run([str(binary), str(original.resolve()), str(legacy.resolve()), str(payload)], capture_output=True, start_new_session=True, timeout=120)
        if run.returncode or len(run.stdout) != 4 + 26 * len(pairs):raise RuntimeError("Original unscaled pair probe failed")
        for c in records:
            count = c["n"] * (c["n"] - 1) // 2;start = c.pop("pair_start")
            c["mutual_bits"] = [run.stdout[2 + 26 * i + 4:2 + 26 * i + 12].hex() for i in range(start, start + count)]
    result["pair_probe_source"] = source.read_text();result["pair_probe_flags"] = flags
    (ROOT / "tests/fixtures/impedance_original.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

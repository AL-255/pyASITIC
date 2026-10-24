"""Capture the unchanged original exponent instruction sequence at full range."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.retained_scalar import Real as R,_exponent


def inputs():
    values=[R(v)for v in(0.,-0.,1.,-1.,math.inf,-math.inf,math.nan,710.,-745.,11400.,-11400.)]
    for power in(-16445,-16444,-16400,-1000,-64,-63,-1,0):
        for sign in(-1,1):values.append(R(sign*Fraction(2)**power))
    log2e=R(Fraction(0xb8aa3b295c17f0bc,1<<63))
    for n in(-16448,-16447,-16446,-16445,-16383,-16382,-1024,-1,0,1,1024,16382,16383,16384,16385):
        for half in(-.5,0.,.5):
            center=(R(n)+R(half))/log2e
            quantum=Fraction(2)**max(_exponent(abs(center.value))-63,-16445)if center.value else Fraction(2)**-16445
            for delta in(-1,0,1):values.append(R._result(center.value+delta*quantum))
    rng=random.Random(90495)
    values.extend(R(rng.uniform(-1000,1000))for _ in range(256))
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    original=reference/'run/asitic.linux.2.2';legacy=reference/'run/libs/libstdc++-2-libc6.1-1-2.9.0.so'
    for path,want in((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError(f'Unexpected oracle checksum: {path}')
    source=ROOT/'tools/original_green_probe.cpp'
    flags=['-m32','-O2','-mfpmath=sse','-msse2','-ffp-contract=off','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie','-Wl,-Ttext-segment=0x10000000']
    values=inputs()
    payload=struct.pack('<I',len(values))+b''.join(struct.pack('<I8d',14,*(-v).words(),0,0,0,0,0)for v in values)
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-exp-')as directory:
        work=Path(directory);binary=work/'probe';input_path=work/'input.bin';input_path.write_bytes(payload)
        subprocess.run(['g++',*flags,str(source),'/lib/i386-linux-gnu/libc.so.6','-Wl,--dynamic-linker=/lib/ld-linux.so.2','-o',str(binary)],check=True)
        result=subprocess.run([str(binary),str(original),str(legacy),str(input_path)],capture_output=True,start_new_session=True,timeout=120)
        if result.returncode or len(result.stdout)!=4+26*len(values):raise RuntimeError(f'Original exponent probe failed: {result.returncode}, {result.stderr[:500]}')
    before,after=struct.unpack_from('<H',result.stdout)[0],struct.unpack_from('<H',result.stdout,len(result.stdout)-2)[0]
    if before!=after or before!=0x37f:raise RuntimeError(f'Unexpected x87 control word: {before:#x}/{after:#x}')
    cases=[]
    for i,value in enumerate(values):
        raw=result.stdout[2+26*i:2+26*(i+1)]
        cases.append(dict(input_words=list(value.words()),output_bits=raw[:8].hex(),extended_bits=raw[16:].hex()))
    cpu={}
    for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
        key,separator,value=line.partition(':')
        if separator and key.strip()in('vendor_id','cpu family','model','model name','stepping'):cpu[key.strip()]=value.strip()
    fixture=dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,compile_flags=flags,
                 reference='Separate instruction audit: original bytes 0x080949b8–0x080949d5 execute FLDL2E/FRNDINT/F2XM1/FSCALE with a supplied saved 80-bit operand and original stack frame. FCHS consumes the negated input. No FP instruction is replaced. This bypasses the caller cutoff and is not a complete Green-function session.',
                 probe_source=source.read_text(),cpu=cpu,input_sha256=hashlib.sha256(payload).hexdigest(),cases=cases)
    (ROOT/'tests/fixtures/exp_original.json').write_text(json.dumps(fixture,separators=(',',':'))+'\n')
    print(f'Captured {len(cases)} original exponent instruction returns')


if __name__=='__main__':main()

"""Capture the checksum-identified i386 libm used by original ASITIC sessions."""
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
SOURCE=r'''
extern "C" int open(const char*,int,...),read(int,void*,unsigned),write(int,const void*,unsigned),close(int);
extern "C" double sin(double),cos(double),original_pow(double,double);
asm(".symver original_pow,pow@GLIBC_2.0");
extern "C" int probe_main(int,char** argv){
 int fd=open(argv[1],0);if(fd<0)return 1;unsigned count;if(read(fd,&count,4)!=4)return 2;
 unsigned short before;asm volatile("fnstcw %0":"=m"(before));write(1,&before,2);
 for(unsigned i=0;i<count;i++){
  unsigned mode;double x;if(read(fd,&mode,4)!=4||read(fd,&x,8)!=8)return 3;
  volatile double result=mode==0?cos(x):mode==1?sin(x):original_pow(x,1.5);double value=result;write(1,&value,8);
 }
 unsigned short after;asm volatile("fnstcw %0":"=m"(after));write(1,&after,2);close(fd);return 0;
}
asm(".text\n.global _start\n_start:\n"
 "xorl %ebp,%ebp\npopl %esi\nmovl %esp,%ecx\nandl $-16,%esp\n"
 "pushl %eax\npushl %esp\npushl %edx\npushl $0\npushl $0\npushl %ecx\npushl %esi\npushl $probe_main\n"
 "call __libc_start_main\nhlt\n");
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libm",type=Path,default=Path("/usr/lib/i386-linux-gnu/libm.so.6"))
    args=parser.parse_args();library=args.libm.resolve();sha=hashlib.sha256(library.read_bytes()).hexdigest()
    parent=json.loads((ROOT/"tests/fixtures/eddy_original.json").read_text())
    observed={v for c in parent["cases"] for v in c["libm_sha256"].values()}
    if observed!={sha}:raise ValueError("Library differs from actual original-session libm captures")
    rng=random.Random(23953);values=[0.,-0.,math.inf,-math.inf,math.nan,1e-320,-1e-320]
    for n in range(-128,129):
        x=n*math.pi/2;values.extend([math.nextafter(x,-math.inf),x,math.nextafter(x,math.inf)])
    values.extend(rng.uniform(-100,100) for _ in range(512))
    values.extend(math.ldexp(rng.uniform(.5,1),rng.randint(-1073,1024))*rng.choice([-1,1]) for _ in range(1024))
    for high in (0x3e400000,0x3e500000,0x3feb6000,0x400368fd,0x419921fb):
        x=struct.unpack('<d',struct.pack('<II',0,high))[0];values.extend([math.nextafter(x,0),x,math.nextafter(x,math.inf)])
    rows=[dict(operation=operation,input=value) for operation in (0,1) for value in values]
    power=[0.,-0.,1e-320,-1.,math.inf,-math.inf,math.nan,*[math.nextafter(1.,direction) for direction in (0,math.inf)]]
    power.extend(10**rng.uniform(-300,300) for _ in range(2048))
    rows.extend(dict(operation=2,input=value) for value in power)
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-ffp-contract=off","-fno-builtin","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-imported-math-") as directory:
        work=Path(directory);source=work/"probe.cpp";binary=work/"probe";payload=work/"input.bin";source.write_text(SOURCE)
        subprocess.run(["g++",*flags,str(source),str(library),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        payload.write_bytes(struct.pack('<I',len(rows))+b''.join(struct.pack('<Id',c['operation'],c['input']) for c in rows))
        run=subprocess.run([str(binary),str(payload)],capture_output=True,start_new_session=True,timeout=120)
        if run.returncode or len(run.stdout)!=4+8*len(rows):raise RuntimeError("Imported math probe failed")
    before,after=struct.unpack_from('<H',run.stdout)[0],struct.unpack_from('<H',run.stdout,len(run.stdout)-2)[0]
    if before!=after or before&0xf00!=0x300:raise RuntimeError("Imported math changed the x87 control word")
    for i,c in enumerate(rows):
        value=c['input'];c['input']=value if math.isfinite(value) else 'nan' if math.isnan(value) else 'inf' if value>0 else '-inf'
        c['output_bits']=run.stdout[2+8*i:10+8*i].hex()
    cpu={}
    if Path('/proc/cpuinfo').exists():
        for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
            key,separator,value=line.partition(':')
            if separator and key.strip() in ('vendor_id','cpu family','model','model name','stepping','microcode'):cpu[key.strip()]=value.strip()
    result=dict(reference="Native i386 libm calls at ASITIC's original GLIBC_2.0 symbol versions, not ASITIC numerical entry points. The library checksum is independently required to equal every actual-original-session libm mapping in eddy_original.json. pow is explicitly version-bound because the default GLIBC_2.29 entry uses a different algorithm.",libm_sha256=sha,native_instruction_cpu=cpu,control_before=before,control_after=after,probe_source=SOURCE,compile_flags=flags,cases=rows)
    (ROOT/"tests/fixtures/imported_math.json").write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(len(rows),'native imported sin/cos/pow fixtures captured')


if __name__=="__main__":main()

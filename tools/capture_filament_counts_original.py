"""Original count rounding, MAXNW clamp, forced counts and signed overflow stores."""
import argparse,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256
ROOT=Path(__file__).resolve().parents[1]


def cases():
    for cap in(1,2,3,9,10,99,500,65536,2147483647,0,-1):
        for width in(0.,-1.,1.,9.,20.,500.,2**31-1.,2**31-.5,2**31,1e300,math.inf,-math.inf,math.nan):
            for flags in((0,0),(-1,-1),(-1,0)):
                yield [width,1.,1.,.5,cap,*flags]
    for cell in(.1,.01,.3,1e-10,7/3,math.pi):
        for n in range(65):
            value=(n+.5)*cell
            for w in(math.nextafter(value,-math.inf),value,math.nextafter(value,math.inf)):
                yield [w,w,cell,cell,500,0,0]
    for cell in(0.,-1.,1e-300,math.inf,math.nan):yield [20.,1.,cell,cell,500,0,0]
    rng=random.Random(0x8064f6c)
    for _ in range(512):yield [10**rng.uniform(-250,250),10**rng.uniform(-250,250),10**rng.uniform(-250,250),10**rng.uniform(-250,250),rng.choice([9,500,2147483647]),0,0]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);a=p.parse_args();original=a.reference.resolve()/'run/asitic.linux.2.2'
    if hashlib.sha256(original.read_bytes()).hexdigest()!=ORIGINAL_SHA256:raise ValueError('Unexpected original checksum')
    rows=list(cases());source=ROOT/'tools/original_filament_counts_probe.cpp';flags=['-m32','-O2','-mfpmath=sse','-msse2','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie','-Wl,-Ttext-segment=0x10000000']
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-counts-')as d:
        work=Path(d);binary=work/'probe';payload=work/'input.bin';subprocess.run(['g++',*flags,str(source),'/lib/i386-linux-gnu/libc.so.6','-Wl,--dynamic-linker=/lib/ld-linux.so.2','-o',str(binary)],check=True)
        payload.write_bytes(struct.pack('<I',len(rows))+b''.join(struct.pack('<7d',*r)for r in rows));run=subprocess.run([str(binary),str(original),str(payload)],capture_output=True,start_new_session=True,timeout=60)
        if run.returncode or len(run.stdout)!=4+20*len(rows):raise RuntimeError(f'Original count probe {run.returncode}: '+run.stderr.decode()[:1000])
    before,after=struct.unpack('<H',run.stdout[:2])[0],struct.unpack('<H',run.stdout[-2:])[0];assert before==after==0x37f
    result=dict(original_sha256=ORIGINAL_SHA256,probe_source=source.read_text(),compile_flags=flags,control_before=before,control_after=after,reference='Intact original set_filament_counts at 0x08064f6c, supplied segment/settings records. Only nonnumerical allocation/status boundaries replaced; numerical instructions/constants unchanged. Actual width/thickness/total integer stores, AL status and ownership flags retained. Separate from complete original CLI histories.',cases=[dict(input_bits=struct.pack('<7d',*r).hex(),output=list(struct.unpack('<5i',run.stdout[2+20*i:2+20*(i+1)])))for i,r in enumerate(rows)])
    (ROOT/'tests/fixtures/filament_counts_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');print(len(rows),'original count records captured')


if __name__=='__main__':main()

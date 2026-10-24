"""Capture intact original geometry reductions on threshold/extreme input records."""
import argparse,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256
ROOT=Path(__file__).resolve().parents[1]


def cases():
    yield dict(label='empty',records=[])
    threshold=1e-10
    for length in(0.,-0.,1e-300,1e-11,math.nextafter(threshold,0.),threshold,math.nextafter(threshold,math.inf),1e-9,-1e-9,1e100,1e300):
        for width in(0.,-0.,1.23456789012345,-1.23456789012345,1e-300,1e300):
            yield dict(label=f'threshold/{length.hex()}/{width.hex()}',records=[[0.,0.,0.,length,0.,0.,width]])
    rng=random.Random(0x804ee74)
    for i in range(320):
        rows=[]
        for j in range(rng.choice([1,2,7,31,64])):
            scale=10**rng.uniform(-250,250);row=[rng.uniform(-10,10)*scale for _ in range(6)]+[rng.uniform(-10,10)*10**rng.uniform(-250,250)]
            rows.append(row)
        yield dict(label=f'finite/{i}',records=rows)
    for value in(math.inf,-math.inf,math.nan):
        for k in range(7):
            row=[0.,0.,0.,40.,30.,20.,5.];row[k]=value
            yield dict(label=f'nonfinite/{value}/{k}',records=[row])
    for word in(0x7ff0000000001234,0xfff0000000002345,0x7ff8000000012345,0xfff8000000045678,0x7ff0000000000001,0xfff8000000000000):
        value=struct.unpack('<d',struct.pack('<Q',word))[0]
        for k in(0,6):
            row=[0.,0.,0.,40.,30.,20.,5.];row[k]=value
            yield dict(label=f'nan-payload/{word:016x}/{k}',records=[row])
    for value in(math.inf,-math.inf):
        yield dict(label=f'invalid-zero-times/{value}',records=[[0.,0.,0.,0.,0.,0.,value]])
        for k in range(3):
            row=[0.,0.,0.,40.,30.,20.,5.];row[k]=row[k+3]=value
            yield dict(label=f'invalid-subtraction/{value}/{k}',records=[row])
    for sign in(1.,-1.):yield dict(label=f'invalid-sum/{sign}',records=[[0.,0.,0.,40.,30.,20.,sign*math.inf],[0.,0.,0.,40.,30.,20.,-sign*math.inf]])
    nan_words=(0x7ff0000000001234,0xfff0000000002345,0x7ff8000000012345,0xfff8000000045678,0x7ff0000000000001,0xfff8000000000000)
    for a in nan_words:
        for b in nan_words:
            x,y=(struct.unpack('<d',struct.pack('<Q',w))[0]for w in(a,b))
            for first,second in((0,3),(3,6),(0,6)):
                row=[0.,0.,0.,40.,30.,20.,5.];row[first]=x;row[second]=y
                yield dict(label=f'nan-pair/{a:016x}/{b:016x}/{first}/{second}',records=[row])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);args=parser.parse_args();original=args.reference.resolve()/'run/asitic.linux.2.2'
    if hashlib.sha256(original.read_bytes()).hexdigest()!=ORIGINAL_SHA256:raise ValueError('Unexpected original checksum')
    records=list(cases());source=ROOT/'tools/original_geometry_metrics_probe.cpp';flags=['-m32','-O2','-mfpmath=sse','-msse2','-fno-pie','-fno-pic','-fno-stack-protector','-fno-exceptions','-fno-rtti','-nostdlib','-no-pie','-Wl,-Ttext-segment=0x10000000']
    with tempfile.TemporaryDirectory(prefix='pyasitic-original-geometry-primitives-')as d:
        work=Path(d);binary=work/'probe';payload=work/'input.bin'
        subprocess.run(['g++',*flags,str(source),'/lib/i386-linux-gnu/libc.so.6','-Wl,--dynamic-linker=/lib/ld-linux.so.2','-o',str(binary)],check=True)
        payload.write_bytes(struct.pack('<I',len(records))+b''.join(struct.pack('<I',len(c['records']))+b''.join(struct.pack('<7d',*r)for r in c['records'])for c in records))
        run=subprocess.run([str(binary),str(original),str(payload)],capture_output=True,start_new_session=True,timeout=60)
        if run.returncode or len(run.stdout)!=4+34*len(records):raise RuntimeError(f'Original geometry probe {run.returncode}: '+run.stderr.decode()[:1000])
    before=struct.unpack('<H',run.stdout[:2])[0];after=struct.unpack('<H',run.stdout[-2:])[0];assert before==after==0x37f
    output=[]
    for i,c in enumerate(records):
        data=run.stdout[2+34*i:2+34*(i+1)];output.append(dict(label=c['label'],records=[struct.pack('<7d',*r).hex()for r in c['records']],length_bits=data[:8].hex(),area_bits=data[8:16].hex(),metal_area_bits=data[16:24].hex(),metal_area_extended_bits=data[24:34].hex()))
    result=dict(original_sha256=ORIGINAL_SHA256,probe_source=source.read_text(),compile_flags=flags,control_before=before,control_after=after,reference='Intact original GEOM 0x0804c620 and METALAREA 0x0804ee74 on supplied primary records. Only nonnumerical sprintf/status boundaries are replaced; the format observer copies actual original variadic GEOM stores. No numerical instruction/constant or runtime numerical import is replaced. Separate from complete CLI creator histories. Raw nonfinite words remain recorded; payload/exception equivalence is unproven.',cases=output)
    (ROOT/'tests/fixtures/geometry_primitives_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');print(len(output),'original geometry primitive records captured')


if __name__=='__main__':main()

"""Direct original mutual primitives plus explicitly separate native x87 probes."""
import argparse,copy,hashlib,json,math,random,struct,subprocess,tempfile
import sys
from pathlib import Path
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]


def production_pairs():
    sys.path.insert(0,str(ROOT/"src"))
    from reasitic import Technology
    from reasitic.bridge import _shape
    from reasitic.solver import discretize,filament_counts
    from reasitic.filament import record,filament_records
    from reasitic.network import _join_for_pads
    sessions=json.loads((ROOT/"tests/fixtures/transformer_network.json").read_text())["cases"]
    result=[]
    for index in (0,4,16,10,17):
        c=sessions[index];tech=Technology.from_text(c["technology"]);mesh=c["mesh"]
        shapes=[_shape(c[key],tech) for key in ("first","second")]
        ground=_shape(c["ground"],tech) if c["ground"] else None
        if ground:
            for shape in shapes:
                if shape.name==ground.name:
                    for segment in shape.segments:segment.nx=segment.ny=-1
        a,b=[discretize(shape,mesh["capacitance_length_cell"],mesh["length_cell"]) for shape in shapes]
        b.segments.reverse();joined=_join_for_pads(a,b);records=[]
        for segment in joined.segments:
            if segment.metal>=len(tech.metals):continue
            ny,nz=filament_counts(segment,mesh["width_cell"],mesh["thickness_cell"])
            for yi in range(ny):
                for zi in range(nz):records.append(record(segment,joined.origin,yi,zi,ny,nz,mesh["width_cell"],9,tech))
        wires=filament_records(records)
        for i,first in enumerate(wires):
            for j in range(i+1,len(wires)):
                result.append(dict(mode=4,input=[*first[:8],*wires[j][:8]],production_pair=dict(coupled_case=index,row=i,column=j)))
    return result


def number(value):return value if math.isfinite(value) else "nan" if math.isnan(value) else "inf" if value>0 else "-inf"


def cases():
    result=[dict(mode=c["mode"],input=c["input"]) for c in json.loads((ROOT/"tests/fixtures/parallel.json").read_text())["cases"]]
    rng=random.Random(62230)
    for _ in range(256):
        length,radius=10**rng.uniform(-12,3),10**rng.uniform(-12,1)
        result.append(dict(mode=0,input=[length,radius]))
        result.append(dict(mode=1,input=[rng.uniform(-1,1)*radius,rng.uniform(-1,1)*radius]))
        widths=[10**rng.uniform(-8,-2) for _ in range(4)]
        result.append(dict(mode=2,input=[*widths,rng.uniform(0,4)*max(widths),rng.uniform(0,4)*max(widths)]))
        length=10**rng.uniform(-4,1);low=rng.uniform(-2,2)*length;high=low+rng.uniform(.1,2)*length;y=rng.uniform(0,2)*length
        result.append(dict(mode=3,input=[0.,0.,0.,length,0.,0.,.1*length,.02*length,low,y,0.,high,y,0.,.12*length,.03*length,rng.choice([0.,.02*length])]))
    for i in range(256):
        a=[rng.uniform(-100,100) for _ in range(6)]+[rng.uniform(.1,10),rng.uniform(.1,2)]
        b=[rng.uniform(-100,100) for _ in range(6)]+[rng.uniform(.1,10),rng.uniform(.1,2)]
        if i%2==0:a[2]=a[5]=3.;b[2]=b[5]=3. if i%4==0 else 5.
        result.append(dict(mode=4,input=[*a,*b]))
    for value in (0.,-0.,1e-320,1e-250,1e250,math.inf,-math.inf,math.nan,-1.,1.,2.,4.,math.nextafter(1.,0.),math.nextafter(1.,2.),11356.,-11400.):
        for operation in (5,6,7):result.append(dict(mode=operation,input=[value,1.,0.]))
    for _ in range(512):
        a=2**rng.uniform(-600,600);b=2**rng.uniform(-600,600)
        result.append(dict(mode=5,input=[a,b,1.]))
        result.append(dict(mode=6,input=[a*rng.choice([-1,1]),b,1.]))
        result.append(dict(mode=7,input=[rng.uniform(-1000,1000),rng.uniform(.5,2),1.]))
    for _ in range(256):
        result.append(dict(mode=8,input=[rng.uniform(-1,1),rng.uniform(-1,1),0.]))
        for mode in (9,10):result.append(dict(mode=mode,input=[rng.uniform(-math.pi,math.pi),1.,0.]))
        result.append(dict(mode=11,input=[rng.uniform(-.999999,.999999),1.,0.]))
    for y in (0.,-0.,1.,-1.,math.inf,-math.inf,math.nan):
        for x in (0.,-0.,1.,-1.,math.inf,-math.inf,math.nan):result.append(dict(mode=8,input=[y,x,0.]))
    for value in (0.,-0.,1e-250,-1e-250,math.pi/2,math.pi,-math.pi):
        for mode in (9,10):result.append(dict(mode=mode,input=[value,1.,0.]))
    for value in (0.,-0.,1e-310,-1e-310,1e-12,-1e-12,math.nextafter(1.,0.),1.,-1.,math.inf,-math.inf,math.nan):
        result.append(dict(mode=11,input=[value,1.,0.]))
    return result+production_pairs()


def capture(ref,rows):
    ref=ref.resolve();original=ref/"run/asitic.linux.2.2";legacy=ref/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"
    for p,sha in ((original,ORIGINAL_SHA256),(legacy,LEGACY_SHA256)):
        if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError(f"Unexpected oracle checksum {p}")
    source=ROOT/"tools/original_mutual_probe.cpp"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-mutual-") as directory:
        root=Path(directory);binary=root/"probe";payload=root/"input.bin"
        subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
        payload.write_bytes(struct.pack("<I",len(rows))+b"".join(struct.pack("<I",row["mode"])+struct.pack("<17d",*[float(v) for v in row["input"]],*([0.]*(17-len(row["input"])))) for row in rows))
        run=subprocess.run([str(binary),str(original),str(legacy),str(payload)],capture_output=True,start_new_session=True,timeout=120)
        if run.returncode or len(run.stdout)!=4+len(rows)*26:raise RuntimeError(f"Original probe failed {run.returncode}, {len(run.stdout)} bytes: {run.stderr[:300]}")
    before=struct.unpack_from("<H",run.stdout)[0];after=struct.unpack_from("<H",run.stdout,len(run.stdout)-2)[0]
    if before!=after or before&0xf00!=0x300:raise RuntimeError(f"Unexpected native x87 control word {before:#x} / {after:#x}")
    for i,row in enumerate(rows):
        raw=run.stdout[2+26*i:2+26*(i+1)];row["input"]=[number(v) for v in row["input"]]
        row.update(status=struct.unpack_from("<i",raw)[0],output_bits=raw[4:12].hex(),extended_bits=raw[12:22].hex(),warnings=struct.unpack_from("<I",raw,22)[0])
    cpu={}
    if Path("/proc/cpuinfo").is_file():
        for line in Path("/proc/cpuinfo").read_text().split("\n\n",1)[0].splitlines():
            key,separator,value=line.partition(":")
            if separator and key.strip() in ("vendor_id","cpu family","model","model name","stepping"):cpu[key.strip()]=value.strip()
    return dict(original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,reference="Modes 0-4 execute intact original self/cross-section/separation/parallel/segment routines. Modes 5-11 separately execute matching native x87 elementary instructions in the probe; these are instruction oracles, not calls into the original binary.",native_instruction_environment=dict(cpu=cpu,control_word_before=before,control_word_after=after),probe_source=source.read_text(),compile_flags=flags,cases=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    result=capture(parser.parse_args().reference,cases())
    (ROOT/"tests/fixtures/mutual_original.json").write_text(json.dumps(result,separators=(",",":"),allow_nan=False)+"\n")
    print(len(result["cases"]),"original/instruction cases captured")


if __name__=="__main__":main()

"""Capture CALCTRANS models, nodes and complete commands from the original binary."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
from capture_network import port_matrix
from capture_potential import read_matrix
from capture_original_symmetric import ORIGINAL_SHA256,LEGACY_SHA256
ROOT=Path(__file__).resolve().parents[1]
TAP=r'''
extern "C" int strncmp(const char*,const char*,unsigned);
extern "C" int vsprintf(char*,const char*,__builtin_va_list);
extern "C" void* fopen(const char*,const char*);
extern "C" int fprintf(void*,const char*,...);
extern "C" int fclose(void*);
extern "C" int sprintf(char* output,const char* format,...) {
 __builtin_va_list args;__builtin_va_start(args,format);
 if(!strncmp(format,"L1=",3)) {
  __builtin_va_list copy;__builtin_va_copy(copy,args);void* file=fopen("transformer-values.out","a");
  for(int i=0;i<7;++i)fprintf(file,"%.17g ",__builtin_va_arg(copy,double));
  fprintf(file,"\n");fclose(file);__builtin_va_end(copy);
 }
 int result=vsprintf(output,format,args);__builtin_va_end(args);return result;
}
'''
def clean(v):
    v=float(v)
    return v if math.isfinite(v) else "nan" if math.isnan(v) else "inf" if v>0 else "-inf"
def matrix(m):return [[[clean(v) for v in z] for z in row] for row in m]
def pairs(m):return [[[z.real,z.imag] for z in row] for row in m]


def primitives(reference,root):
    source=ROOT/"tools/original_transformer_probe.cpp";binary=root/"probe";payload=root/"matrix.bin"
    flags=["-m32","-O2","-mfpmath=sse","-msse2","-fno-pie","-fno-pic","-fno-stack-protector","-fno-exceptions","-fno-rtti","-nostdlib","-no-pie","-Wl,-Ttext-segment=0x10000000"]
    subprocess.run(["g++",*flags,str(source),"/lib/i386-linux-gnu/libc.so.6","-Wl,--dynamic-linker=/lib/ld-linux.so.2","-o",str(binary)],check=True)
    rng=random.Random(523);rules=[]
    for scale in (1e-250,1e-100,1e-3,1,1e100,1e250):
        for _ in range(8):rules.append(dict(frequency_hz=1e9,input=[[rng.uniform(-2,2)*scale,rng.uniform(-2,2)*scale] for _ in range(4)]))
    rules.extend(dict(frequency_hz=f,input=y) for f,y in [(2e9,[[1,2],[99,35],[-.1,-.2],[2,4]]),(1e9,[[1,0],[0,1],[0,0],[-1,0]]),(1e9,[[0,0]]*4),(0.,[[1,2]]*4),(1e-300,[[1,2]]*4),(1e300,[[1,2]]*4),(1e9,[["inf",0],[1,0],[0,0],[1,0]]),(1e9,[["nan",0],[1,0],[0,0],[1,0]]),(1e9,[[1,-0.],[0,-0.],[-0.,-0.],[2,-0.]])])
    for n in (1,2,5,17,65):
        for terminated in (False,True):
            c=[[complex(.0002*(i+1),.001*(i+1)) if i==j else complex(.000001,.00001)/(abs(i-j)+1) for j in range(n)] for i in range(n)]
            ind=[[complex(2+i*.1,-3) if i==j else complex(.01,.03)/(abs(i-j)+1) for j in range(n)] for i in range(n)]
            if terminated:c[n//2][n//2]+=1e15
            rules.append(dict(frequency_hz=1e9,capacitance=pairs(c),inductance=pairs(ind)))
    for case in rules:
        mode=int("capacitance" in case);n=len(case["capacitance"]) if mode else 0
        values=([v for key in ("capacitance","inductance") for j in range(n) for i in range(n) for v in case[key][i][j]] if mode else [float(v) for z in case["input"] for v in z])
        payload.write_bytes(struct.pack("<IId",mode,n,case["frequency_hz"])+struct.pack("<"+"d"*len(values),*values))
        result=subprocess.run([str(binary),str(reference/"run/asitic.linux.2.2"),str(reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so"),str(payload)],capture_output=True,start_new_session=True,timeout=60)
        if result.returncode:raise RuntimeError(f"Original transformer probe exited {result.returncode}: {result.stderr[:300]}")
        assert len(result.stdout)==4+16*n*n+31*8
        case["success"]=struct.unpack_from("<I",result.stdout)[0];offset=4
        if mode:
            data=struct.unpack_from("<"+"d"*(2*n*n),result.stdout,offset);offset+=16*n*n
            case["C"]=[clean(data[2*(j*n+i)+k]) for i in range(n) for j in range(n) for k in (0,1)]
        for key,count in (("Y",8),("I",8),("M",7),("Z",8)):
            case[key]=list(map(clean,struct.unpack_from("<"+"d"*count,result.stdout,offset)));offset+=8*count
    return rules,flags


def sessions(reference,root,library_path):
    executable=reference/"run/asitic.linux.2.2";tap=root/"tap.cpp";tap.write_text(TAP)
    subprocess.run(["g++","-m32","-O2","-fPIC","-shared","-nostdlib","-fno-builtin",str(tap),"/lib/i386-linux-gnu/libc.so.6","-o",str(root/"tap.so")],check=True)
    configs=[]
    a=dict(kind="wire",parameters=dict(name="A",length=40,width=5,metal="M4",x=10,y=20))
    b=dict(kind="wire",parameters=dict(name="B",length=30,width=5,metal="M3",x=20,y=50))
    wires="WIRE NAME=A:LEN=40:WID=5:METAL=M4:XORG=10:YORG=20\nWIRE NAME=B:LEN=30:WID=5:METAL=M3:XORG=20:YORG=50\n"
    for termination in (0,1e-10,50,1e15):configs.append((a,b,wires,"quit\n",termination,False,False))
    # Refined unequal CAP/LMAT cells and a separately parsed ground.
    configs.append((a,b,wires,"quit\n",10,True,False))
    configs.append((a,b,wires,"quit\n",50,True,True))
    for kind,parameters,creation,answers in [
        ("transformer",dict(primary_name="A",secondary_name="B",length=80,height=70,width=3,spacing=2,turns=1.25,secondary_turns=1,metal="M4",exit_metal="M3",x=10,y=10),"TRANS PNAME=A:SNAME=B:LEN=80:WID=70:W=3:S=2:NP=1.25:NS=1:METAL=M4:EXIT=M3:XORG=10:YORG=10\n","quit\n"),
        ("balun",dict(name="T",length=80,width=3,secondary_width=4,spacing=2,turns=3,metal="M4",secondary_metal="M3",x=10,y=10),"BALUN NAME=T:LEN=80:W1=3:W2=4:S=2:N=3:METAL=M4:METAL2=M3:XORG=10:YORG=10\n","quit\n"),
        ("transformer3d",dict(primary_name="A",secondary_name="B",length=80,height=70,width=3,spacing=8,turns=1.25,metal="M4",secondary_metal="M3",x=10,y=10),"3DMIRRORTRANS\n","A\nB\n80 70\n3\n8\n1.25\nM4\nM3\n10 10\n0\n1\nquit\n"),
    ]:
        for termination,grounded,eddy in ((0,False,False),(50,True,False),(50,True,True)):
            configs.append((dict(kind=kind,parameters=parameters,winding=0),dict(kind=kind,parameters=parameters,winding=1),creation,answers,termination,grounded,eddy))
    configs=[(*c,"explicit_first" if not c[5] else "strip") for c in configs]+[(*configs[i],"default") for i in (0,6,9,12)]
    for i in (0,6):
        a,b,creation,answers,termination,grounded,eddy,mode=configs[i]
        configs.append((b,a,creation,answers,termination,grounded,eddy,"default"))
    cases=[]
    for index,(first,second,creation,answers,termination,grounded,eddy,reference_mode) in enumerate(configs):
        tech=(reference/"run/tek/CMOS.tek").read_text()
        for key,value in (("fftx",64),("ffty",64),("chipx",128),("chipy",128)):
            tech=re.sub(rf"(?im)^(\s*{key}\s*=\s*)[\d.]+",rf"\g<1>{value}",tech)
        fine=index in (4,5)
        mesh=dict(length_cell=20 if fine else 1000,width_cell=3 if fine else 1000,thickness_cell=.5 if fine else 1000,capacitance_length_cell=30 if fine else 1000,capacitance_width_cell=8 if fine else 1000)
        ground=dict(kind="wire",parameters=dict(name="G",length=110,width=8,metal="M1",x=5,y=115)) if grounded else first if reference_mode=="explicit_first" else None
        ground_creation="WIRE NAME=G:LEN=110:WID=8:METAL=M1:XORG=5:YORG=115\n" if grounded else ""
        if first["kind"]=="wire":names=(first["parameters"]["name"],second["parameters"]["name"])
        else:
            winding_names=("T-P","T-S") if first["kind"]=="balun" else ("A","B")
            names=(winding_names[first.get("winding",0)],winding_names[second.get("winding",1)])
        suffix="" if reference_mode=="default" else f" {'G' if grounded else names[0]} {termination}"
        script=f"CELL {mesh['length_cell']} {mesh['width_cell']} {mesh['thickness_cell']}\nCCELL {mesh['capacitance_length_cell']} {mesh['capacitance_width_cell']}\nEDDY {'ON' if eddy else 'OFF'}\nSAVEMAT TRUE\n{creation}{ground_creation}CALCTRANS {names[0]} {names[1]} 1{suffix}\n2PORTTRANS {names[0]} {names[1]} 1 1 1 Y RECT y.out{suffix}\n2PORTTRANS {names[0]} {names[1]} 1 1 1 S RECT s.out{suffix}\n"
        path=root/str(index);path.mkdir();(path/"process.tek").write_text(tech);(path/"input.asit").write_text(script)
        env=dict(os.environ,LD_PRELOAD=str(root/"tap.so"),LD_LIBRARY_PATH=library_path,TERM="dumb",INPUTRC="/dev/null")
        result=subprocess.run([str(executable),"-g","-t","process.tek","-x","input.asit"],input=answers,capture_output=True,text=True,cwd=path,timeout=120,start_new_session=True,env=env)
        if result.returncode or not (path/"transformer-values.out").is_file() or not (path/"y.out").is_file():raise RuntimeError(result.stdout+result.stderr)
        metrics=list(map(clean,(path/"transformer-values.out").read_text().splitlines()[0].split()))
        # The command parser stores numeric arguments in binary32 before the
        # backend receives them as doubles. Record its actual SI input.
        native_termination=struct.unpack("<f",struct.pack("<f",termination))[0]
        cases.append(dict(first=first,second=second,ground=ground,reference_mode=reference_mode,command_termination_ohm=termination,termination_ohm=native_termination,eddy=eddy,mesh=mesh,frequency_hz=1e9,technology=tech,metrics=metrics,nonfinite_model=all(isinstance(v,str) for v in metrics),
                          nodal_capacitance_matrix=matrix(read_matrix(path/"Ycap.out")),admittance_matrix=matrix(port_matrix(path/"y.out")),scattering_matrix=matrix(port_matrix(path/"s.out")),script=script,stdin=answers,stdout=result.stdout))
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True);parser.add_argument("--native-library-path",required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    for path,sha in ((reference/"run/asitic.linux.2.2",ORIGINAL_SHA256),(reference/"run/libs/libstdc++-2-libc6.1-1-2.9.0.so",LEGACY_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError(f"Unexpected oracle checksum {path}")
    with tempfile.TemporaryDirectory(prefix="pyasitic-original-transformer-") as directory:
        root=Path(directory);rules,flags=primitives(reference,root);cases=sessions(reference,root,args.native_library_path)
    (ROOT/"tests/fixtures/transformer_network.json").write_text(json.dumps(dict(reference="Intact original transformer inverse/model and folded-node routines; complete original CALCTRANS / 2PORTTRANS sessions. Scalar model output is tapped at sprintf without changing numerical instructions.",original_sha256=ORIGINAL_SHA256,legacy_sha256=LEGACY_SHA256,probe_source=(ROOT/"tools/original_transformer_probe.cpp").read_text(),compile_flags=flags,tap=TAP,rules=rules,cases=cases),separators=(",",":"),allow_nan=False)+"\n")
    print(len(rules),"direct original rules",len(cases),"complete original coupled sessions")

if __name__=="__main__":main()

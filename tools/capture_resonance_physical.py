"""Capture complete native SELFRES SLOW sessions with full-precision output taps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
TAP=r'''
extern "C" int strcmp(const char*,const char*);
extern "C" int vprintf(const char*,__builtin_va_list);
extern "C" int vsprintf(char*,const char*,__builtin_va_list);
extern "C" void* fopen(const char*,const char*);
extern "C" int fprintf(void*,const char*,...);
extern "C" int fclose(void*);
extern "C" int printf(const char* format,...) {
    __builtin_va_list args;__builtin_va_start(args,format);
    if(!strcmp(format,"\nf1=%5.2lf f2=%5.2lf f_g=%5.2lf Zin.i=%lf")) {
        __builtin_va_list copy;__builtin_va_copy(copy,args);
        double v[4];for(int i=0;i<4;++i)v[i]=__builtin_va_arg(copy,double);__builtin_va_end(copy);
        void* file=fopen("resonance-trace.out","a");fprintf(file,"P %.17g %.17g %.17g %.17g\n",v[0],v[1],v[2],v[3]);fclose(file);
    }
    int result=vprintf(format,args);__builtin_va_end(args);return result;
}
extern "C" int sprintf(char* output,const char* format,...) {
    __builtin_va_list args;__builtin_va_start(args,format);
    if(!strcmp(format,"Self Resonant Frequency Occurs at %5.2lf (GHz).")) {
        __builtin_va_list copy;__builtin_va_copy(copy,args);double v=__builtin_va_arg(copy,double);__builtin_va_end(copy);
        void* file=fopen("resonance-trace.out","a");fprintf(file,"R %.17g\n",v);fclose(file);
    }
    int result=vsprintf(output,format,args);__builtin_va_end(args);return result;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();executable=reference/"recomp_cpp/build/cli/asitic"
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-resonance-physical-") as directory:
        root=Path(directory);source=root/"tap.cpp";source.write_text(TAP);tap=root/"tap.so"
        subprocess.run(["g++","-m32","-O2","-fPIC","-shared","-nostdlib","-fno-builtin",str(source),"/lib/i386-linux-gnu/libc.so.6","-o",str(tap)],check=True)
        configs=[
            ("square","CMOS",dict(length=80,width=5,spacing=3,turns=1,metal="M1",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1:METAL=M1:EXIT=-1:XORG=10:YORG=20"),
            ("square","CMOS",dict(length=80,width=5,spacing=3,turns=2.5,metal="M4",x=10,y=10),"SQUARE NAME=A:LEN=80:W=5:S=3:N=2.5:METAL=M4:EXIT=-1:XORG=10:YORG=10"),
            ("polygon","CMOS",dict(radius=35,sides=6,width=5,spacing=3,turns=1.25,metal="M4",x=20,y=20),"SPIRAL NAME=A:RAD=35:SIDES=6:W=5:S=3:N=1.25:METAL=M4:XORG=20:YORG=20"),
            ("wire","BiCMOS",dict(length=40,width=5,metal="M2",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M2:XORG=10:YORG=20"),
            ("wire","CMOS",dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20"),
            ("capacitor","CMOS",dict(length=40,width=5,metal="M2",bottom_metal="M1",x=40,y=50),"CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1:XORG=40:YORG=50"),
        ]
        for index,(kind,process,parameters,creation) in enumerate(configs):
            technology=(reference/f"run/tek/{process}.tek").read_text()
            for key,value in (("fftx",32),("ffty",32),("chipx",128),("chipy",128)):
                technology=re.sub(rf"(?im)^(\s*{key}\s*=\s*)[\d.]+",rf"\g<1>{value}",technology)
            for differential in (False,True):
                ground_metal="M1" if process=="CMOS" else "M2"
                ground=dict(kind="wire",parameters=dict(name="G",length=100,width=5,metal=ground_metal,x=10,y=110))
                # Include the reverse-bound path and actual layered eddy binding.
                first,last=(100,1) if differential else (1,100)
                if kind=="wire" and process=="CMOS":
                    ground=None;first,last=.5,.6
                eddy=process=="BiCMOS" and differential
                mesh=dict(length_cell=20,width_cell=3,thickness_cell=.5,capacitance_length_cell=50,capacitance_width_cell=8) if index==0 and differential else dict(length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=1000)
                ground_creation=f"WIRE NAME=G:LEN=100:WID=5:METAL={ground_metal}:XORG=10:YORG=110\n" if ground else ""
                script=f"CELL {mesh['length_cell']} {mesh['width_cell']} {mesh['thickness_cell']}\nCCELL {mesh['capacitance_length_cell']} {mesh['capacitance_width_cell']}\nEDDY {'ON' if eddy else 'OFF'}\n{creation}\n{ground_creation}SELFRES A {first} {last} 0.1 {'D' if differential else 'S'} SLOW 1"+(" G" if ground else "")+"\n"
                path=root/f"case-{index}-{int(differential)}";path.mkdir();(path/"input.asit").write_text(script);(path/"process.tek").write_text(technology)
                environment={k:v for k,v in os.environ.items() if k not in ("LD_LIBRARY_PATH","LD_PRELOAD")};environment["LD_PRELOAD"]=str(tap)
                result=subprocess.run([str(executable),"-g","-t","process.tek","-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=path,timeout=120,start_new_session=True,env=environment)
                if result.returncode or not (path/"resonance-trace.out").is_file():raise RuntimeError(result.stdout+result.stderr)
                progress=[];frequency=None
                for line in (path/"resonance-trace.out").read_text().splitlines():
                    tag,*values=line.split()
                    if tag=="P":progress.append(list(map(float,values)))
                    elif tag=="R":frequency=float(values[0])
                def native_hz(value):return struct.unpack('f',struct.pack('f',value*1e9))[0]
                cases.append(dict(kind=kind,process=process,parameters=parameters,technology=technology,ground=ground,eddy=eddy,mesh=mesh,
                                  first_hz=native_hz(first),last_hz=native_hz(last),step_hz=native_hz(.1),
                                  differential=differential,frequency_ghz=frequency,progress=progress,script=script,stdout=result.stdout))
    output=ROOT/"tests/fixtures/resonance_physical.json"
    output.write_text(json.dumps(dict(reference="Unmodified native SELFRES SLOW command; printf/sprintf output taps retain full precision without altering numerical inputs or algorithms",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),tap=TAP,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases))


if __name__=="__main__":main()

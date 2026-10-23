"""Capture native PIX snapshots, precise model/ZIN reports and known 2PORTX exports."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_eddy import read_matrix as read_lmat
from capture_network import port_matrix

ROOT=Path(__file__).resolve().parents[1]
TAP=r'''
extern "C" int strcmp(const char*,const char*);
extern "C" int strncmp(const char*,const char*,unsigned);
extern "C" int vsprintf(char*,const char*,__builtin_va_list);
extern "C" int vfprintf(void*,const char*,__builtin_va_list);
extern "C" void* dlsym(void*,const char*);
extern "C" int fprintf(void*,const char*,...);
extern "C" int fclose(void*);
using Open=void*(*)(const char*,const char*);
Open real_open=nullptr;void* observed_file=nullptr;char observed_tag=0;
extern "C" void* fopen(const char* path,const char* mode) {
    if(!real_open)real_open=reinterpret_cast<Open>(dlsym(reinterpret_cast<void*>(-1),"fopen"));
    void* file=real_open(path,mode);observed_file=file;
    observed_tag=!strcmp(path,"YC.out")?'C':!strcmp(path,"Zbig.out")?'B':!strncmp(path,"current_",8)?'I':!strncmp(path,"voltages_",9)?'V':0;
    return file;
}
extern "C" int fprintf(void* file,const char* format,...) {
    __builtin_va_list args;__builtin_va_start(args,format);
    if(file==observed_file && observed_tag && !strcmp(format,"\n%10d %10d %20.10lg %20.10lg")) {
        __builtin_va_list copy;__builtin_va_copy(copy,args);int row=__builtin_va_arg(copy,int),column=__builtin_va_arg(copy,int);
        double real=__builtin_va_arg(copy,double),imag=__builtin_va_arg(copy,double);__builtin_va_end(copy);
        // Both RHS columns are inside the explicitly allocated native rhs(m,2)
        // backing array. Columns 3+ in the CLI's square-print tail are undefined.
        if(observed_tag=='C' || (observed_tag=='B'?row==column:column<=2)) {
            void* log=real_open("pix-vectors.out","a");fprintf(log,"%c %d %d %.17g %.17g\n",observed_tag,row,column,real,imag);fclose(log);
        }
    }
    int result=vfprintf(file,format,args);__builtin_va_end(args);return result;
}
extern "C" int sprintf(char* output,const char* format,...) {
    __builtin_va_list args;__builtin_va_start(args,format);int count=0;const char* tag="";
    if(!strncmp(format,"Pi Model at f=",14)) { count=4;tag="Q"; }
    else if(!strncmp(format,"L  =",4)) { count=7;tag="M"; }
    else if(!strcmp(format,"Zin = %5.3lf + j %5.3lf")) { count=2;tag="Z"; }
    if(count) {
        __builtin_va_list copy;__builtin_va_copy(copy,args);void* file=fopen("pix-values.out","a");fprintf(file,"%s ",tag);
        for(int i=0;i<count;++i)fprintf(file,"%.17g ",__builtin_va_arg(copy,double));
        fprintf(file,"\n");fclose(file);__builtin_va_end(copy);
    }
    int result=vsprintf(output,format,args);__builtin_va_end(args);return result;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();executable=reference/"recomp_cpp/build/cli/asitic"
    configs=[
        ("wire","CMOS",dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20",False,False,False),
        ("wire","CMOS",dict(length=40,width=5,metal="M4",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M4:XORG=10:YORG=20",True,False,True),
        ("square","CMOS",dict(length=80,width=5,spacing=3,turns=1,metal="M1",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1:METAL=M1:EXIT=-1:XORG=10:YORG=20",True,False,False),
        ("square","CMOS",dict(length=80,width=5,spacing=3,turns=1,metal="M1",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1:METAL=M1:EXIT=-1:XORG=10:YORG=20",True,False,True),
        ("square","CMOS",dict(length=80,width=3,spacing=3,turns=1.25,metal="M4",exit_metal="M3",x=10,y=20),"SQUARE NAME=A:LEN=80:W=3:S=3:N=1.25:METAL=M4:EXIT=M3:XORG=10:YORG=20",True,False,False),
        ("polygon","CMOS",dict(radius=35,sides=6,width=5,spacing=3,turns=1.25,metal="M4",x=20,y=20),"SPIRAL NAME=A:RAD=35:SIDES=6:W=5:S=3:N=1.25:METAL=M4:XORG=20:YORG=20",True,False,False),
        ("multimetal","CMOS",dict(length=60,width=5,spacing=3,turns=1,metal="M5",bottom_metal="M3",x=10,y=20),"MMSQUARE NAME=A:LEN=60:W=5:S=3:N=1:METAL=M5:EXIT=M3:XORG=10:YORG=20",True,False,False),
        ("capacitor","CMOS",dict(length=40,width=5,metal="M2",bottom_metal="M1",x=40,y=50),"CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1:XORG=40:YORG=50",True,False,False),
        ("square","CMOS",dict(length=80,width=5,spacing=3,turns=1.25,metal="M4",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1.25:METAL=M4:EXIT=-1:XORG=10:YORG=20",True,True,False),
        ("square","BiCMOS",dict(length=80,width=5,spacing=3,turns=1.25,metal="M3",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1.25:METAL=M3:EXIT=-1:XORG=10:YORG=20",True,True,False),
    ]
    cases=[]
    with tempfile.TemporaryDirectory(prefix="reasitic-pix-reference-") as directory:
        root=Path(directory);source=root/"tap.cpp";source.write_text(TAP);tap=root/"tap.so"
        subprocess.run(["g++","-m32","-O2","-fPIC","-shared","-nostdlib","-fno-builtin",str(source),"/lib/i386-linux-gnu/libc.so.6","-o",str(tap)],check=True)
        for index,(kind,process,parameters,creation,grounded,eddy,fine) in enumerate(configs):
            technology=(reference/f"run/tek/{process}.tek").read_text()
            for key,value in (("fftx",64),("ffty",64),("chipx",128),("chipy",128)):
                technology=re.sub(rf"(?im)^(\s*{key}\s*=\s*)[\d.]+",rf"\g<1>{value}",technology)
            ground_metal="M1" if process=="CMOS" else "M2"
            ground=dict(kind="wire",parameters=dict(name="G",length=100,width=8,metal=ground_metal,x=10,y=110)) if grounded else None
            mesh=dict(length_cell=20 if fine else 1000,width_cell=3 if fine else 1000,thickness_cell=.5 if fine else 1000,
                      capacitance_length_cell=50 if fine else 1000,capacitance_width_cell=8 if fine else 1000)
            frequency=2 if fine else 1;arg=" G" if grounded else ""
            ground_creation=f"WIRE NAME=G:LEN=100:WID=8:METAL={ground_metal}:XORG=10:YORG=110\n" if grounded else ""
            script=f"CELL {mesh['length_cell']} {mesh['width_cell']} {mesh['thickness_cell']}\nCCELL {mesh['capacitance_length_cell']} {mesh['capacitance_width_cell']}\nEDDY {'ON' if eddy else 'OFF'}\nSAVEMAT TRUE\n{creation}\n{ground_creation}PIX A {frequency}{arg}\nZIN S\nZIN X\nZIN D\nLMAT A {frequency} impedance.out\n"
            # Native 2PORTX falls back to combined Pi2 for wires and joined
            # capacitors/multimetal windings, whereas PIX always uses the
            # extended backend. Multimetal joins overwrite initial type 18.
            known=kind in ("square","polygon")
            if known:script+=f"2PORTX A {frequency} {frequency} 1 Y RECT SLOW y.out{arg}\n2PORTX A {frequency} {frequency} 1 S RECT SLOW s.out{arg}\n"
            path=root/str(index);path.mkdir();(path/"input.asit").write_text(script);(path/"process.tek").write_text(technology)
            environment={k:v for k,v in os.environ.items() if k not in ("LD_LIBRARY_PATH","LD_PRELOAD")};environment["LD_PRELOAD"]=str(tap)
            result=subprocess.run([str(executable),"-g","-t","process.tek","-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=path,timeout=120,start_new_session=True,env=environment)
            if result.returncode or not (path/"pix-values.out").is_file():raise RuntimeError(result.stdout+result.stderr)
            reports={"Q":[],"M":[],"Z":[]}
            for line in (path/"pix-values.out").read_text().splitlines():
                tag,*values=line.split();reports[tag].append([float(v) if math.isfinite(float(v)) else "nan" if math.isnan(float(v)) else "inf" if float(v)>0 else "-inf" for v in values])
            vectors={"C":{},"I":{},"V":{},"B":{}}
            for line in (path/"pix-vectors.out").read_text().splitlines():
                tag,i,j,real,imag=line.split();vectors[tag][int(i)-1,int(j)-1]=[float(real),float(imag)]
            def tapped(tag):
                values=vectors[tag];rows=max(i for i,j in values)+1;columns=max(j for i,j in values)+1
                return [[values[i,j] for j in range(columns)] for i in range(rows)]
            currents,voltages=tapped("I"),tapped("V")
            direct_ports=[currents[0],[[-v for v in z] for z in currents[-1]]]
            cases.append(dict(kind=kind,process=process,parameters=dict(name="A",**parameters),technology=technology,ground=ground,eddy=eddy,mesh=mesh,frequency_hz=frequency*1e9,
                              capacitance_matrix=tapped("C"),inductive_impedance_matrix=read_lmat(path/"impedance.out"),
                              filament_impedance_diagonal=[vectors["B"][i,i] for i in range(len(vectors["B"]))],
                              # The CLI dumper loops rows x rows even for the
                              # one-column vector slice. Only column 1 is defined.
                              currents_first=[[row[0]] for row in currents],voltages_first=[[row[0]] for row in voltages],direct_admittance_matrix=direct_ports,
                              admittance_matrix=port_matrix(path/"y.out") if known else None,scattering_matrix=port_matrix(path/"s.out") if known else None,
                              qualities=reports["Q"][0][1:],metrics=reports["M"][0],input_impedances=reports["Z"],script=script,stdout=result.stdout))
    output=ROOT/"tests/fixtures/pix.json"
    for i,case in enumerate(cases):
        for key in ("capacitance_matrix","inductive_impedance_matrix","currents_first","voltages_first","admittance_matrix","scattering_matrix"):
            if case[key] is not None and any(not math.isfinite(v) for row in case[key] for cell in row for v in cell):
                raise RuntimeError(f"Nonfinite native matrix: {i} {case['kind']} {case['process']} {key}")
    output.write_text(json.dumps(dict(reference="Unmodified native PIX/LMAT snapshots, full-precision sprintf model/ZIN taps, and 2PORTX Y/S exports for its known extended types",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),tap=TAP,cases=cases),indent=2,allow_nan=False)+"\n")
    print(output,len(cases))


if __name__=="__main__":main()

"""Capture native no-eddy PI2 snapshots, printed metrics and precise Y/S records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_potential import read_matrix

ROOT=Path(__file__).resolve().parents[1]


def port_matrix(path):
    records=[list(map(float,line.split())) for line in path.read_text().splitlines() if re.match(r"^\s*[0-9].*[eE][+-]",line)]
    if len(records)!=1 or len(records[0])!=9:
        raise ValueError(f"Expected one native port record in {path}")
    r=records[0]
    return [[r[1:3],r[3:5]],[r[5:7],r[7:9]]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--eddy",action="store_true")
    args=parser.parse_args()
    reference=args.reference.resolve()
    executable=reference/"recomp_cpp/build/cli/asitic"
    configs=[
        ("wire","CMOS",1,dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20",None,"",1000,1000,1000,1000,1000),
        ("square","CMOS",1,dict(length=80,width=5,spacing=3,turns=1,metal="M1",exit_metal="M2",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1:METAL=M1:EXIT=M2:XORG=10:YORG=20",None,"",1000,1000,1000,1000,1000),
        ("square","CMOS",1,dict(length=80,width=5,spacing=3,turns=1,metal="M1",exit_metal="M2",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=3:N=1:METAL=M1:EXIT=M2:XORG=10:YORG=20",None,"",20,3,.5,50,8),
        ("polygon","CMOS",2,dict(radius=35,sides=6,width=5,spacing=3,turns=1.25,metal="M4",x=20,y=20),"SPIRAL NAME=A:RAD=35:SIDES=6:W=5:S=3:N=1.25:METAL=M4:XORG=20:YORG=20",None,"",1000,1000,1000,1000,1000),
        ("wire","CMOS",1,dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20",dict(length=30,width=5,metal="M2",x=10,y=50),"WIRE NAME=G:LEN=30:WID=5:METAL=M2:XORG=10:YORG=50",20,3,.5,20,8),
        ("capacitor","CMOS",1,dict(length=40,width=5,metal="M2",bottom_metal="M1",x=40,y=50),"CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1:XORG=40:YORG=50",None,"",1000,1000,1000,1000,1000),
        ("multimetal","CMOS",1,dict(length=60,width=5,spacing=3,turns=1,metal="M5",bottom_metal="M3",x=10,y=20),"MMSQUARE NAME=A:LEN=60:W=5:S=3:N=1:METAL=M5:EXIT=M3:XORG=10:YORG=20",None,"",1000,1000,1000,1000,1000),
        ("wire","BiCMOS",1,dict(length=40,width=5,metal="M2",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M2:XORG=10:YORG=20",None,"",1000,1000,1000,1000,1000),
    ]
    cases=[]
    for kind,process,frequency,parameters,creation,ground,ground_creation,length,width,thickness,clength,cwidth in configs:
        technology=(reference/f"run/tek/{process}.tek").read_text()
        # Independent 64-square FFT / 128-um chip fixtures complement CAP's
        # original 128-square tables and keep repeated end-to-end tests small.
        for field,value in (("fftx",64),("ffty",64),("chipx",128),("chipy",128)):
            technology=re.sub(rf"(?im)^(\s*{field}\s*=\s*)[\d.]+",rf"\g<1>{value}",technology)
        ground_arg=" G" if ground else ""
        script=f"CELL {length} {width} {thickness}\nCCELL {clength} {cwidth}\nEDDY "+("ON" if args.eddy else "OFF")+f"\nSAVEMAT TRUE\n{creation}\n{ground_creation}\nPI2 A {frequency}{ground_arg}\n"
        script+=f"2PORT A {frequency} {frequency} 1 Y RECT SLOW y.out{ground_arg}\n2PORT A {frequency} {frequency} 1 S RECT SLOW s.out{ground_arg}\nZIN S\nZIN D\nSHUNTR S\nSHUNTR D\n"
        with tempfile.TemporaryDirectory(prefix="reasitic-network-reference-") as directory:
            path=Path(directory)
            (path/"input.asit").write_text(script)
            (path/"process.tek").write_text(technology)
            result=subprocess.run([str(executable),"-g","-t","process.tek","-x","input.asit"],input="quit\n",capture_output=True,text=True,
                                  cwd=directory,timeout=60,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
            if result.returncode or not (path/"s.out").is_file() or "Pi Model at" not in result.stdout:
                raise RuntimeError(result.stdout+result.stderr)
            cases.append(dict(kind=kind,process=process,technology=technology,parameters=dict(name="A",**parameters),
                              ground=dict(kind="wire",parameters=dict(name="G",**ground)) if ground else None,
                              frequency_hz=frequency*1e9,eddy=args.eddy,mesh=dict(length_cell=length,width_cell=width,thickness_cell=thickness,
                              capacitance_length_cell=clength,capacitance_width_cell=cwidth),
                              capacitance_matrix=read_matrix(path/"ZC.out"),inductive_admittance_matrix=read_matrix(path/"YM.out"),
                              nodal_capacitance_matrix=read_matrix(path/"Ycap.out"),admittance_matrix=port_matrix(path/"y.out"),
                              scattering_matrix=port_matrix(path/"s.out"),script=script,stdout=result.stdout))
    output=ROOT/("tests/fixtures/network_eddy.json" if args.eddy else "tests/fixtures/network.json")
    output.write_text(json.dumps(dict(reference="Unmodified C++ PI2 command, snapshots and 15-digit Y/S output",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),cases=cases),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":
    main()

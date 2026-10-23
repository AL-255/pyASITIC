"""Capture full native layered-potential/admittance matrices and FFT tables."""
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


def read_matrix(path):
    rows=[]
    for line in path.read_text().splitlines():
        cells=line.split()
        if len(cells)==4:
            i,j=int(cells[0])-1,int(cells[1])-1
            while len(rows)<=i:
                rows.append([])
            rows[i].append([float(cells[2]),float(cells[3])])
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    reference=args.reference.resolve()
    executable=reference/"recomp_cpp/build/cli/asitic"
    configs=[
        ("wire", "CMOS",1,dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20",None,"",1000,1000),
        ("wire", "CMOS",5,dict(length=40,width=5,metal="M5",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M5:XORG=10:YORG=20",None,"",1000,1000),
        ("square","CMOS",1,dict(length=80,width=5,spacing=2,turns=1,metal="M1",exit_metal="M2",x=10,y=20),"SQUARE NAME=A:LEN=80:W=5:S=2:N=1:METAL=M1:EXIT=M2:XORG=10:YORG=20",None,"",1000,1000),
        ("polygon","CMOS",2,dict(radius=50,sides=6,width=8,spacing=4,turns=1.5,metal="M4",x=100,y=100),"SPIRAL NAME=A:RAD=50:SIDES=6:W=8:S=4:N=1.5:METAL=M4:XORG=100:YORG=100",None,"",1000,1000),
        ("wire","CMOS",1,dict(length=40,width=5,metal="M1",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=10:YORG=20",dict(length=30,width=5,metal="M2",x=10,y=50),"WIRE NAME=G:LEN=30:WID=5:METAL=M2:XORG=10:YORG=50",20,8),
        ("capacitor","CMOS",1,dict(length=40,width=5,metal="M2",bottom_metal="M1",x=50,y=50),"CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1:XORG=50:YORG=50",None,"",1000,1000),
        ("wire","BiCMOS",1,dict(length=40,width=5,metal="M2",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M2:XORG=10:YORG=20",None,"",1000,1000),
        ("wire","BiCMOS",2,dict(length=40,width=5,metal="M3",x=10,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M3:XORG=10:YORG=20",dict(length=30,width=5,metal="MSUB",x=10,y=50),"WIRE NAME=G:LEN=30:WID=5:METAL=MSUB:XORG=10:YORG=50",1000,1000),
    ]
    cases=[]
    for kind,process,frequency,parameters,creation,ground,ground_creation,length_cell,width_cell in configs:
        technology=(reference/f"run/tek/{process}.tek").read_text()
        script=f"CELL 1000 1000 1000\nCCELL {length_cell} {width_cell}\nSAVEMAT TRUE\n"+creation+"\n"+ground_creation+f"\nCAP A {frequency}"+(" G" if ground else "")+"\n"
        with tempfile.TemporaryDirectory(prefix="reasitic-potential-reference-") as directory:
            Path(directory,"input.asit").write_text(script)
            result=subprocess.run([str(executable),"-g","-t",str(reference/f"run/tek/{process}.tek"),"-x","input.asit"],input="quit\n",
                                  capture_output=True,text=True,cwd=directory,timeout=60,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
            if result.returncode or not Path(directory,"YC.out").is_file():
                raise RuntimeError(result.stdout+result.stderr)
            cache_path=next(Path(directory).glob("*.dat"))
            cache=cache_path.read_bytes()
            nx,ny,f=struct.unpack_from("<iid",cache)
            layers=len(re.findall(r"<layer>",technology,re.I))
            metals=len(re.findall(r"<metal>",technology,re.I))
            offset=16+40*layers+236*metals
            def value(index):
                return list(struct.unpack_from("<dd",cache,index))
            greens=[]
            for source in range(metals):
                for target in range(source,metals):
                    xy_offset=offset
                    x_offset=xy_offset+(nx+1)*(ny+1)*16
                    y_offset=x_offset+2*nx*16
                    greens.append(dict(source=source,target=target,
                                       x=[[i,value(x_offset+i*16)] for i in sorted({0,1,2,nx//4,nx//2,nx-1,nx,nx+1,2*nx-1})],
                                       y=[[i,value(y_offset+i*16)] for i in sorted({0,1,2,ny//4,ny//2,ny-1,ny,ny+1,2*ny-1})],
                                       xy=[[x,y,value(xy_offset+(x*(nx+1)+y)*16)] for x,y in [(1,1),(1,ny//2),(nx//2,1),(nx//2,ny//2),(nx-1,ny-1),(nx,0),(0,ny),(nx,ny)]]))
                    offset=y_offset+2*ny*16
            cases.append(dict(kind=kind,process=process,technology=technology,parameters=dict(name="A",**parameters),ground=dict(name="G",**ground) if ground else None,
                              frequency_hz=frequency*1e9,length_cell=length_cell,width_cell=width_cell,
                              potential=read_matrix(Path(directory,"Pmat.out")),matrix=read_matrix(Path(directory,"YC.out")),greens=greens,
                              script=script,stdout=result.stdout,cache_sha256=hashlib.sha256(cache).hexdigest()))
    output=ROOT/"tests/fixtures/potential.json"
    output.write_text(json.dumps(dict(reference="C++ CAP command process, Pmat/YC snapshots and actual cache FFT entries",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),cases=cases),indent=2)+"\n")
    print(output)


if __name__=="__main__":
    main()

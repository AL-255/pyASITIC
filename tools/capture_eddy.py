"""Capture complete native LMAT matrices with EDDY ON, including fine meshes."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def read_matrix(path,complex_values=True):
    rows=[]
    for line in path.read_text().splitlines():
        cells=line.split()
        if len(cells)!=(4 if complex_values else 3):continue
        i=int(cells[0])-(0 if complex_values else 1)
        while len(rows)<=i:rows.append([])
        rows[i].append([float(cells[2]),float(cells[3])] if complex_values else float(cells[2]))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();executable=reference/"recomp_cpp/build/cli/asitic"
    configs=[
        ("wire","CMOS",dict(length=40,width=5,metal="M1"),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=0:YORG=0"),
        ("square","CMOS",dict(length=80,width=5,spacing=2,turns=1,metal="M1"),"SQUARE NAME=A:LEN=80:W=5:S=2:N=1:METAL=M1:EXIT=-1:XORG=0:YORG=0"),
        ("square","CMOS",dict(length=100,width=5,spacing=2,turns=2.5,metal="M5"),"SQUARE NAME=A:LEN=100:W=5:S=2:N=2.5:METAL=M5:EXIT=-1:XORG=0:YORG=0"),
        ("polygon","CMOS",dict(radius=50,sides=6,width=3,spacing=2,turns=1.5,metal="M4"),"SPIRAL NAME=A:RAD=50:SIDES=6:W=3:S=2:N=1.5:METAL=M4:XORG=0:YORG=0"),
        ("square","CMOS",dict(length=80,height=70,width=3,spacing=2,turns=1.25,metal="M4",exit_metal="M3"),"SQUARE NAME=A:LEN=80:WID=70:W=3:S=2:N=1.25:METAL=M4:EXIT=M3:XORG=0:YORG=0"),
        ("wire","BiCMOS",dict(length=40,width=5,metal="M2"),"WIRE NAME=A:LEN=40:WID=5:METAL=M2:XORG=0:YORG=0"),
        ("square","BiCMOS",dict(length=80,width=5,spacing=2,turns=1.25,metal="M3"),"SQUARE NAME=A:LEN=80:W=5:S=2:N=1.25:METAL=M3:EXIT=-1:XORG=0:YORG=0"),
        ("polygon","BiCMOS",dict(radius=40,sides=8,width=5,spacing=3,turns=1.5,metal="M3"),"SPIRAL NAME=A:RAD=40:SIDES=8:W=5:S=3:N=1.5:METAL=M3:XORG=0:YORG=0"),
    ]
    cases=[]
    for kind,process,parameters,creation in configs:
        technology=(reference/f"run/tek/{process}.tek").read_text()
        script=f"CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY ON\nSAVEMAT TRUE\n{creation}\nLMAT A 1 coarse.out\nCELL 50 3 .5\nCCELL 50 1000\nLMAT A 2 fine.out\n"
        with tempfile.TemporaryDirectory(prefix="reasitic-eddy-reference-") as directory:
            path=Path(directory);(path/"input.asit").write_text(script)
            result=subprocess.run([str(executable),"-g","-t",str(reference/f"run/tek/{process}.tek"),"-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=directory,timeout=120,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
            if result.returncode or not (path/"fine.out").is_file():raise RuntimeError(result.stdout+result.stderr)
            cases.append(dict(kind=kind,process=process,technology=technology,parameters=parameters,script=script,stdout=result.stdout,
                              matrix_1ghz=read_matrix(path/"coarse.out"),matrix_fine_2ghz=read_matrix(path/"fine.out"),
                              eddy_fine_2ghz=read_matrix(path/"Eddy.out",False) if (path/"Eddy.out").is_file() else None))
    # The native axial-length rule can take sqrt(negative) for short/wide
    # joined conductors. Record the failure instead of inventing a correction.
    script="CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY ON\nWIRE NAME=P1:LEN=10:WID=8:METAL=M4:XORG=10:YORG=20\nWIRE NAME=A:LEN=40:WID=5:METAL=M4:XORG=20:YORG=20\nJOIN P1 A\nLMAT P1 1 invalid.out\n"
    with tempfile.TemporaryDirectory(prefix="reasitic-eddy-nonfinite-") as directory:
        path=Path(directory);(path/"input.asit").write_text(script)
        result=subprocess.run([str(executable),"-g","-t",str(reference/"run/tek/CMOS.tek"),"-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=directory,timeout=120,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
        if result.returncode or not (path/"invalid.out").is_file():raise RuntimeError(result.stdout+result.stderr)
        matrix=[[[value if math.isfinite(value) else str(value) for value in cell] for cell in row] for row in read_matrix(path/"invalid.out")]
        nonfinite=dict(technology=(reference/"run/tek/CMOS.tek").read_text(),script=script,stdout=result.stdout,matrix=matrix,
                       first=dict(length=10,width=8,metal="M4",x=10,y=20),second=dict(length=40,width=5,metal="M4",x=20,y=20))
    output=ROOT/"tests/fixtures/eddy.json"
    output.write_text(json.dumps(dict(reference="Unmodified C++ LMAT command with EDDY ON",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),cases=cases,nonfinite_cases=[nonfinite]),indent=2,allow_nan=False)+"\n")
    print(output)


if __name__=="__main__":main()

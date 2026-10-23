"""Capture real C++ reference INDUCTANCE/RESISHF command sessions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import struct
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference",type=Path,required=True)
    args = parser.parse_args()
    root = args.reference.resolve()
    executable = root/"recomp_cpp/build/cli/asitic"
    cases = []
    for i,(kind,params,command) in enumerate([
        ("wire",dict(length=40,width=5,metal="M1"),"WIRE NAME=A:LEN=40:WID=5:METAL=M1:XORG=0:YORG=0"),
        ("wire",dict(length=80,width=10,metal="M5",angle=37),"WIRE NAME=A:LEN=80:WID=10:METAL=M5:XORG=0:YORG=0:ORIENT=37"),
        ("square",dict(length=80,height=70,width=3,spacing=2,turns=1.25,metal="M4",exit_metal="M3"),"SQUARE NAME=A:LEN=80:WID=70:W=3:S=2:N=1.25:METAL=M4:EXIT=M3"),
        ("square",dict(length=100,width=5,spacing=2,turns=2.5,metal="M5"),"SQUARE NAME=A:LEN=100:W=5:S=2:N=2.5:METAL=M5:EXIT=-1"),
        ("square",dict(length=120,height=80,width=4,spacing=3,turns=1.75,metal="M3",phase=-1),"SQUARE NAME=A:LEN=120:WID=80:W=4:S=3:N=1.75:METAL=M3:EXIT=-1:PHASE=-1"),
        ("polygon",dict(radius=50,sides=6,width=3,spacing=2,turns=1.5,metal="M4"),"SPIRAL NAME=A:RAD=50:SIDES=6:W=3:S=2:N=1.5:METAL=M4"),
        ("polygon",dict(radius=70,sides=8,width=5,spacing=3,turns=2,metal="M5"),"SPIRAL NAME=A:RAD=70:SIDES=8:W=5:S=3:N=2:METAL=M5"),
        ("ring",dict(radius=40,sides=16,width=3,gap=20,metal="M4"),"RING NAME=A:RAD=40:SIDES=16:W=3:GAP=20:METAL=M4"),
        ("capacitor",dict(length=40,width=5,metal="M2",bottom_metal="M1"),"CAPACITOR NAME=A:LEN=40:WID=5:METAL1=M2:METAL2=M1"),
        ("multimetal",dict(length=80,height=70,width=3,spacing=2,turns=1,metal="M5",bottom_metal="M3"),"MMSQUARE NAME=A:LEN=80:WID=70:W=3:S=2:N=1:METAL=M5:EXIT=M3"),
        ("symmetric_square",dict(length=100,inner_gap=15,width=3,spacing=2,turns=2,metal="M4",secondary_metal="M3"),"SYMSQ NAME=A:LEN=100:ILEN=15:W=3:S=2:N=2:METAL=M4:METAL2=M3"),
        ("symmetric_polygon",dict(radius=50,sides=6,inner_gap=15,width=3,spacing=2,turns=2,metal="M4",secondary_metal="M3",x=57.5,y=57.5),"SYMPOLY NAME=A:RAD=50:ILEN=15:SIDES=6:W=3:S=2:N=2:METAL=M4:METAL2=M3"),
    ]):
        with tempfile.TemporaryDirectory(prefix="reasitic-reference-") as directory:
            script = "CELL 1000 1000 1000\nCCELL 1000 1000\n"+command+"\nBSAVE geometry A\nINDUCTANCE A\nRESIS A\n"
            frequencies = [0.001,0.1,1,10,100]
            script += "".join(f"RESISHF A {f}\n" for f in frequencies)
            script += "LMAT A 1 matrix.out\n"
            script += "CELL 50 3 0.5\nCCELL 50 1000\nLMAT A 2 mesh.out\n"
            script += "CELL 20 1000 1000\nCCELL 50 1000\nLMAT A 1 unequal.out\n"
            Path(directory,"input.asit").write_text(script)
            result = subprocess.run([str(executable),"-g","-t",str(root/"run/tek/CMOS.tek"),"-x","input.asit"],
                                    input="quit\n",text=True,capture_output=True,cwd=directory,timeout=30,start_new_session=True,
                                    env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
            output = result.stdout
            inductance = re.search(r"Inductance of A = ([\d.eE+-]+)",output)
            dc = re.search(r"Resistance of A = ([\d.eE+-]+)",output)
            hf = re.findall(r"A: at ([\d.eE+-]+) GHz R = ([\d.eE+-]+)",output)
            if result.returncode or not inductance or not dc or len(hf)!=len(frequencies):
                raise RuntimeError(output+result.stderr)
            def read_matrix(filename):
                matrix = []
                for line in Path(directory,filename).read_text().splitlines():
                    parts=line.split()
                    if len(parts)==4:
                        i,j=int(parts[0]),int(parts[1])
                        while len(matrix)<=i:
                            matrix.append([])
                        matrix[i].append([float(parts[2]),float(parts[3])])
                return matrix
            binary=next(Path(directory).glob("geometry.*")).read_bytes()
            offset=20
            if struct.unpack_from("<I",binary,offset)[0]!=0x88:
                raise ValueError("Invalid native binary shape marker")
            offset+=4+0xbc
            segments=[]
            while struct.unpack_from("<I",binary,offset)[0]==0x89:
                offset+=4
                segments.append(list(struct.unpack_from("<6d",binary,offset)))
                offset+=0xf0
            cases.append(dict(kind=kind,parameters=params,script=script,stdout=output,geometry_endpoints=segments,matrix_1ghz=read_matrix("matrix.out"),matrix_fine_2ghz=read_matrix("mesh.out"),matrix_unequal_1ghz=read_matrix("unequal.out"),
                              inductance_nh=float(inductance[1]),dc=float(dc[1]),
                              hf=[[float(f)*1e9,float(r.rstrip("."))] for f,r in hf]))
    destination = Path(__file__).resolve().parents[1]/"tests/fixtures/analysis.json"
    destination.write_text(json.dumps(dict(reference="C++ reconstruction command process",executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                                           reference_commit=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),cases=cases),indent=2)+"\n")
    print(destination)


if __name__ == "__main__":
    main()

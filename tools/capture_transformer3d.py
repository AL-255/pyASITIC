"""Capture connected C++ 3D creator sessions, geometry and electrical reports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args()
    reference=args.reference.resolve()
    executable=reference/"recomp_cpp/build/cli/asitic"
    cases=[]
    for parameters in [
        dict(length=80,height=80,width=3,spacing=8,turns=1,metal="M4",secondary_metal="M3"),
        dict(length=80,height=80,width=3,spacing=8,turns=1.25,metal="M4",secondary_metal="M3"),
        dict(length=120,height=90,width=5,spacing=10,turns=1.75,metal="M5",secondary_metal="M1"),
        dict(length=80,height=80,width=3,spacing=8,turns=2,metal="M4",secondary_metal="M3"),
        dict(length=120,height=100,width=2.5,spacing=7.75,turns=2.5,metal="M1",secondary_metal="M5"),
        dict(length=160,height=140,width=4.125,spacing=9.25,turns=3.2,metal="M5",secondary_metal="M2",angle=37,phase=-1),
        dict(length=160,height=150,width=3,spacing=8,turns=3.75,metal="M2",secondary_metal="M4",angle=-90),
    ]:
        parameters={"primary_name":"P","secondary_name":"S","x":100,"y":100,"angle":0,"phase":1,**parameters}
        answers=["P","S",f'{parameters["length"]} {parameters["height"]}',str(parameters["width"]),str(parameters["spacing"]),str(parameters["turns"]),parameters["metal"],parameters["secondary_metal"],"100 100",str(parameters["angle"]),str(parameters["phase"]),"quit"]
        script="CELL 1000 1000 1000\nCCELL 1000 1000\n3DMIRRORTRANS\nSAVE saved\n"
        for name in ("P","S"):
            script+=f"INDUCTANCE {name}\nRESIS {name}\nRESISHF {name} 2\nLMAT {name} 1 {name}.out\n"
        with tempfile.TemporaryDirectory(prefix="reasitic-3d-reference-") as directory:
            Path(directory,"input.asit").write_text(script)
            result=subprocess.run([str(executable),"-g","-t",str(reference/"run/tek/CMOS.tek"),"-x","input.asit"],input="\n".join(answers)+"\n",
                                  text=True,capture_output=True,cwd=directory,timeout=30,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
            if result.returncode:
                raise RuntimeError(result.stdout+result.stderr)
            geometry={}
            for block in Path(directory,"saved.spi").read_text().split("BLOCK=SPIRAL")[1:]:
                name=re.search(r"NAME=([^:]+)",block)[1]
                geometry[name]=[]
                for part in block.split("BLOCK=SEGMENT")[1:]:
                    values=dict(re.findall(r"(\w+)=([^:\n]+)",part.split("BLOCK=ENDSEGMENT")[0]))
                    geometry[name].append({key:value if key=="METAL" else float(value) for key,value in values.items() if key not in ("NX","NY")})
            matrices={}
            for name in ("P","S"):
                matrix=[]
                for line in Path(directory,name+".out").read_text().splitlines():
                    parts=line.split()
                    if len(parts)==4:
                        i,j=int(parts[0]),int(parts[1])
                        while len(matrix)<=i:
                            matrix.append([])
                        matrix[i].append([float(parts[2]),float(parts[3])])
                matrices[name]=matrix
            cases.append(dict(parameters=parameters,geometry=geometry,matrices=matrices,script=script,stdin="\n".join(answers)+"\n",stdout=result.stdout,
                              inductance={n:float(v) for n,v in re.findall(r"Inductance of (P|S) = ([\d.eE+-]+)",result.stdout)},
                              dc={n:float(v) for n,v in re.findall(r"Resistance of (P|S) = ([\d.eE+-]+)",result.stdout)},
                              hf={n:float(v.rstrip(".")) for n,v in re.findall(r"(P|S): at 2.000000 GHz R = ([\d.eE+-]+)",result.stdout)}))
    destination=ROOT/"tests/fixtures/transformer3d.json"
    destination.write_text(json.dumps(dict(reference="C++ reconstruction 3DMIRRORTRANS / 3DTrans command",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),
                                          source_sha256=hashlib.sha256((reference/"recomp_cpp/src/transformer3d.cpp").read_bytes()).hexdigest(),cases=cases),indent=2)+"\n")
    print(destination)


if __name__=="__main__":
    main()

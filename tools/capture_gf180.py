"""Exercise generated GF180 files in the unmodified ASITIC executable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from capture_network import port_matrix
from capture_potential import read_matrix

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve();binary=reference/"recomp_cpp/build/cli/asitic";cases=[]
    for identifier,density,kind,metal,creation,parameters in [
        ("gf180-1p3m-6ka-no-mim","none","wire","M3","WIRE NAME=A:LEN=40:WID=8:METAL=M3:XORG=40:YORG=40",dict(length=40,width=8,x=40,y=40)),
        ("gf180-1p5m-11ka-mim-b","1.5","square","M5","SQUARE NAME=A:LEN=80:W=8:S=4:N=1:METAL=M5:EXIT=-1:XORG=40:YORG=40",dict(length=80,width=8,spacing=4,turns=1,exit_metal=-1,x=40,y=40)),
        ("gf180-1p6m-30ka-mim-a","1.0","polygon","M6","SPIRAL NAME=A:RAD=40:SIDES=6:W=8:S=4:N=1.25:METAL=M6:XORG=60:YORG=60",dict(radius=40,sides=6,width=8,spacing=4,turns=1.25,x=60,y=60)),
    ]:
        cat=json.loads((ROOT/"src/reasitic/technologies/catalog.json").read_text())
        preset=next(p for p in cat["presets"] if p["id"]==identifier)
        filename=preset["variants"][density];text=(ROOT/"src/reasitic/technologies"/filename).read_text()
        script=f"CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\nSAVEMAT TRUE\n{creation}\nPI2 A 2\n2PORT A 2 2 1 Y RECT SLOW y.out\n2PORT A 2 2 1 S RECT SLOW s.out\n"
        with TemporaryDirectory(prefix="reasitic-gf180-reference-") as directory:
            path=Path(directory);(path/"process.tek").write_text(text);(path/"input.asit").write_text(script)
            env={k:v for k,v in os.environ.items() if k not in ("LD_PRELOAD","LD_LIBRARY_PATH")}
            run=subprocess.run([str(binary),"-g","-t","process.tek","-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=directory,timeout=120,start_new_session=True,env=env)
            if run.returncode or not (path/"s.out").is_file():raise RuntimeError(run.stdout+run.stderr)
            cases.append(dict(preset=identifier,density=density,filename=filename,technology=text,kind=kind,parameters=dict(name="A",metal=metal,**parameters),frequency_hz=2e9,
                              capacitance_matrix=read_matrix(path/"ZC.out"),inductive_admittance_matrix=read_matrix(path/"YM.out"),
                              admittance_matrix=port_matrix(path/"y.out"),scattering_matrix=port_matrix(path/"s.out"),script=script,stdout=run.stdout))
    destination=ROOT/"tests/fixtures/gf180_network.json"
    destination.write_text(json.dumps(dict(reference="Unmodified native PI2/2PORT with generated GF180 .tek files; these check port consistency, not foundry RF calibration",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),cases=cases),indent=2,allow_nan=False)+"\n")
    print(destination,len(cases))


if __name__=="__main__":main()

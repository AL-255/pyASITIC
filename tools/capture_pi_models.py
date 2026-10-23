"""Capture native PI3/PI4 circuit models and precise Y/S port records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from capture_network import port_matrix

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    args=parser.parse_args();reference=args.reference.resolve()
    executable=reference/"recomp_cpp/build/cli/asitic"
    technology=(reference/"run/tek/CMOS.tek").read_text()
    for key,value in (("fftx",64),("ffty",64),("chipx",128),("chipy",128)):
        technology=re.sub(rf"(?im)^(\s*{key}\s*=\s*)[\d.]+",rf"\g<1>{value}",technology)
    cases=[]
    for model in ("pi3","pi4"):
        for kind,parameters,creation in [
            ("wire",dict(length=40,width=5,metal="M4",x=20,y=20),"WIRE NAME=A:LEN=40:WID=5:METAL=M4:XORG=20:YORG=20"),
            ("square",dict(length=60,width=5,spacing=3,turns=1,metal="M4",x=20,y=20),"SQUARE NAME=A:LEN=60:W=5:S=3:N=1:METAL=M4:EXIT=-1:XORG=20:YORG=20"),
        ]:
            for frequency in (1,5):
                ground=dict(kind="wire",parameters=dict(name="G",length=100,width=8,metal="M1",x=10,y=100))
                first_pad=dict(kind="wire",parameters=dict(name="P1",length=10,width=8,metal="M4",x=10,y=20))
                second_pad=dict(kind="wire",parameters=dict(name="P2",length=10,width=8,metal="M4",x=95,y=20))
                script="CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\nSAVEMAT TRUE\n"+creation+"\nWIRE NAME=G:LEN=100:WID=8:METAL=M1:XORG=10:YORG=100\n"
                if model=="pi3":
                    script+=f"PI3 A G {frequency}\n2PORT A {frequency} {frequency} 1 Y RECT SLOW y.out G\n2PORT A {frequency} {frequency} 1 S RECT SLOW s.out G\n"
                else:
                    script+="WIRE NAME=P1:LEN=10:WID=8:METAL=M4:XORG=10:YORG=20\nWIRE NAME=P2:LEN=10:WID=8:METAL=M4:XORG=95:YORG=20\n"
                    script+=f"PI4 A {frequency} P1 P2 G\n2PORTPAD A P1 P2 {frequency} {frequency} 1 Y RECT y.out G\n2PORTPAD A P1 P2 {frequency} {frequency} 1 S RECT s.out G\n"
                with tempfile.TemporaryDirectory(prefix="reasitic-pi-model-reference-") as directory:
                    path=Path(directory);(path/"input.asit").write_text(script);(path/"process.tek").write_text(technology)
                    result=subprocess.run([str(executable),"-g","-t","process.tek","-x","input.asit"],input="quit\n",capture_output=True,text=True,cwd=directory,timeout=60,start_new_session=True,env={k:v for k,v in os.environ.items() if k!="LD_LIBRARY_PATH"})
                    if result.returncode or not (path/"y.out").is_file():
                        raise RuntimeError(result.stdout+result.stderr)
                    cases.append(dict(model=model,kind=kind,parameters=dict(name="A",**parameters),technology=technology,ground=ground,
                                      first_pad=first_pad if model=="pi4" else None,second_pad=second_pad if model=="pi4" else None,
                                      frequency_hz=frequency*1e9,admittance_matrix=port_matrix(path/"y.out"),scattering_matrix=port_matrix(path/"s.out"),
                                      model_stdout=result.stdout.split("2PORT")[0],stdout=result.stdout,script=script))
    output=ROOT/"tests/fixtures/pi_models.json"
    output.write_text(json.dumps(dict(reference="Unmodified native PI3/PI4 commands and 2PORT/2PORTPAD Y/S records",reference_commit=subprocess.check_output(["git","-C",str(reference),"rev-parse","HEAD"],text=True).strip(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),cases=cases),indent=2)+"\n")
    print(output)


if __name__=="__main__":
    main()

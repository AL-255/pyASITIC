"""Capture dense Pi2 models directly from the original ASITIC process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from capture_network import port_matrix

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_SHA256="72bcb93444604b89a65cb64e5825bfcff0ac740a816120d0f171855206bd572f"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--native-library-path",required=True)
    args=parser.parse_args();original=args.reference.resolve()/"run/asitic.linux.2.2"
    if hashlib.sha256(original.read_bytes()).hexdigest()!=ORIGINAL_SHA256:raise ValueError("Unexpected original executable checksum")
    base=json.loads((ROOT/"tests/fixtures/network.json").read_text())["cases"][2]
    creation=next(line for line in base["script"].splitlines() if line.startswith("SQUARE "))
    cases=[]
    for fft,frequency in ((64,1),(128,1),(128,5),(128,20)):
        technology=base["technology"] if fft==64 else (args.reference/"run/tek/CMOS.tek").read_text()
        script=f"CELL 5 1.5 0.5\nCCELL 50 8\nEDDY OFF\n{creation}\nPI2 A {frequency}\n"
        script+=f"2PORT A {frequency} {frequency} 1 Y RECT SLOW y.out\n2PORT A {frequency} {frequency} 1 S RECT SLOW s.out\n"
        with tempfile.TemporaryDirectory(prefix="pyasitic-original-dense-network-") as directory:
            work=Path(directory);(work/"process.tek").write_text(technology);(work/"input.asit").write_text(script)
            result=subprocess.run([str(original),"-g","-t","process.tek","-x","input.asit"],cwd=work,
                env=dict(os.environ,LD_LIBRARY_PATH=args.native_library_path,TERM="dumb",INPUTRC="/dev/null"),
                input="EXIT\n",text=True,capture_output=True,start_new_session=True,timeout=60)
            if result.returncode or "Pi Model at" not in result.stdout:raise RuntimeError(result.stdout+result.stderr)
            cases.append(dict(kind=base["kind"],parameters=base["parameters"],technology=technology,frequency_hz=frequency*1e9,fft=fft,
                mesh=dict(length_cell=5,width_cell=1.5,thickness_cell=.5,capacitance_length_cell=50,capacitance_width_cell=8),
                admittance_matrix=port_matrix(work/"y.out"),scattering_matrix=port_matrix(work/"s.out"),stdout=result.stdout,script=script))
    output=ROOT/"tests/fixtures/network_dense.json"
    output.write_text(json.dumps(dict(reference="Unmodified original PI2 and precise 2PORT Y/S at 189 filaments, 63 contacts; no reconstructed executable.",original_sha256=ORIGINAL_SHA256,cases=cases),indent=2)+"\n")
    print(output,len(cases),"direct original-binary dense network sessions")


if __name__=="__main__":main()

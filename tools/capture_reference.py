"""Capture immutable original-ASITIC SAVE/RESIS fixtures from the reference repo.

Run manually with --reference ~/github/asitic-re. Ordinary CI uses committed
fixtures and does not need the legacy executable or libraries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference",type=Path,required=True)
    args = parser.parse_args()
    root = args.reference.resolve()
    proof = root/"recomp_cpp/build/cli/native-creator-proof"
    fixtures = []
    for family in ("square","polygon","wire","ring","via","capacitor","multimetal_square"):
        directory = proof/family/"native"
        text = (directory/"saved.spi").read_text()
        shapes = []
        for block in text.split("BLOCK=SPIRAL")[1:]:
            header = block.split("BLOCK=SEGMENT")[0]
            fields = dict(re.findall(r"(\w+)=([^:\n]+)",header))
            segments = []
            for segment in block.split("BLOCK=SEGMENT")[1:]:
                values = dict(re.findall(r"(\w+)=([^:\n]+)",segment.split("BLOCK=ENDSEGMENT")[0]))
                # Uninitialized T for vias and NX/NY for metals are deliberately
                # excluded; endpoints/layer/width are physically defined.
                segments.append({k:v if k=="METAL" else float(v) for k,v in values.items() if k not in ("T","NX","NY")})
            shapes.append({"fields":fields,"segments":segments})
        log = (directory/"stdout.log").read_text()
        resistances = {name:float(value) for name,value in re.findall(r"Resistance of (\S+) = ([\d.eE+-]+)",log)}
        fixtures.append({"family":family,"script":(directory/"input.asit").read_text(),"stdin":(directory/"stdin.txt").read_text(),"shapes":shapes,"resistance_dc":resistances,
                         "source_sha256":hashlib.sha256((directory/"saved.spi").read_bytes()).hexdigest()})
    out = Path(__file__).resolve().parents[1]/"tests/fixtures/creators.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"reference_commit":subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),
                               "source":"Original executable native-creator-proof, saved.spi before LMAT meshing",
                               "fixtures":fixtures},indent=2)+"\n")
    print(out)


if __name__ == "__main__":
    main()

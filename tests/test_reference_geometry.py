import json
from pathlib import Path
import unittest
import math
import struct
from reasitic import build, Technology, resistance_dc

FIXTURES = json.loads((Path(__file__).parent/"fixtures/creators.json").read_text())["fixtures"]


class ReferenceGeometryTests(unittest.TestCase):
    def test_original_creator_records(self):
        tech = Technology.default()
        for fixture in FIXTURES:
            for expected in fixture["shapes"]:
                f = expected["fields"]
                p = dict(name=f["NAME"],length=float(f["LEN"]),height=float(f["WID"]),width=float(f["W"]),
                         spacing=float(f["S"]),radius=float(f["RAD"]),angle=float(f["ORIENT"])*180/3.141592653589793,
                         x=float(f["XORG"]),y=float(f["YORG"]),phase=int(f["PHASE"]),sides=int(f["SIDES"]))
                family = {"multimetal_square":"multimetal"}.get(fixture["family"],fixture["family"])
                if family in ("square","polygon","multimetal"):
                    p["turns"] = float(f["N"])
                if family == "ring":
                    # SAVE prints six significant digits; native keyword angles
                    # are converted from degrees then stored as binary32.
                    gap = float(next(part.split("=")[1] for part in fixture["script"].split(":") if part.startswith("GAP=")))
                    p["gap"] = struct.unpack("f",struct.pack("f",math.radians(gap)))[0]*180/math.pi
                if family == "via":
                    # Native N is not the array count; get the actual keyword script.
                    lines = fixture["stdin"].splitlines()
                    index = lines.index(f["NAME"])
                    p.update(via=lines[index+1],nx=int(lines[index+2]),ny=int(lines[index+3]),sides=16)
                else:
                    p["metal"] = f["METAL"]
                if family == "square":
                    p["exit_metal"] = f.get("EXIT",-1)
                if family == "capacitor":
                    p["bottom_metal"] = f["EXIT"]
                if family == "multimetal":
                    p["bottom_metal"] = f["EXIT"]
                with self.subTest(family=family,name=f["NAME"]):
                    shape = build(family,technology=tech,**p)
                    self.assertEqual(len(shape.segments),len(expected["segments"]))
                    names = [m.name for m in tech.metals]+[v.name for v in tech.vias]
                    for i,(s,e) in enumerate(zip(shape.segments,expected["segments"])):
                        self.assertEqual(names[s.metal],e["METAL"],f"segment {i}")
                        fields = dict(AX=s.outer_start[0],AY=s.outer_start[1],BX=s.outer_end[0],BY=s.outer_end[1],
                                      CX=s.inner_start[0],CY=s.inner_start[1],DX=s.inner_end[0],DY=s.inner_end[1],
                                      PORT1X=s.start[0],PORT1Y=s.start[1],PORT2X=s.end[0],PORT2Y=s.end[1],W=s.width)
                        for key,value in fields.items():
                            self.assertAlmostEqual(value,e[key],delta=5.1e-7,msg=f"segment {i} {key}")
                    if f["NAME"] in fixture["resistance_dc"]:
                        self.assertAlmostEqual(resistance_dc(shape,tech),fixture["resistance_dc"][f["NAME"]],delta=5.1e-7)


if __name__ == "__main__":
    unittest.main()

"""Run CI Python groups without reducing local unittest discovery coverage."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flatten(test)
        else:yield test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group",choices=("plan","core","potential"));parser.add_argument("--process");parser.add_argument("--frequency",type=float)
    args=parser.parse_args()
    if args.group=="plan":
        cases=json.loads((ROOT/"tests/fixtures/potential.json").read_text())["cases"]
        groups=sorted({(c["process"],c["frequency_hz"]) for c in cases})
        if not groups:raise ValueError("No native potential fixture groups")
        print("potential_matrix="+json.dumps(dict(include=[dict(process=p,frequency=f,label=f"{p} {f/1e9:g} GHz") for p,f in groups]),separators=(",",":")))
        return
    if args.group=="potential":
        if args.process is None or args.frequency is None:parser.error("Potential group requires --process and --frequency")
        os.environ["REASITIC_POTENTIAL_PROCESS"]=args.process
        os.environ["REASITIC_POTENTIAL_FREQUENCY"]=str(args.frequency)
    sys.path.insert(0,str(ROOT/"src"))
    discovered=unittest.defaultTestLoader.discover(str(ROOT/"tests"))
    tests=[t for t in flatten(discovered) if (t.__class__.__module__=="test_potential")== (args.group=="potential")]
    if not tests:raise ValueError("No Python checks selected")
    print(f"Running {len(tests)} Python checks in {args.group}",flush=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=="__main__":main()

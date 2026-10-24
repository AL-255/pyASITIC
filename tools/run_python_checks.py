"""Run CI Python groups without reducing local unittest discovery coverage."""
import argparse
from collections import Counter
import hashlib
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


def discover(group):
    sys.path.insert(0,str(ROOT/'src'))
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    tests=sorted((t for t in flatten(suite) if (t.__class__.__module__=='test_potential')==(group=='potential')),key=lambda t:t.id())
    if not tests or any(isinstance(t,unittest.loader._FailedTest)for t in tests):raise ValueError('Missing tests or failed module discovery')
    return tests


def select(tests,shard=None,shards=None):
    if shard is None and shards is None:return tests
    if shard is None or shards is None or not 1<=shard<=shards:raise ValueError('Shards require 1 <= shard <= shards')
    return tests[shard-1::shards]


def ids_digest(tests):
    return hashlib.sha256(('\n'.join(t.id()for t in tests)+'\n').encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group",choices=("plan","core","potential"));parser.add_argument("--process");parser.add_argument("--frequency",type=float)
    parser.add_argument('--shard',type=int);parser.add_argument('--shards',type=int)
    parser.add_argument('--ids-sha');parser.add_argument('--list',action='store_true')
    args=parser.parse_args()
    if args.group!='core' and any(v is not None for v in (args.shard,args.shards,args.ids_sha)):parser.error('Sharding applies only to core checks')
    if args.group=="plan":
        cases=json.loads((ROOT/"tests/fixtures/potential.json").read_text())["cases"]
        groups=sorted({(c["process"],c["frequency_hz"]) for c in cases})
        if not groups:raise ValueError("No native potential fixture groups")
        print("potential_matrix="+json.dumps(dict(include=[dict(process=p,frequency=f,label=f"{p} {f/1e9:g} GHz") for p,f in groups]),separators=(",",":")))
        core=discover('core');parts=[select(core,i,4)for i in range(1,5)]
        expected=Counter(t.id()for t in core);actual=Counter(t.id()for part in parts for t in part)
        if any(n!=1 for n in expected.values())or expected!=actual or any(not part for part in parts):raise ValueError('Core shards must partition every discovered test exactly once')
        print('core_matrix='+json.dumps(dict(include=[dict(shard=i,shards=4,ids_sha=ids_digest(part))for i,part in enumerate(parts,1)]),separators=(',',':')))
        return
    if args.group=="potential":
        if args.process is None or args.frequency is None:parser.error("Potential group requires --process and --frequency")
        os.environ["REASITIC_POTENTIAL_PROCESS"]=args.process
        os.environ["REASITIC_POTENTIAL_FREQUENCY"]=str(args.frequency)
    tests=select(discover(args.group),args.shard,args.shards)
    if not tests:raise ValueError("No Python checks selected")
    if args.ids_sha is not None and ids_digest(tests)!=args.ids_sha:raise ValueError('Selected test IDs differ from the validated build plan')
    if args.list:
        print('\n'.join(t.id()for t in tests));return
    label=f'{args.group} shard {args.shard}/{args.shards}'if args.shard is not None else args.group
    print(f"Running {len(tests)} Python checks in {label}; test IDs SHA256 {ids_digest(tests)}",flush=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=="__main__":main()

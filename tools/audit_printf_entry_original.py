"""Strict public output calls from entry through the real vfprintf/formatter."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import audit_vfprintf_whole_original as parent
from printf_archive import read_fixture
from printf_fixture import expand_state
from reasitic.printf_entry_storage import PrintfEntryStorage


def engine(fixture,state):
    m,file=parent.file_engine(fixture,state);state=expand_state(fixture,state)
    return m,PrintfEntryStorage(file,shr1_af=fixture['integer_cpu']['shr1_af'],xstate=bytes.fromhex(state['xstate']))


def compare(fixture,case):return parent.compare(fixture,case,storage_factory=engine,call_kind='entry')


def run(fixture,*,shard=1,shards=1):return parent.run(fixture,shard=shard,shards=shards,storage_factory=engine,call_kind='entry')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_entry_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();report=run(read_fixture(args.fixture),shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k not in('results','case_indices')});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

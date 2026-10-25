"""Strict complete dispatcher/kill/VDSO targets, with no kernel output input."""
import argparse,collections,gzip,json
from pathlib import Path
from audit_dispatch_storage_original import compare as dispatch

ROOT=Path(__file__).resolve().parents[1]


def compare(fixture,case):return dispatch(fixture,case,kill=True)


def run(fixture):
    results=[compare(fixture,c)for c in fixture['cases']]
    report=dict(cases=len(results),cases_without_dispatch=sum(not c['dispatch_calls']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('operations_checked','words_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/kill_storage_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

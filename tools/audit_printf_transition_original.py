"""Strict real printf continuation over disjoint complete native histories."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_command_transition_original import compare
from audit_printf_file_original import selected_indices

COUNTERS=('events_checked','buffers_checked','buffer_bytes_checked','heap_words_checked','component_words_checked','points_checked','point_words_checked','unknown_bytes','console_calls_checked','calendar_calls_checked','files_checked','file_bytes_checked','faults_checked','stdin_positions_checked','printf_calls_checked','printf_registers_checked','point_bytes_checked','component_bytes_checked')


def run(fixture,*,shard=1,shards=1):
    indices=selected_indices(len(fixture['cases']),shard,shards);results=[]
    for i in indices:
        case=fixture['cases'][i];r=compare(fixture,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r.get('printf_calls_checked',0)} continuing printf calls, {len(r['differences'])} differences",flush=True)
    report=dict(total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),native_terminal_counts=dict(collections.Counter(fixture['cases'][i]['signal']for i in indices)),differences=sum(len(r['differences'])for r in results),results=results)
    for key in COUNTERS:report[key]=sum(r.get(key,0)for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_transition_original.json.gz');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));report=run(f,shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k not in('results','case_indices')});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

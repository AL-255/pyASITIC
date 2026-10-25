"""Strict formatter-prefix and whole-formatter audits; conversions stay required."""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_printf_file_original import engine as file_engine,compare as compare_calls,selected_indices
from printf_fixture import expand_state
from printf_archive import read_fixture
from reasitic.printf_format import PrintfFormat


def engine(fixture,state):
    m,file=file_engine(fixture,state);state=expand_state(fixture,state)
    return m,PrintfFormat(file,shr1_af=fixture['integer_cpu']['shr1_af'],xstate=bytes.fromhex(state['xstate']))


def compare(fixture,case,*,prefix=False):
    calls=[];missing=[]
    for i,call in enumerate(case['printf_calls']):
        if prefix:
            if 'initial_write'not in call:missing.append(dict(kind='format-missing-initial-write',call=i));continue
            point=call['initial_write'];end=point['children_start']
            if not 0<=end<=len(call['children']):raise ValueError('Invalid initial-write helper boundary')
            calls.append(dict(kind='before_initial_write',before=call['before'],after=point['before'],children=call['children'][:end]))
        else:calls.append(dict(call,kind='format'))
    result=compare_calls(fixture,dict(case,printf_calls=calls),storage_factory=engine);result['calls_required']=len(case['printf_calls']);result['differences'].extend(missing);return result


def run(fixture,*,prefix=False,shard=1,shards=1):
    indices=selected_indices(len(fixture['cases']),shard,shards);results=[]
    for i in indices:
        c=fixture['cases'][i];r=compare(fixture,c,prefix=prefix);results.append(r);print(f"{c['label']}/{c['cache_mode']}: {r['calls_checked']} {'prefixes'if prefix else'formatters'}, {len(r['differences'])} differences",flush=True)
    report=dict(scope='prefix'if prefix else'complete',total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),cases_without_calls=sum(not fixture['cases'][i]['printf_calls']for i in indices),native_terminal_counts=dict(collections.Counter(fixture['cases'][i]['signal']for i in indices)),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_required','calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_format_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--prefix',action='store_true');p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();f=read_fixture(args.fixture);report=run(f,prefix=args.prefix,shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

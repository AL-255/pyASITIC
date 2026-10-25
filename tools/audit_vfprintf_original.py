"""Native caller phases around the still-required vfprintf formatter child.

Formatter return is an independent suffix-component input only. This audit
does not initialize continuing execution from it or implement formatting.
Every formatter boundary and all middle-child targets remain in the corpus.
"""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_printf_file_original import compare as compare_phase,engine as file_engine,selected_indices
from printf_fixture import expand_state
from printf_archive import read_fixture
from reasitic.vfprintf_storage import VfprintfStorage


def engine(fixture,state):
    m,storage=file_engine(fixture,state);return m,VfprintfStorage(storage)


def phases(fixture,case):
    result=[];missing=[];middle=0
    for index,call in enumerate(case['printf_calls']):
        if 'after'not in call or'formatter'not in call or'after'not in call['formatter']:
            missing.append(dict(kind='vfprintf-missing-boundary',call=index));continue
        fmt=call['formatter'];start,end=(fmt[k]for k in ('children_start','children_end'))
        if not 0<=start<=end<=len(call['children']):raise ValueError('Invalid formatter child boundary indices')
        middle+=end-start;context=expand_state(fixture,call['before'])
        for name,a,b,children in (
            ('before_formatter',context,expand_state(fixture,fmt['before']),call['children'][:start]),
            ('after_formatter',dict(context,**expand_state(fixture,fmt['after'])),expand_state(fixture,call['after']),call['children'][end:]),
        ):result.append(dict(kind=name,before=a,after=b,children=children,parent_call=index))
    return result,missing,middle


def compare(fixture,case):
    calls,missing,middle=phases(fixture,case)
    result=compare_phase(fixture,dict(case,printf_calls=calls),storage_factory=engine)
    result['differences'].extend(missing);result['parent_calls']=len(case['printf_calls']);result['formatter_calls_pending']=len(case['printf_calls']);result['formatter_children_pending']=middle
    return result


def run(fixture,*,shard=1,shards=1):
    indices=selected_indices(len(fixture['cases']),shard,shards);results=[]
    for i in indices:
        c=fixture['cases'][i];r=compare(fixture,c);results.append(r);print(f"{c['label']}/{c['cache_mode']}: {r['calls_checked']} caller phases, {len(r['differences'])} differences; {r['formatter_calls_pending']} formatter calls still required",flush=True)
    report=dict(total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),cases_without_calls=sum(not fixture['cases'][i]['printf_calls']for i in indices),native_terminal_counts=dict(collections.Counter(fixture['cases'][i]['signal']for i in indices)),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('parent_calls','formatter_calls_pending','formatter_children_pending','calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/vfprintf_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();f=read_fixture(args.fixture);report=run(f,shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

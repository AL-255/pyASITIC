"""Whole vfprintf execution from parent entry, with every inner state an assertion.

The observer checks produced memory/heap/GP/FP at formatter boundaries. Its
comparison adapter returns only already-produced source registers and uses
the same live Memory/Heap; it never initializes execution from a boundary.
"""
import argparse,collections,json,sys,weakref
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_printf_file_original import compare as compare_state,engine as file_engine,selected_indices
from printf_fixture import expand_state
from printf_archive import read_fixture
from reasitic.vfprintf_storage import VfprintfStorage

COUNTERS=('calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked')


def engine(fixture,state):
    m,file=file_engine(fixture,state);state=expand_state(fixture,state)
    return m,VfprintfStorage(file,shr1_af=fixture['integer_cpu']['shr1_af'],xstate=bytes.fromhex(state['xstate']))


def compare(fixture,case,*,storage_factory=None,call_kind='vfprintf'):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],parent_calls_required=len(case['printf_calls']),boundary_states_checked=0,boundary_words_checked=0,boundary_registers_checked=0,boundary_fp_bytes_checked=0,differences=[],**dict.fromkeys(COUNTERS,0))
    for index,call in enumerate(case['printf_calls']):
        boundary=call.get('formatter',{});observations=[]
        if 'before'not in boundary or'after'not in boundary:result['differences'].append(dict(kind='vfprintf-whole-missing-boundary',call=index))
        start,end=(boundary.get(key)for key in('children_start','children_end'))
        if isinstance(start,bool)or isinstance(end,bool)or not isinstance(start,int)or not isinstance(end,int)or not 0<=start<=end<=len(call['children']):raise ValueError('Invalid whole-parent formatter child boundary indices')
        def factory(f,a):
            m,storage=(storage_factory or engine)(f,a);reference=weakref.proxy(storage)
            def observe(name,registers,xstate):
                observations.append(name);key={'formatter-before':'before','formatter-after':'after'}[name]
                if key not in boundary:return
                adapter=SimpleNamespace(heap=reference.heap,children=[],xstate=xstate,boundary=lambda _incoming:dict(registers))
                # Same live source state, read-only assertions. No boundary
                # target is returned to source execution by this adapter.
                record=dict(kind='boundary',before=a,after=boundary[key],children=[])
                checked=compare_state(f,dict(case,printf_calls=[record]),storage_factory=lambda _f,_a:(m,adapter))
                result['boundary_states_checked']+=checked['calls_checked']
                for source,target in(('words_checked','boundary_words_checked'),('registers_checked','boundary_registers_checked'),('fp_bytes_checked','boundary_fp_bytes_checked')):result[target]+=checked[source]
                result['differences'].extend(dict(d,call=index,boundary=name)for d in checked['differences'])
                if name=='formatter-before':actual=reference.formatter_children_start;expected=start
                else:actual=reference.formatter_children_end;expected=end
                if actual!=expected:result['differences'].append(dict(kind='vfprintf-whole-child-boundary',call=index,boundary=name,actual=actual,original=expected))
            storage.observer=observe;return m,storage
        checked=compare_state(fixture,dict(case,printf_calls=[dict(call,kind=call_kind)]),storage_factory=factory)
        for key in COUNTERS:result[key]+=checked[key]
        result['differences'].extend(dict(d,call=index)for d in checked['differences'])
        if checked['calls_checked']and observations!=['formatter-before','formatter-after']:result['differences'].append(dict(kind='vfprintf-whole-observer-boundaries',call=index,actual=observations))
    return result


def run(fixture,*,shard=1,shards=1,storage_factory=None,call_kind='vfprintf'):
    indices=selected_indices(len(fixture['cases']),shard,shards);results=[]
    for i in indices:
        c=fixture['cases'][i];r=compare(fixture,c,storage_factory=storage_factory,call_kind=call_kind);results.append(r);print(f"{c['label']}/{c['cache_mode']}: {r['calls_checked']} whole parents, {r['boundary_states_checked']} source boundary assertions, {len(r['differences'])} differences",flush=True)
    report=dict(total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),cases_without_calls=sum(not fixture['cases'][i]['printf_calls']for i in indices),native_terminal_counts=dict(collections.Counter(fixture['cases'][i]['signal']for i in indices)),results=results,differences=sum(len(r['differences'])for r in results))
    for key in('parent_calls_required',*COUNTERS,'boundary_states_checked','boundary_words_checked','boundary_registers_checked','boundary_fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/vfprintf_whole_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();report=run(read_fixture(args.fixture),shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k not in('results','case_indices')});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

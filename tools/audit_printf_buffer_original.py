"""Complete printf buffer write regions, registers, FP and child boundaries."""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from printf_fixture import data,memory_for,expand_state
from reasitic.printf_buffer import PrintfBuffer
from printf_archive import read_fixture


def engine(fixture,state):
    state=expand_state(fixture,state);m=memory_for(fixture,state);base=m.u32(next(x['address']for x in state['maps']if x['name'].endswith('/libc.so.6')))
    return m,PrintfBuffer(m,libc_base=base,shr1_af=fixture['integer_cpu']['shr1_af'])


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,children_checked=0,child_registers_checked=0,differences=[])
    for index,call in enumerate(case['printf_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='printf-missing-return',call=index));continue
        a,b=(expand_state(fixture,call[p])for p in ('before','after'))
        try:m,storage=engine(fixture,a);registers=storage.write(a['registers'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='printf-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        def check(left,right,kind,unit=4,address=0):
            if left==right:return
            if len(left)!=len(right):result['differences'].append(dict(kind=kind+'-size',call=index))
            for offset in range(0,len(right),unit):
                if left[offset:offset+unit]!=right[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,address=address+offset,actual=left[offset:offset+unit].hex(),original=right[offset:offset+unit].hex()))
        owners=lambda s:[(r['address'],r['size'])for r in s['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='printf-region-owners',call=index))
        for r in b['regions']:
            expected=data(fixture,r)
            try:actual=m.read(r['address'],len(expected))
            except ValueError as error:result['differences'].append(dict(kind='printf-memory-unavailable',call=index,address=r['address'],reason=str(error)))
            else:check(actual,expected,'printf-memory-word',address=r['address'])
            result['words_checked']+=(len(expected)+3)//4
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='printf-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='printf-register',call=index,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'printf-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        if len(storage.children)!=len(call['children']):result['differences'].append(dict(kind='printf-child-count',call=index,actual=len(storage.children),original=len(call['children'])))
        for child,(actual,expected)in enumerate(zip(storage.children,call['children'])):
            result['children_checked']+=1
            if actual['kind']!=expected['kind']:result['differences'].append(dict(kind='printf-child-kind',call=index,child=child))
            for phase in ('before','after'):
                if set(actual[phase])!=set(expected[phase]):result['differences'].append(dict(kind='printf-child-register-set',call=index,child=child,phase=phase))
                for name,value in expected[phase].items():
                    if actual[phase].get(name)!=value:result['differences'].append(dict(kind='printf-child-register',call=index,child=child,phase=phase,name=name,actual=actual[phase].get(name),original=value))
                    result['child_registers_checked']+=1
    return result


def selected_indices(count,shard=1,shards=1):
    if isinstance(shard,bool)or isinstance(shards,bool)or not isinstance(shard,int)or not isinstance(shards,int)or not 1<=shard<=shards<=count:raise ValueError('Require 1 <= shard <= shards <= histories')
    return list(range(shard-1,count,shards))


def run(fixture,*,shard=1,shards=1):
    indices=selected_indices(len(fixture['cases']),shard,shards);cases=[fixture['cases'][i]for i in indices];results=[]
    for case in cases:
        r=compare(fixture,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['calls_checked']} buffer writes, {len(r['differences'])} differences",flush=True)
    report=dict(total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),cases_without_calls=sum(not c['printf_calls']for c in cases),native_terminal_counts=dict(collections.Counter(c['signal']for c in cases)),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_buffer_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();f=read_fixture(args.fixture);report=run(f,shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

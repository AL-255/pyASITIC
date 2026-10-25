"""Complete native fflush return regions, registers, FP and write effects."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from getline_fixture import expand_state
from reasitic.flush_storage import FlushStorage
from reasitic.plt_fixup_storage import PltFixup


def engine(fixture,state):
    state=expand_state(fixture,state);m=memory_for(fixture,state);base=m.u32(next(x['address']for x in state['maps']if x['name'].endswith('/libc.so.6')))
    loader=PltFixup(m,state['loader_base'],tls_base=state['tls_base'])
    return m,FlushStorage(m,loader,state,libc_base=base,tls_base=state['tls_base'])


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,writes_checked=0,write_bytes_checked=0,differences=[])
    for index,call in enumerate(case['flush_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='flush-missing-return',call=index));continue
        a,b=(expand_state(fixture,call[p])for p in ('before','after'))
        try:m,storage=engine(fixture,a);registers=storage.flush(a['registers'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='flush-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        def check(left,right,kind,unit=4,address=0):
            if left==right:return
            if len(left)!=len(right):result['differences'].append(dict(kind=kind+'-size',call=index))
            for offset in range(0,len(right),unit):
                if left[offset:offset+unit]!=right[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,address=address+offset,actual=left[offset:offset+unit].hex(),original=right[offset:offset+unit].hex()))
        owners=lambda s:[(r['address'],r['size'])for r in s['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='flush-region-owners',call=index))
        for r in b['regions']:
            expected=data(fixture,r)
            try:actual=m.read(r['address'],len(expected))
            except ValueError as error:result['differences'].append(dict(kind='flush-memory-unavailable',call=index,address=r['address'],reason=str(error)))
            else:check(actual,expected,'flush-memory-word',address=r['address'])
            result['words_checked']+=(len(expected)+3)//4
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='flush-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='flush-register',call=index,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'flush-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        if len(storage.writes)!=len(call['writes']):result['differences'].append(dict(kind='flush-write-count',call=index,actual=len(storage.writes),original=len(call['writes'])))
        for actual,expected in zip(storage.writes,call['writes']):
            if actual!=expected:result['differences'].append(dict(kind='flush-write',call=index,actual=actual,original=expected))
            result['writes_checked']+=1;result['write_bytes_checked']+=expected['count']
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/flush_storage_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in f['cases']:
        r=compare(f,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['calls_checked']} flushes, {len(r['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_calls=sum(not c['flush_calls']for c in f['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in f['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked','writes_checked','write_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

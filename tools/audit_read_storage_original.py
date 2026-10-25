"""Complete independent stdin read memory/register/FP/offset comparisons."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from reasitic.read_storage import ReadStorage


def engine(fixture,state):
    m=memory_for(fixture,state);libc=m.u32(next(x['address']for x in state['maps']if x['name'].endswith('/libc.so.6')))
    return m,ReadStorage(m,libc_base=libc,tls_base=state['tls_base'])


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,positions_checked=0,bytes_read=0,differences=[])
    for index,call in enumerate(case['read_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='read-missing-return',call=index));continue
        a,b=call['before'],call['after'];external=a['external_stdin']
        try:m,storage=engine(fixture,a);actual=storage.read(a['registers'],bytes.fromhex(external['data']),external['position'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='read-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1;result['bytes_read']+=len(actual['data'])
        def check(left,right,kind,unit=4,address=0):
            if len(left)!=len(right):result['differences'].append(dict(kind=kind+'-size',call=index))
            for offset in range(0,len(right),unit):
                if left[offset:offset+unit]!=right[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,address=address+offset,actual=left[offset:offset+unit].hex(),original=right[offset:offset+unit].hex()))
        owners=lambda state:[(r['address'],r['size'])for r in state['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='read-region-owners',call=index))
        for region in b['regions']:
            expected=data(fixture,region)
            try:raw=m.read(region['address'],len(expected))
            except ValueError as error:result['differences'].append(dict(kind='read-memory-unavailable',call=index,address=region['address'],reason=str(error)))
            else:check(raw,expected,'read-memory-word',address=region['address'])
            result['words_checked']+=(len(expected)+3)//4
        registers=actual['registers']
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='read-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='read-register',call=index,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'read-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        if actual['position']!=b['position']:result['differences'].append(dict(kind='read-position',call=index,actual=actual['position'],original=b['position']))
        result['positions_checked']+=1
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/read_storage_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in f['cases']:
        r=compare(f,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['calls_checked']} reads, {len(r['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_read=sum(not c['read_calls']for c in f['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in f['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked','positions_checked','bytes_read'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

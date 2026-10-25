"""Every internal getline search/copy call against complete native targets."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from reasitic.getline_bytes import GetlineBytes
from getline_fixture import expand_state,expand_case


def engine(fixture,state):
    state=expand_state(fixture,state)
    m=memory_for(fixture,state);libc=m.u32(next(x['address']for x in state['maps']if x['name'].endswith('/libc.so.6')))
    return m,GetlineBytes(m,libc_base=libc,shr1_af=fixture['integer_cpu']['shr1_af'])


def compare(fixture,case):
    case=expand_case(fixture,case)
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,differences=[])
    for index,call in enumerate(case['byte_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='getline-bytes-missing-return',call=index));continue
        a,b=call['before'],call['after'];kind=call['kind']
        try:m,storage=engine(fixture,a);registers=getattr(storage,kind)(a['registers'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='getline-bytes-runtime',call=index,operation=kind,reason=str(error)));continue
        result['calls_checked']+=1
        def check(left,right,category,unit=4,address=0):
            if left==right:return
            if len(left)!=len(right):result['differences'].append(dict(kind=category+'-size',call=index))
            for offset in range(0,len(right),unit):
                if left[offset:offset+unit]!=right[offset:offset+unit]:result['differences'].append(dict(kind=category,call=index,operation=kind,address=address+offset,actual=left[offset:offset+unit].hex(),original=right[offset:offset+unit].hex()))
        owners=lambda state:[(r['address'],r['size'])for r in state['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='getline-bytes-region-owners',call=index))
        for region in b['regions']:
            expected=data(fixture,region)
            try:raw=m.read(region['address'],len(expected))
            except ValueError as error:result['differences'].append(dict(kind='getline-bytes-memory-unavailable',call=index,address=region['address'],reason=str(error)))
            else:check(raw,expected,'getline-bytes-memory-word',address=region['address'])
            result['words_checked']+=(len(expected)+3)//4
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='getline-bytes-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='getline-bytes-register',call=index,operation=kind,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'getline-bytes-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/getline_bytes_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in f['cases']:
        r=compare(f,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['calls_checked']} calls, {len(r['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_calls=sum(not c['byte_calls']for c in f['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in f['cases'])),operations=dict(collections.Counter(x['kind']for c in f['cases']for x in c['byte_calls'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

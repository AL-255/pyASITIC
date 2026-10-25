"""Independent ELF lookup entry inputs -> complete native return assertions."""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.loader_lookup_storage import LoaderLookup


def data(fixture,region):
    if 'pages'in region:
        pages=[]
        for key in region['pages']:
            page=bytes.fromhex(fixture['loader_pages'][key])
            if hashlib.sha256(page).hexdigest()!=key:raise ValueError('Invalid loader page content')
            pages.append(page)
        raw=b''.join(pages)
    else:raw=bytes.fromhex(fixture['loader_regions'][region['sha256']])
    if len(raw)!=region['size']or hashlib.sha256(raw).hexdigest()!=region['sha256']:raise ValueError('Invalid loader region content')
    return raw


def memory_for(fixture,before):
    # Preserve the exact region union, including gaps, while avoiding a sort
    # of thousands of overlapping ELF owners on every guest memory access.
    ranges=[]
    for start,end in sorted((r['address'],r['address']+r['size'])for r in before['regions']):
        if ranges and start<=ranges[-1][1]:ranges[-1][1]=max(ranges[-1][1],end)
        else:ranges.append([start,end])
    memory=Memory(AddressSpace([dict(start=start,end=end)for start,end in ranges]))
    for r in before['regions']:memory.write(r['address'],data(fixture,r))
    return memory


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,differences=[])
    for index,call in enumerate(case['lookup_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='loader-lookup-missing-return',index=index));continue
        a,b=call['before'],call['after'];memory=memory_for(fixture,a)
        try:actual=LoaderLookup(memory,a['loader_base']).lookup(a['registers'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='loader-lookup-runtime',index=index,reason=str(error)));continue
        result['calls_checked']+=1
        owners=lambda records:[(r['address'],r['size'])for r in records]
        if owners(a['regions'])!=owners(b['regions']):result['differences'].append(dict(kind='loader-lookup-region-owners',index=index))
        def check(actual,expected,kind,unit=4,address=0):
            if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',index=index,actual=len(actual),original=len(expected)))
            for offset in range(0,len(expected),unit):
                if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,index=index,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
        for region in b['regions']:
            expected=data(fixture,region);address=region['address']
            check(memory.read(address,len(expected)),expected,'loader-lookup-memory-word',address=address);result['words_checked']+=(len(expected)+3)//4
        if set(actual['registers'])!=set(b['registers']):result['differences'].append(dict(kind='loader-lookup-register-set',index=index))
        for name,value in b['registers'].items():
            if actual['registers'].get(name)!=value:result['differences'].append(dict(kind='loader-lookup-register',index=index,name=name,actual=actual['registers'].get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'loader-lookup-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
    if case['lookup_pending']:result['differences'].append(dict(kind='loader-lookup-pending',count=case['lookup_pending']))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/loader_lookup_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        result=compare(fixture,case);results.append(result);print(f"{case['label']}/{case['cache_mode']}: {result['calls_checked']} calls, {len(result['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_calls=sum(not c['lookup_calls']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

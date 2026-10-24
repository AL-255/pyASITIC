"""Independent pre-delivery CPU state -> every native signal-frame byte."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.signal_frame import deliver,legacy_x87


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],native_terminal_signal=case['signal'],deliveries_checked=0,stack_words_checked=0,registers_checked=0,xstate_bytes_checked=0,legacy_bytes_checked=0,differences=[])
    for index,arrival in enumerate(case['arrivals']):
        before,after=arrival['before'],arrival['after'];stack=before['stack'];address=stack['address'];data=bytes.fromhex(stack['data'])
        memory=Memory(AddressSpace([dict(start=address,end=address+len(data))]));memory.write(address,data)
        xstate=bytes.fromhex(before['xstate'])
        try:actual=deliver(memory,before['registers'],xstate,number=before['number'],action=before['action'],mask=before['mask'],thread=before['thread'],cpu=fixture['signal_frame_provenance']['cpu'],vdso=before['vdso'])
        except (ValueError,NotImplementedError)as error:
            result['differences'].append(dict(kind='signal-runtime',index=index,reason=str(error)));continue
        result['deliveries_checked']+=1
        def check(actual,expected,kind,unit=4,address=0):
            if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',index=index,actual=len(actual),original=len(expected)))
            for offset in range(0,len(expected),unit):
                if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,index=index,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
        if after['stack']['address']!=address:result['differences'].append(dict(kind='signal-stack-owner',index=index))
        check(memory.read(address,len(data)),bytes.fromhex(after['stack']['data']),'signal-stack-word',address=address)
        result['stack_words_checked']+=len(after['stack']['data'])//8
        if set(actual['registers'])!=set(after['registers']):result['differences'].append(dict(kind='signal-register-set',index=index))
        for name,value in after['registers'].items():
            if actual['registers'].get(name)!=value:result['differences'].append(dict(kind='signal-register',index=index,name=name,actual=actual['registers'].get(name),original=value))
            result['registers_checked']+=1
        if actual['mask']!=after['mask']:result['differences'].append(dict(kind='signal-mask',index=index,actual=actual['mask'],original=after['mask']))
        check(actual['xstate'],bytes.fromhex(after['xstate']),'signal-xstate-byte',unit=1);result['xstate_bytes_checked']+=len(after['xstate'])//2
        check(legacy_x87(xstate,before['registers']),bytes.fromhex(before['fpregs']),'signal-legacy-byte',unit=1);result['legacy_bytes_checked']+=len(before['fpregs'])//2
    if case['signal_pending']is not None:result['differences'].append(dict(kind='signal-delivery-not-observed'))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/signal_frames_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        result=compare(fixture,case);results.append(result)
        print(f"{case['label']}/{case['cache_mode']}: {result['deliveries_checked']} deliveries, {len(result['differences'])} differences; observed terminal signal {case['signal']}",flush=True)
    report=dict(cases=len(results),cases_without_delivery=sum(not c['arrivals']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('deliveries_checked','stack_words_checked','registers_checked','xstate_bytes_checked','legacy_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

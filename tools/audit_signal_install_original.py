"""Independent BSD signal entry state -> complete native return state."""
import argparse,collections,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.signal_install_storage import startup,bsd_signal


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,stack_words_checked=0,registers_checked=0,fp_bytes_checked=0,differences=[])
    for index,call in enumerate(case['bsd_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='signal-install-missing-return',index=index));continue
        a,b=call['before'],call['after'];stack=a['stack'];address=stack['address'];data=bytes.fromhex(stack['data'])
        memory=Memory(AddressSpace([dict(start=address,end=address+len(data))]));memory.write(address,data)
        try:
            boot=startup(memory,a['main_frame'])
            actual=bsd_signal(memory,a['registers'],libc_base=a['libc_base'],guard=boot['guard'],intr_mask=a['intr_mask'],old_action=a['old_action'],has_vdso=bool(boot['auxv'].get(32)))
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='signal-install-runtime',index=index,reason=str(error)));continue
        result['calls_checked']+=1
        def check(actual,expected,kind,unit=4,address=0):
            if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',index=index,actual=len(actual),original=len(expected)))
            for offset in range(0,len(expected),unit):
                if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,index=index,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
        if b['stack']['address']!=address:result['differences'].append(dict(kind='signal-install-stack-owner',index=index))
        check(memory.read(address,len(data)),bytes.fromhex(b['stack']['data']),'signal-install-stack-word',address=address)
        result['stack_words_checked']+=len(b['stack']['data'])//8
        if set(actual['registers'])!=set(b['registers']):result['differences'].append(dict(kind='signal-install-register-set',index=index))
        for name,value in b['registers'].items():
            if actual['registers'].get(name)!=value:result['differences'].append(dict(kind='signal-install-register',index=index,name=name,actual=actual['registers'].get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'signal-install-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        # The kernel input action remains in the native local stack at return.
        offset=a['registers']['esp']-652+20-b['stack']['address'];record=bytes.fromhex(b['stack']['data'])[offset:offset+20]
        handler,flags,restorer,mask=struct.unpack('<IIIQ',record)
        if actual['action']!=dict(handler=handler,flags=flags,restorer=restorer,mask=mask):result['differences'].append(dict(kind='signal-install-action',index=index))
    if case['bsd_pending']:result['differences'].append(dict(kind='signal-install-pending',count=case['bsd_pending']))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/signal_install_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        result=compare(fixture,case);results.append(result);print(f"{case['label']}/{case['cache_mode']}: {result['calls_checked']} calls, {len(result['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_calls=sum(not c['bsd_calls']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','stack_words_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

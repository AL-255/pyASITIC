"""Strict independent dispatcher caller ABI comparisons, not replay seeds."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from reasitic.command_storage import Characters
from reasitic.dispatch_storage import DispatchStorage
from reasitic.plt_fixup_storage import PltFixup


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],operations_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,differences=[])
    for call_index,call in enumerate(case['dispatch_calls']):
        context=call['entry']
        for phase,start,end,method in (('history','entry','history','history'),('normalization','history','parse','before_parser'),('quit','parsed','kill','quit_binding')):
            if start not in call or end not in call:result['differences'].append(dict(kind='dispatch-missing-boundary',call=call_index,phase=phase));continue
            a,b=call[start],call[end];m=memory_for(fixture,a)
            storage=DispatchStorage(m,Characters(context['characters']),PltFixup(m,context['loader_base'],tls_base=context['tls_base']),context)
            try:registers=getattr(storage,method)(a['registers'])
            except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='dispatch-runtime',phase=phase,call=call_index,reason=str(error)));continue
            result['operations_checked']+=1
            def check(actual,expected,kind,unit=4,address=0):
                if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',phase=phase,call=call_index))
                for offset in range(0,len(expected),unit):
                    if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,phase=phase,call=call_index,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
            owners=lambda state:[(r['address'],r['size'])for r in state['regions']]
            if owners(a)!=owners(b):result['differences'].append(dict(kind='dispatch-region-owners',phase=phase,call=call_index))
            for r in b['regions']:
                original=data(fixture,r);check(m.read(r['address'],len(original)),original,'dispatch-memory-word',address=r['address']);result['words_checked']+=(len(original)+3)//4
            if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='dispatch-register-set',phase=phase,call=call_index))
            for key,value in b['registers'].items():
                if registers.get(key)!=value:result['differences'].append(dict(kind='dispatch-register',phase=phase,call=call_index,name=key,actual=registers.get(key),original=value))
                result['registers_checked']+=1
            check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'dispatch-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/dispatch_storage_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in f['cases']:
        r=compare(f,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['operations_checked']} operations, {len(r['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_dispatch=sum(not c['dispatch_calls']for c in f['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in f['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('operations_checked','words_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

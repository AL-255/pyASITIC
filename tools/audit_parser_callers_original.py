"""Strict complete parser caller/prologue and every comparison PUSH target."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from capture_parser_callers_original import expand_point
from reasitic.parser_callers import parser_to_tokenizer,tokenizer_return_to_catalog,catalog_to_comparison,comparison_argument
from audit_dispatch_storage_original import compare as dispatch


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],operations_checked=0,comparisons_checked=0,words_checked=0,bytes_checked=0,registers_checked=0,fp_bytes_checked=0,differences=[])
    expanded=dict(case,dispatch_calls=[{key:expand_point(fixture,point)for key,point in call.items()if key!='comparisons'}for call in case['dispatch_calls']])
    prior=dispatch(fixture,expanded)
    for key in('operations_checked','words_checked','registers_checked','fp_bytes_checked'):result[key]+=prior[key]
    result['differences'].extend(prior['differences'])
    result['bytes_checked']+=sum(r['size']for call in expanded['dispatch_calls']for phase in('history','parse','kill')for r in call[phase]['regions'])
    for call_index,call in enumerate(case['dispatch_calls']):
        operations=[('parser','parse','tokenizer',parser_to_tokenizer),('tokenized','tokenized','catalog',tokenizer_return_to_catalog),('catalog','catalog','comparison_ready',catalog_to_comparison)]
        entries=[]
        for phase,start,end,function in operations:
            if start not in call or end not in call:result['differences'].append(dict(kind='parser-missing-boundary',call=call_index,phase=phase));continue
            entries.append((phase,call[start],call[end],function))
        for i,pair in enumerate(call.get('comparisons',())):
            if 'after'not in pair:result['differences'].append(dict(kind='parser-missing-comparison-return',call=call_index,index=i));continue
            entries.append(('comparison.'+str(i),pair['before'],pair['after'],comparison_argument))
        for phase,start,end,function in entries:
            a,b=expand_point(fixture,start),expand_point(fixture,end);m=memory_for(fixture,a)
            try:registers=function(m,a['registers'])
            except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='parser-runtime',call=call_index,phase=phase,reason=str(error)));continue
            result['operations_checked']+=1
            if phase.startswith('comparison.'):result['comparisons_checked']+=1
            if[(r['address'],r['size'])for r in a['regions']]!=[(r['address'],r['size'])for r in b['regions']]:result['differences'].append(dict(kind='parser-region-owners',call=call_index,phase=phase))
            def check(actual,expected,kind,*,address=0,unit=4):
                if actual==expected:return
                if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',call=call_index,phase=phase))
                for offset in range(0,len(expected),unit):
                    if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=call_index,phase=phase,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
            for r in b['regions']:
                native=data(fixture,r);check(m.read(r['address'],len(native)),native,'parser-memory-word',address=r['address']);result['words_checked']+=(len(native)+3)//4;result['bytes_checked']+=len(native)
            if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='parser-register-set',call=call_index,phase=phase))
            for name,value in b['registers'].items():
                result['registers_checked']+=1
                if registers.get(name)!=value:result['differences'].append(dict(kind='parser-register',call=call_index,phase=phase,name=name,actual=registers.get(name),original=value))
            check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'parser-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
    return result


def run(fixture):
    results=[compare(fixture,c)for c in fixture['cases']]
    report=dict(cases=len(results),cases_without_dispatch=sum(not c['dispatch_calls']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('operations_checked','comparisons_checked','words_checked','bytes_checked','registers_checked','fp_bytes_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/parser_callers_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

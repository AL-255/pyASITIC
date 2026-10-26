"""Complete prior histories plus real CRT/string/frame/mutex boundaries."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import audit_shunt_exit_original as parent
from audit_loader_lookup_original import data
from exit_fixture import read_fixture,expand_case

CRT_TOTALS=('native_crt_calls','crt_calls_checked','crt_phases_checked','crt_words_checked','crt_heap_boundaries_checked','crt_argument_words_checked','crt_values_checked','crt_unknown_bytes')


def phase(fixture,entry,expected,engine,record,identity,counts,differences):
    temporary=dict.fromkeys(parent.EXIT_TOTALS,0);found=[]
    parent.phase(fixture,entry,expected,engine,record,identity,temporary,found)
    for key in('phases_checked','words_checked','heap_boundaries_checked','unknown_bytes'):counts['crt_'+key]+=temporary['exit_'+key]
    differences.extend(dict(d,kind=d['kind'].replace('exit-','crt-',1))for d in found)


def observe_call(fixture,entry,native,which,engine,record,counts,differences,seen,*,component=False):
    index=record['index'];identity=dict(call=index,phase=which);seen.append((index,which))
    if which=='before':counts['crt_calls_checked']+=1
    if component and index==0 and which=='before':return
    if index>=len(native):differences.append(dict(kind='crt-extra-call',**identity));return
    target=native[index]
    if(record['kind'],record['pc'])!=(target['kind'],target['pc']):differences.append(dict(kind='crt-call',**identity,actual=(record['kind'],record['pc']),original=(target['kind'],target['pc'])))
    if which=='before':
        for i,value in enumerate(record['arguments']):
            counts['crt_argument_words_checked']+=1
            if target['arguments'][i]!=value:differences.append(dict(kind='crt-argument',**identity,index=i,actual=value,original=target['arguments'][i]))
    if which not in target:differences.append(dict(kind='crt-extra-phase',**identity));return
    phase(fixture,entry,target[which],engine,record,identity,counts,differences)
    if which=='after'and record.get('value')is not None:
        counts['crt_values_checked']+=1
        if record['value']!=target[which]['registers']['eax']:differences.append(dict(kind='crt-value',**identity,actual=record['value'],original=target[which]['registers']['eax']))


def remaining(fixture,native,seen,differences):
    for index,call in enumerate(native):
        for which in('before','after'):
            if which not in call:continue
            for region in call[which]['regions']:data(fixture,region)
            if(index,which)not in seen:differences.append(dict(kind='crt-phase-missing',call=index,phase=which,original_kind=call['kind']))


def compare(fixture,entry,*,return_state=False):
    entry=expand_case(fixture,entry);native=entry['shutdown']['crt_calls'];seen=[];differences=[];counts=dict.fromkeys(CRT_TOTALS,0);counts['native_crt_calls']=len(native)
    def observe(which,engine,record,storage):
        observe_call(fixture,entry,native,which,engine,record,counts,differences,seen)
        target=native[record['index']]
        if which in target and len(storage.events)!=target[which]['shutdown_event_count']:differences.append(dict(kind='crt-event-count',call=record['index'],phase=which,actual=len(storage.events),original=target[which]['shutdown_event_count']))
    result,h,a,m,storage=parent.compare(fixture,entry,return_state=True,observe_crt=observe)
    remaining(fixture,native,seen,differences);result.update(counts);result['differences'].extend(differences)
    if return_state:return result,h,a,m,storage
    return result


def compare_isolated(fixture,entry):
    from types import SimpleNamespace
    from audit_malloc_storage_original import engine as malloc_engine
    from reasitic.exit_storage import ExitStorage
    from reasitic.crt_storage import CRTStorage
    entry=expand_case(fixture,entry);native=entry['shutdown']['crt_calls'];seen=[];differences=[];counts=dict.fromkeys(CRT_TOTALS,0);counts['native_crt_calls']=len(native)
    before=native[0]['before'];ctx=entry['transition_inputs']['loader_context'];h,m,_=malloc_engine(fixture,dict(before,regions=ctx['regions']+before['regions']),ctx)
    history=SimpleNamespace(heap=h,memory=m,inputs=entry['transition_inputs'],libio=entry['libio_inputs'])
    def release(address,caller,*,before_free):before_free();h.free(address)
    exiting=ExitStorage(history,release=release)
    def observe(which,engine,record):observe_call(fixture,entry,native,which,engine,record,counts,differences,seen,component=True)
    engine=CRTStorage(exiting,observe=observe)
    try:engine.main_fini()
    except(ValueError,NotImplementedError)as error:differences.append(dict(kind='crt-runtime',reason=str(error)))
    remaining(fixture,native,seen,differences)
    return dict(label=entry['label'],cache_mode=entry['cache_mode'],differences=differences,**counts)


def run(fixture,*,isolated=False):
    results=[]
    for entry in fixture['cases']:
        r=(compare_isolated if isolated else compare)(fixture,entry);results.append(r);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(r['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    keys=CRT_TOTALS if isolated else(*parent.parent.parent.parent.parent.TOTALS,'printf_calls_checked','printf_registers_checked','native_io_calls','io_calls_checked','io_words_checked','io_registers_checked','io_positions_checked','io_unknown_bytes',*parent.parent.parent.MALLOC_TOTALS,*parent.parent.CLEANUP_TOTALS,*parent.EXIT_TOTALS,*CRT_TOTALS)
    for key in keys:report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--isolated',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();fixture=read_fixture(ROOT/'tests/fixtures/shunt_crt_original.json.gz');report=run(fixture,isolated=a.isolated)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

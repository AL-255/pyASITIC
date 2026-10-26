"""Full prior history and source-driven exit-list/loader/fini assertions."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import audit_shunt_cleanup_original as parent
from audit_allocator_original import state_differences,heap_mapping_owners
from audit_loader_lookup_original import data
from exit_fixture import read_fixture,expand_case
from reasitic.memory import MemoryFault,UnknownMemory

EXIT_TOTALS=('native_exit_calls','exit_calls_checked','exit_phases_checked','exit_words_checked','exit_heap_boundaries_checked','exit_argument_words_checked','exit_object_order_checked','exit_unknown_bytes')


def phase(fixture,entry,expected,engine,record,identity,counts,differences):
    m,h=engine.m,engine.heap;inputs=engine.history.inputs;workspace=inputs['workspace_address']
    stack=next(r for r in inputs['initial_regions']if r['address']<=workspace and workspace+4460<=r['address']+len(r['data'])//2)
    owners=[(stack['address'],len(stack['data'])//2),*heap_mapping_owners(h),(h.arena_address,h.arena_size),(engine.history.libio['libc_symbols']['_IO_list_all']['address'],4)]
    owners.extend((r['address'],r['size'])for r in inputs['stdio_context']['regions']);owners.extend((r['address'],r['size'])for r in inputs['exit_inputs']['regions'])
    if owners!=[(r['address'],r['size'])for r in expected['regions']]:differences.append(dict(kind='exit-region-owners',**identity,actual=owners))
    for region in expected['regions']:
        original=data(fixture,region);address=region['address']
        try:raw=m.read(address,len(original))
        except(MemoryFault,UnknownMemory):raw=None
        if raw!=original:
            for offset in range(0,len(original),4):
                size=min(4,len(original)-offset)
                try:word=raw[offset:offset+size]if raw is not None else m.read(address+offset,size)
                except(MemoryFault,UnknownMemory):counts['exit_unknown_bytes']+=size;differences.append(dict(kind='exit-unknown-word',**identity,address=address+offset));continue
                if word!=original[offset:offset+size]:differences.append(dict(kind='exit-word',**identity,address=address+offset,actual=word.hex(),original=original[offset:offset+size].hex()))
        counts['exit_words_checked']+=(len(original)+3)//4
    differences.extend(dict(d,**identity)for d in state_differences(h,expected['heap'],memory=m));counts['exit_heap_boundaries_checked']+=1
    for name,value in dict(arena_address=h.arena_address,parameters=h.parameters,flags=h.flags,max_fast=h.max_fast,tcache_address=h.cache_address,tcache_counts=[h._cache_count(i)for i in range(64)],tcache_key=h._cache_key,mapping_policy=h.address_space.policy).items():
        if value!=expected['heap'][name]:differences.append(dict(kind='exit-heap-field',**identity,name=name,actual=value,original=expected['heap'][name]))
    differences.append(dict(kind='exit-register-continuation-missing',**identity,original=expected['registers']))
    differences.append(dict(kind='exit-fp-continuation-missing',**identity,bytes=len(expected['xstate'])//2));counts['exit_phases_checked']+=1


def compare(fixture,entry,*,return_state=False,observe_crt=None):
    entry=expand_case(fixture,entry);native=entry['shutdown']['exit_calls'];differences=[];seen=[];counts=dict.fromkeys(EXIT_TOTALS,0);counts['native_exit_calls']=len(native)
    def observe(which,engine,record,storage):
        if observe_crt is not None:engine.observe_crt=lambda p,c,r:observe_crt(p,c,r,storage)
        index=record['index'];identity=dict(call=index,phase=which);seen.append((index,which))
        if which=='before':counts['exit_calls_checked']+=1
        if index>=len(native):differences.append(dict(kind='exit-extra-call',**identity));return
        target=native[index]
        if (record['kind'],record['pc'])!=(target['kind'],target['pc']):differences.append(dict(kind='exit-call',**identity,actual=(record['kind'],record['pc']),original=(target['kind'],target['pc'])))
        # The observer stores three raw stack words; only the source-declared
        # arguments have C parameter roles. All words remain full-stack targets.
        if which=='before':
            for i,value in enumerate(record['arguments']):
                counts['exit_argument_words_checked']+=1
                if target['arguments'][i]!=value:differences.append(dict(kind='exit-argument',**identity,index=i,actual=value,original=target['arguments'][i]))
        if which not in target:differences.append(dict(kind='exit-extra-phase',**identity));return
        phase(fixture,entry,target[which],engine,record,identity,counts,differences)
        if len(storage.events)!=target[which]['shutdown_event_count']:differences.append(dict(kind='exit-event-count',**identity,actual=len(storage.events),original=target[which]['shutdown_event_count']))
    result,h,a,m,storage=parent.compare(fixture,entry,return_state=True,observe_exit=observe)
    for index,call in enumerate(native):
        for which in('before','after'):
            if which not in call:continue
            for region in call[which]['regions']:data(fixture,region)
            if(index,which)not in seen:differences.append(dict(kind='exit-phase-missing',call=index,phase=which,original_kind=call['kind']))
    engine=getattr(storage.history,'exiting',None)
    if engine is not None:
        order=[c['arguments'][0]for c in native if c['kind']=='object'];counts['exit_object_order_checked']=len(order)
        if engine.object_order!=order:differences.append(dict(kind='exit-object-order',actual=engine.object_order,original=order))
    else:differences.append(dict(kind='exit-order-continuation-missing'))
    result.update(counts);result['differences'].extend(differences)
    if return_state:return result,h,a,m,storage
    return result


def compare_isolated(fixture,entry):
    from types import SimpleNamespace
    from audit_malloc_storage_original import engine as malloc_engine
    from reasitic.exit_storage import ExitStorage
    entry=expand_case(fixture,entry);native=entry['shutdown']['exit_calls'];counts=dict.fromkeys(EXIT_TOTALS,0);counts['native_exit_calls']=len(native);differences=[];seen=[]
    before=native[0]['before'];ctx=entry['transition_inputs']['loader_context'];h,m,_=malloc_engine(fixture,dict(before,regions=ctx['regions']+before['regions']),ctx)
    history=SimpleNamespace(heap=h,memory=m,inputs=entry['transition_inputs'],libio=entry['libio_inputs'])
    def observe(which,engine,record):
        index=record['index'];seen.append((index,which))
        if which=='before':counts['exit_calls_checked']+=1
        if index==0 and which=='before':return  # Component input, never full-history input.
        if index>=len(native):differences.append(dict(kind='exit-extra-call',call=index,phase=which));return
        target=native[index]
        if(record['kind'],record['pc'])!=(target['kind'],target['pc']):differences.append(dict(kind='exit-call',call=index,phase=which))
        if which=='before':
            for i,value in enumerate(record['arguments']):
                counts['exit_argument_words_checked']+=1
                if target['arguments'][i]!=value:differences.append(dict(kind='exit-argument',call=index,phase=which,index=i,actual=value,original=target['arguments'][i]))
        if which not in target:differences.append(dict(kind='exit-extra-phase',call=index,phase=which));return
        phase(fixture,entry,target[which],engine,record,dict(call=index,phase=which),counts,differences)
    engine=ExitStorage(history,observe=observe)
    try:engine.run(0)
    except(ValueError,NotImplementedError)as error:differences.append(dict(kind='exit-runtime',reason=str(error)))
    for index,call in enumerate(native):
        for which in('before','after'):
            if which not in call:continue
            for region in call[which]['regions']:data(fixture,region)
            if(index,which)not in seen:differences.append(dict(kind='exit-phase-missing',call=index,phase=which,original_kind=call['kind']))
    order=[c['arguments'][0]for c in native if c['kind']=='object'];counts['exit_object_order_checked']=len(order)
    if engine.object_order!=order:differences.append(dict(kind='exit-object-order',actual=engine.object_order,original=order))
    return dict(label=entry['label'],cache_mode=entry['cache_mode'],differences=differences,**counts)


def run(fixture,*,isolated=False):
    results=[]
    for entry in fixture['cases']:
        r=(compare_isolated if isolated else compare)(fixture,entry);results.append(r);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(r['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    keys=EXIT_TOTALS if isolated else(*parent.parent.parent.parent.TOTALS,'printf_calls_checked','printf_registers_checked','native_io_calls','io_calls_checked','io_words_checked','io_registers_checked','io_positions_checked','io_unknown_bytes',*parent.parent.MALLOC_TOTALS,*parent.CLEANUP_TOTALS,*EXIT_TOTALS)
    for key in keys:report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--isolated',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();fixture=read_fixture(ROOT/'tests/fixtures/shunt_exit_original.json.gz');r=run(fixture,isolated=a.isolated)
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items()if k!='results'});raise SystemExit(int(bool(r['differences'])))


if __name__=='__main__':main()

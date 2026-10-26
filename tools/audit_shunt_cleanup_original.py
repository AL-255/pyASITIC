"""Every prior target plus complete continuing log-close/finalizer assertions."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import audit_shunt_malloc_original as parent
from audit_allocator_original import state_differences,heap_mapping_owners
from audit_loader_lookup_original import data
from reasitic.memory import MemoryFault,UnknownMemory

CLEANUP_TOTALS=('native_cleanup_calls','cleanup_calls_checked','cleanup_phases_checked','cleanup_words_checked','cleanup_heap_boundaries_checked','cleanup_unknown_bytes')


def compare_phase(fixture,expected,cleanup,call,event_count,counts,differences,identity):
    m,h,inputs=cleanup.memory,cleanup.heap,cleanup.history.inputs;workspace=inputs['workspace_address']
    stack=next(r for r in inputs['initial_regions']if r['address']<=workspace and workspace+4460<=r['address']+len(r['data'])//2)
    owners=[(stack['address'],len(stack['data'])//2),*heap_mapping_owners(h)]
    owners.extend(((h.arena_address,h.arena_size),(cleanup.abi['libc_symbols']['_IO_list_all']['address'],4),(call['file'],304)))
    owners.extend((r['address'],r['size'])for r in inputs['stdio_context']['regions'])
    if owners!=[(r['address'],r['size'])for r in expected['regions']]:differences.append(dict(kind='cleanup-region-owners',**identity,actual=owners))
    for region in expected['regions']:
        original=data(fixture,region);p=region['address']
        try:raw=m.read(p,len(original))
        except(MemoryFault,UnknownMemory):raw=None
        if raw!=original:
            for offset in range(0,len(original),4):
                size=min(4,len(original)-offset)
                try:word=raw[offset:offset+size]if raw is not None else m.read(p+offset,size)
                except(MemoryFault,UnknownMemory):counts['cleanup_unknown_bytes']+=size;differences.append(dict(kind='cleanup-unknown-word',**identity,address=p+offset));continue
                if word!=original[offset:offset+size]:differences.append(dict(kind='cleanup-word',**identity,address=p+offset,actual=word.hex(),original=original[offset:offset+size].hex()))
        counts['cleanup_words_checked']+=(len(original)+3)//4
    differences.extend(dict(d,**identity)for d in state_differences(h,expected['heap'],memory=m));counts['cleanup_heap_boundaries_checked']+=1
    for name,value in dict(arena_address=h.arena_address,parameters=h.parameters,flags=h.flags,max_fast=h.max_fast,tcache_address=h.cache_address,tcache_counts=[h._cache_count(i)for i in range(64)],tcache_key=h._cache_key,mapping_policy=h.address_space.policy).items():
        if value!=expected['heap'][name]:differences.append(dict(kind='cleanup-heap-field',**identity,name=name,actual=value,original=expected['heap'][name]))
    if event_count!=expected['shutdown_event_count']:differences.append(dict(kind='cleanup-event-count',**identity,actual=event_count,original=expected['shutdown_event_count']))
    # Semantic close has not yet executed its caller/free CPU frames.
    # The complete native state remains required, never copied into it.
    differences.append(dict(kind='cleanup-register-continuation-missing',**identity,original=expected['registers']))
    differences.append(dict(kind='cleanup-fp-continuation-missing',**identity,bytes=len(expected['xstate'])//2))
    counts['cleanup_phases_checked']+=1


def compare(fixture,entry,*,return_state=False,observe_exit=None):
    native=entry['shutdown']['cleanup'];differences=[];seen=[];counts=dict.fromkeys(CLEANUP_TOTALS,0);counts['native_cleanup_calls']=len(native)
    def observe(phase,cleanup,address,storage):
        index=len(cleanup.calls)-1;call=cleanup.calls[-1];ordinal=len(call['free'])-1 if phase=='free'else None;identity=dict(call=index,phase=phase)
        if ordinal is not None:identity['free']=ordinal
        seen.append((index,phase,ordinal))
        if phase=='before':counts['cleanup_calls_checked']+=1
        if index>=len(native):differences.append(dict(kind='cleanup-extra-call',**identity));return
        target=native[index]
        if(call['kind'],call['file'])!=(target['kind'],target.get('file')):differences.append(dict(kind='cleanup-call',**identity,actual=(call['kind'],call['file']),original=(target['kind'],target.get('file'))))
        if phase=='free':
            if ordinal>=len(target['free']):differences.append(dict(kind='cleanup-extra-free',**identity));return
            if address!=target['free'][ordinal]['address']:differences.append(dict(kind='cleanup-free-owner',**identity,actual=address,original=target['free'][ordinal]['address']))
            expected=target['free'][ordinal]['state']
        elif phase in target:expected=target[phase]
        else:differences.append(dict(kind='cleanup-extra-phase',**identity));return
        compare_phase(fixture,expected,cleanup,call,len(storage.events),counts,differences,identity)
    result,h,a,m,storage=parent.compare(fixture,entry,return_state=True,observe_cleanup=observe,observe_exit=observe_exit)
    for index,call in enumerate(native):
        phases=[(phase,None,call[phase])for phase in('before','after')if phase in call]+[('free',ordinal,point['state'])for ordinal,point in enumerate(call.get('free',[]))]
        for phase,ordinal,point in phases:
            for region in point['regions']:data(fixture,region)
            if(index,phase,ordinal)not in seen:differences.append(dict(kind='cleanup-phase-missing',call=index,phase=phase,free=ordinal,original_kind=call['kind']))
    result.update(counts);result['differences'].extend(differences)
    if return_state:return result,h,a,m,storage
    return result


def compare_isolated(fixture,entry):
    from types import SimpleNamespace
    from audit_malloc_storage_original import engine
    from reasitic.process_cleanup import ProcessCleanup
    native=entry['shutdown']['cleanup'];differences=[];counts=dict.fromkeys(CLEANUP_TOTALS,0);counts['native_cleanup_calls']=len(native)
    for index,call in enumerate(native):
        for point in [call[k]for k in('before','after')if k in call]+[v['state']for v in call.get('free',[])]:
            for region in point['regions']:data(fixture,region)
        if call['kind']=='XFreeThreads':
            for phase in('before','after'):differences.append(dict(kind='cleanup-phase-missing',call=index,phase=phase,original_kind=call['kind']))
            continue
        before=call['before'];ctx=entry['transition_inputs']['loader_context']
        try:
            h,m,_=engine(fixture,dict(before,regions=ctx['regions']+before['regions']),ctx)
            history=SimpleNamespace(heap=h,memory=m,inputs=entry['transition_inputs'],libio=entry['libio_inputs'])
            event_count=before['shutdown_event_count']
            def release(address,caller,*,before_free):
                nonlocal event_count
                event_count+=1;before_free();h.free(address)
            def observe(phase,cleanup,address):
                if phase=='before':return  # This component boundary is its earlier input.
                actual=cleanup.calls[-1];identity=dict(call=index,phase=phase)
                if phase=='free':
                    ordinal=len(actual['free'])-1;identity['free']=ordinal;target=call['free'][ordinal]
                    if target['address']!=address:differences.append(dict(kind='cleanup-free-owner',**identity,actual=address,original=target['address']))
                    expected=target['state']
                else:expected=call[phase]
                compare_phase(fixture,expected,cleanup,actual,event_count,counts,differences,identity)
            cleanup=ProcessCleanup(history,release=release,observe=observe);cleanup.close(call['kind'],call['file']);counts['cleanup_calls_checked']+=1
        except(ValueError,NotImplementedError)as error:differences.append(dict(kind='cleanup-runtime',call=index,reason=str(error)))
    return dict(label=entry['label'],cache_mode=entry['cache_mode'],differences=differences,**counts)


def run(fixture,*,isolated=False):
    results=[]
    for entry in fixture['cases']:
        r=(compare_isolated if isolated else compare)(fixture,entry);results.append(r);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(r['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    keys=CLEANUP_TOTALS if isolated else(*parent.parent.parent.TOTALS,'printf_calls_checked','printf_registers_checked','native_io_calls','io_calls_checked','io_words_checked','io_registers_checked','io_positions_checked','io_unknown_bytes',*parent.MALLOC_TOTALS,*CLEANUP_TOTALS)
    for key in keys:report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--isolated',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    f=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_cleanup_original.json.gz').read_bytes()));r=run(f,isolated=a.isolated)
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items()if k!='results'});raise SystemExit(int(bool(r['differences'])))


if __name__=='__main__':main()

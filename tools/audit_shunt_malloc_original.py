"""Continuing stdin malloc and independent whole-function ABI assertions."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import audit_shunt_repl_original as parent
from audit_malloc_storage_original import engine
from audit_allocator_original import state_differences
from audit_loader_lookup_original import data
from reasitic.memory import MemoryFault,UnknownMemory

MALLOC_TOTALS=('native_malloc_calls','malloc_calls_checked','malloc_phases_checked','malloc_words_checked','malloc_registers_checked','malloc_heap_boundaries_checked','malloc_unknown_bytes')


def compare_isolated(fixture,entry):
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],differences=[],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,heap_boundaries_checked=0)
    for index,call in enumerate(entry['shutdown']['malloc']):
        if 'after'not in call:result['differences'].append(dict(kind='malloc-return-missing',call=index));continue
        before,after=call['before'],call['after'];ctx=entry['transition_inputs']['loader_context']
        inputs=dict(before,regions=ctx['regions']+before['regions'])
        try:
            h,m,storage=engine(fixture,inputs,ctx);storage.enter(before['registers'])
            pointer=h.malloc(m.u32(before['registers']['esp']+4));r=storage.returned(pointer)
        except(ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='malloc-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        if [(v['address'],v['size'])for v in before['regions']]!=[(v['address'],v['size'])for v in after['regions']]:result['differences'].append(dict(kind='malloc-region-owners',call=index))
        for region in after['regions']:
            expected=data(fixture,region);raw=m.read(region['address'],len(expected));result['words_checked']+=(len(expected)+3)//4
            if raw!=expected:
                for offset in range(0,len(expected),4):
                    if raw[offset:offset+4]!=expected[offset:offset+4]:result['differences'].append(dict(kind='malloc-word',call=index,address=region['address']+offset,actual=raw[offset:offset+4].hex(),original=expected[offset:offset+4].hex()))
        if set(r)!=set(after['registers']):result['differences'].append(dict(kind='malloc-register-set',call=index))
        for name,value in after['registers'].items():
            result['registers_checked']+=1
            if r.get(name)!=value:result['differences'].append(dict(kind='malloc-register',call=index,name=name,actual=r.get(name),original=value))
        a,b=bytes.fromhex(before['xstate']),bytes.fromhex(after['xstate']);result['fp_bytes_checked']+=len(b)
        if len(a)!=len(b):result['differences'].append(dict(kind='malloc-fp-size',call=index,actual=len(a),original=len(b)))
        if a!=b:
            for offset,(left,right)in enumerate(zip(a,b)):
                if left!=right:result['differences'].append(dict(kind='malloc-fp-byte',call=index,offset=offset,actual=left,original=right))
        result['differences'].extend(state_differences(h,after['heap'],memory=m));result['heap_boundaries_checked']+=1
        for name,value in dict(arena_address=h.arena_address,parameters=h.parameters,flags=h.flags,max_fast=h.max_fast,tcache_address=h.cache_address,tcache_counts=[h._cache_count(i)for i in range(64)],tcache_key=h._cache_key,mapping_policy=h.address_space.policy).items():
            if value!=after['heap'][name]:result['differences'].append(dict(kind='malloc-heap-field',call=index,name=name,actual=value,original=after['heap'][name]))
        if after['heap']['maps']!=before['heap']['maps']or sorted(h.address_space.ranges)!=sorted((v['start'],v['end'])for v in after['heap']['maps']):result['differences'].append(dict(kind='malloc-mappings',call=index))
        if after['heap']['event_count']!=before['heap']['event_count']:result['differences'].append(dict(kind='malloc-observer-event-count',call=index))
        for error in after['heap']['errors']:
            if error['section']!='chunks':result['differences'].append(dict(kind='malloc-additional-native-heap-error',call=index,error=error))
    return result


def compare(fixture,entry,*,return_state=False):
    native=entry['shutdown']['malloc'];differences=[];seen=[];counts=dict.fromkeys(MALLOC_TOTALS,0);counts['native_malloc_calls']=len(native)
    def observe(phase,registers,storage):
        index=len(storage.malloc_calls)-1;seen.append((index,phase))
        if phase=='before':counts['malloc_calls_checked']+=1
        if index>=len(native)or phase not in native[index]:differences.append(dict(kind='malloc-extra-phase',call=index,phase=phase));return
        # Only the live source heap/memory and original first-driver input
        # owners supply actual values. Later malloc snapshots are assertions.
        expected=native[index][phase];m,h=storage.memory,storage.heap;inputs=storage.history.inputs
        workspace=inputs['workspace_address'];stack=next(r for r in inputs['initial_regions']if r['address']<=workspace and workspace+4460<=r['address']+len(r['data'])//2)
        base=h.parameters['sbrk_base'];owners=[(stack['address'],len(stack['data'])//2)]
        owners.extend((start,end-start)for start,end in sorted(h.address_space.ranges)if start<=base<end)
        owners.append((h.arena_address,h.arena_size))
        if owners!=[(r['address'],r['size'])for r in expected['regions']]:differences.append(dict(kind='malloc-region-owners',call=index,phase=phase,actual=owners))
        for region in expected['regions']:
            original=data(fixture,region);address=region['address']
            try:raw=m.read(address,len(original))
            except(MemoryFault,UnknownMemory):raw=None
            if raw!=original:
                for offset in range(0,len(original),4):
                    size=min(4,len(original)-offset)
                    try:word=raw[offset:offset+size]if raw is not None else m.read(address+offset,size)
                    except(MemoryFault,UnknownMemory):counts['malloc_unknown_bytes']+=size;differences.append(dict(kind='malloc-unknown-word',call=index,phase=phase,address=address+offset));continue
                    if word!=original[offset:offset+size]:differences.append(dict(kind='malloc-word',call=index,phase=phase,address=address+offset,actual=word.hex(),original=original[offset:offset+size].hex()))
            counts['malloc_words_checked']+=(len(original)+3)//4
        if set(registers)!=set(expected['registers']):differences.append(dict(kind='malloc-register-set',call=index,phase=phase))
        for name,value in expected['registers'].items():
            counts['malloc_registers_checked']+=1
            if registers.get(name)!=value:differences.append(dict(kind='malloc-register',call=index,phase=phase,name=name,actual=registers.get(name),original=value))
        differences.extend(dict(d,call=index,phase=phase)for d in state_differences(h,expected['heap'],memory=m));counts['malloc_heap_boundaries_checked']+=1
        for name,value in dict(arena_address=h.arena_address,parameters=h.parameters,flags=h.flags,max_fast=h.max_fast,tcache_address=h.cache_address,tcache_counts=[h._cache_count(i)for i in range(64)],tcache_key=h._cache_key,mapping_policy=h.address_space.policy).items():
            if value!=expected['heap'][name]:differences.append(dict(kind='malloc-heap-field',call=index,phase=phase,name=name,actual=value,original=expected['heap'][name]))
        # malloc itself preserves FP state (independently checked above), but
        # full earlier x87/SIMD execution has not yet supplied a source XSAVE.
        differences.append(dict(kind='malloc-fp-continuation-missing',call=index,phase=phase,bytes=len(expected['xstate'])//2))
        counts['malloc_phases_checked']+=1
    result,h,a,m,storage=parent.compare(fixture,entry,return_state=True,observe_malloc=observe)
    for index,call in enumerate(native):
        for phase in call:
            for region in call[phase]['regions']:data(fixture,region)
            if(index,phase)not in seen:differences.append(dict(kind='malloc-phase-missing',call=index,phase=phase))
    result.update(counts);result['differences'].extend(differences)
    if return_state:return result,h,a,m,storage
    return result


def run(fixture,*,isolated=False):
    results=[];compare_case=compare_isolated if isolated else compare
    for entry in fixture['cases']:
        r=compare_case(fixture,entry);results.append(r);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(r['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    keys=('calls_checked','words_checked','registers_checked','fp_bytes_checked','heap_boundaries_checked')if isolated else(*parent.parent.TOTALS,'printf_calls_checked','printf_registers_checked','native_io_calls','io_calls_checked','io_words_checked','io_registers_checked','io_positions_checked','io_unknown_bytes',*MALLOC_TOTALS)
    for key in keys:report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--isolated',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    f=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_malloc_original.json.gz').read_bytes()));report=run(f,isolated=a.isolated)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

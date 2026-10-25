"""Complete stdio caller and malloc regions, registers, FP and heap state."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_file_allocation_original import compare as callers
from audit_allocator_original import state_differences
from audit_loader_lookup_original import data,memory_for
from reasitic.heap import Heap
from reasitic.malloc_storage import MallocStorage


def engine(fixture,state,context):
    m=memory_for(fixture,state);snapshot=state['heap'];chunks={c['address']:c for c in snapshot['chunks']}
    # A native corrupted header walk can stop before otherwise reachable bin
    # chunks. Retain that physical walk/error unchanged as a later target,
    # while loading independently earlier bin-owned headers from the same
    # earlier bytes. No later heap snapshot supplies the missing inventory.
    pointers={p for chain in snapshot['bins']+snapshot['fastbins']for p in chain}
    pointers.update(p-8 for chain in snapshot['tcache']for p in chain)
    for p in sorted(pointers):
        size=m.u32(p+4)&~7
        for address in (p,p+size):
            if address not in chunks:chunks[address]=dict(address=address,prev_size=m.u32(address),size_word=m.u32(address+4))
    h=Heap(dict(snapshot,chunks=list(chunks.values())));m.address_space=h.address_space
    libc=m.u32(next(x['address']for x in context['maps']if x['name'].endswith('/libc.so.6')))
    h.observe_header_stores(m);h.attach_cache_memory(m,m.u32(libc+0x22fe34+0x3bfc))
    return h,m,MallocStorage(h,m,libc_base=libc,tls_base=context['tls_base'])


def compare(fixture,case):
    result=callers(fixture,case);result['heap_boundaries_checked']=0
    for index,call in enumerate(case['allocation_calls']):
        for start,end in (('entry','malloc'),('allocated','return')):
            if start in call and end in call:
                a,b=call[start]['heap'],call[end]['heap']
                if {k:v for k,v in a.items()if k!='label'}!={k:v for k,v in b.items()if k!='label'}:
                    result['differences'].append(dict(kind='malloc-caller-heap-change',call=index,phase=start))
                result['heap_boundaries_checked']+=1
        if 'malloc'not in call or'allocated'not in call:result['differences'].append(dict(kind='malloc-missing-boundary',call=index));continue
        a,b=call['malloc'],call['allocated']
        try:
            h,m,storage=engine(fixture,a,call['entry']);storage.enter(a['registers'])
            pointer=h.malloc(m.u32(a['registers']['esp']+4));registers=storage.returned(pointer)
        except (ValueError,NotImplementedError)as error:
            result['differences'].append(dict(kind='malloc-runtime',call=index,reason=str(error)));continue
        result['operations_checked']+=1
        def check(actual,expected,kind,unit=4,address=0):
            if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',call=index))
            for offset in range(0,len(expected),unit):
                if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
        owners=lambda state:[(r['address'],r['size'])for r in state['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='malloc-region-owners',call=index))
        for region in b['regions']:
            expected=data(fixture,region);check(m.read(region['address'],len(expected)),expected,'malloc-memory-word',address=region['address']);result['words_checked']+=(len(expected)+3)//4
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='malloc-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='malloc-register',call=index,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        check(bytes.fromhex(a['xstate']),bytes.fromhex(b['xstate']),'malloc-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        target=b['heap'];result['differences'].extend(state_differences(h,target,memory=m))
        fields=dict(arena_address=h.arena_address,parameters=h.parameters,flags=h.flags,max_fast=h.max_fast,
                    tcache_address=h.cache_address,tcache_counts=[h._cache_count(i)for i in range(64)])
        for name,value in fields.items():
            if value!=target[name]:result['differences'].append(dict(kind='malloc-heap-field',call=index,name=name,actual=value,original=target[name]))
        if m.read(h.arena_address,len(bytes.fromhex(target['arena_bytes'])))!=bytes.fromhex(target['arena_bytes']):
            result['differences'].append(dict(kind='malloc-arena-image',call=index))
        # This implemented branch makes no mapping/system allocation calls.
        if target['maps']!=a['heap']['maps']or sorted(h.address_space.ranges)!=sorted((x['start'],x['end'])for x in target['maps']):
            result['differences'].append(dict(kind='malloc-mappings',call=index))
        if target['event_count']!=a['heap']['event_count']:result['differences'].append(dict(kind='malloc-observer-event-count',call=index))
        for error in target['errors']:
            if error['section']!='chunks':result['differences'].append(dict(kind='malloc-additional-native-heap-error',call=index,error=error))
        result['heap_boundaries_checked']+=1
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/malloc_storage_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();f=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for case in f['cases']:
        r=compare(f,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['operations_checked']} operations, {len(r['differences'])} differences",flush=True)
    report=dict(cases=len(results),cases_without_allocation=sum(not c['allocation_calls']for c in f['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in f['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('operations_checked','words_checked','registers_checked','fp_bytes_checked','heap_boundaries_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

"""Complete printf FILE-buffer setup/completion and every native target."""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from printf_fixture import data,memory_for,expand_state
from reasitic.printf_file import PrintfFile
from printf_archive import read_fixture
from audit_allocator_original import state_differences,header_walk
from reasitic.heap import Heap
from reasitic.memory import MemoryFault
from reasitic.libio_abi import LibioABI
from reasitic.plt_fixup_storage import PltFixup


def heap_errors(heap,memory):
    """Re-observe all metadata errors from produced bytes, including bad links.

    This follows the native read-only observer, not its recorded errors.
    Unknown earlier bytes still raise; only an actual unmapped guest range
    produces the corresponding GDB memory-read diagnostic.
    """
    m=memory;_,errors=header_walk(m,heap.parameters['sbrk_base'],heap.top)
    def chain_at(head,end,offset,safe,section):
        chain=[];seen=set();p=head
        while p!=end:
            if p in seen or len(chain)>=100000:errors.append(dict(section=section,address=p,reason='cycle-or-limit'));break
            try:following=m.u32(p+offset)
            except MemoryFault as error:errors.append(dict(section=section,address=p,reason=f'Cannot access memory at address {error.address:#x}'));break
            seen.add(p);chain.append(p);p=following^((p+offset)>>12)if safe else following
        return chain
    for index in range(1,128):
        head=heap._bin_head(index);chain=chain_at(m.u32(head+8),head,8,False,f'bin.{index}');previous=head
        for p in chain:
            if m.u32(p+12)!=previous:errors.append(dict(section=f'bin.{index}',address=p,reason='backlink'))
            previous=p
        if m.u32(head+12)!=previous:errors.append(dict(section=f'bin.{index}',address=head,reason='tail'))
    for index in range(11):chain_at(m.u32(heap.arena_address+12+4*index),0,8,True,f'fastbin.{index}')
    for index in range(64):
        chain=chain_at(m.u32(heap.cache_address+128+4*index)if heap.tcache_enabled else 0,0,0,True,f'tcache.{index}')
        count=m.u16(heap.cache_address+2*index)if heap.tcache_enabled else 0
        if len(chain)!=count:errors.append(dict(section=f'tcache.{index}',reason='count',count=count,observed=len(chain)))
    return errors


def engine(fixture,state):
    state=expand_state(fixture,state);m=memory_for(fixture,state);base=m.u32(next(x['address']for x in state['maps']if x['name'].endswith('/libc.so.6')))
    snapshot=state['heap'];chunks={c['address']:c for c in snapshot['chunks']}
    pointers={p for chain in snapshot['bins']+snapshot['fastbins']for p in chain}
    pointers.update(p-8 for chain in snapshot['tcache']for p in chain)
    for p in sorted(pointers):
        size=m.u32(p+4)&~7
        for address in (p,p+size):
            if address not in chunks:chunks[address]=dict(address=address,prev_size=m.u32(address),size_word=m.u32(address+4))
    heap=Heap(dict(snapshot,chunks=list(chunks.values())));m.address_space=heap.address_space
    heap.observe_header_stores(m);heap.attach_cache_memory(m,m.u32(base+0x22fe34+0x3bfc))
    io=LibioABI(m,PltFixup(m,state['loader_base'],tls_base=state['tls_base']),state,libc_base=base,tls_base=state['tls_base']);io.profile=state['profile']
    return m,PrintfFile(m,libc_base=base,tls_base=state['tls_base'],heap=heap,io=io)


def compare(fixture,case,*,storage_factory=engine):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],calls_checked=0,words_checked=0,registers_checked=0,fp_bytes_checked=0,children_checked=0,child_registers_checked=0,differences=[])
    for index,call in enumerate(case['printf_calls']):
        if 'after'not in call:result['differences'].append(dict(kind='printf-missing-return',call=index));continue
        a,b=(expand_state(fixture,call[p])for p in ('before','after'))
        try:m,storage=storage_factory(fixture,a);registers=getattr(storage,call['kind'])(a['registers'])
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='printf-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        heap=storage.heap;target=b['heap'];result['differences'].extend(dict(call=index,**d)for d in state_differences(heap,target,memory=m))
        fields=dict(arena_address=heap.arena_address,parameters=heap.parameters,flags=heap.flags,max_fast=heap.max_fast,tcache_address=heap.cache_address,tcache_counts=[heap._cache_count(i)for i in range(64)])
        for name,value in fields.items():
            if value!=target[name]:result['differences'].append(dict(kind='printf-heap-field',call=index,name=name,actual=value,original=target[name]))
        if m.read(heap.arena_address,len(bytes.fromhex(target['arena_bytes'])))!=bytes.fromhex(target['arena_bytes']):result['differences'].append(dict(kind='printf-arena-image',call=index))
        if target['maps']!=a['heap']['maps']or sorted(heap.address_space.ranges)!=sorted((x['start'],x['end'])for x in target['maps']):result['differences'].append(dict(kind='printf-mappings',call=index))
        if target['event_count']!=a['heap']['event_count']:result['differences'].append(dict(kind='printf-observer-event-count',call=index))
        errors=heap_errors(heap,m)
        if errors!=target['errors']:result['differences'].append(dict(kind='printf-heap-errors',call=index,actual=errors,original=target['errors']))
        def check(left,right,kind,unit=4,address=0):
            if left==right:return
            if len(left)!=len(right):result['differences'].append(dict(kind=kind+'-size',call=index))
            for offset in range(0,len(right),unit):
                if left[offset:offset+unit]!=right[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,address=address+offset,actual=left[offset:offset+unit].hex(),original=right[offset:offset+unit].hex()))
        owners=lambda s:[(r['address'],r['size'])for r in s['regions']]
        if owners(a)!=owners(b):result['differences'].append(dict(kind='printf-region-owners',call=index))
        for r in b['regions']:
            expected=data(fixture,r)
            try:actual=m.read(r['address'],len(expected))
            except ValueError as error:result['differences'].append(dict(kind='printf-memory-unavailable',call=index,address=r['address'],reason=str(error)))
            else:check(actual,expected,'printf-memory-word',address=r['address'])
            result['words_checked']+=(len(expected)+3)//4
        if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='printf-register-set',call=index))
        for name,value in b['registers'].items():
            if registers.get(name)!=value:result['differences'].append(dict(kind='printf-register',call=index,name=name,actual=registers.get(name),original=value))
            result['registers_checked']+=1
        produced_fp=getattr(storage,'xstate',None)
        check(bytes.fromhex(a['xstate'])if produced_fp is None else produced_fp,bytes.fromhex(b['xstate']),'printf-fp-byte',unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
        if len(storage.children)!=len(call['children']):result['differences'].append(dict(kind='printf-child-count',call=index,actual=len(storage.children),original=len(call['children'])))
        for child,(actual,expected)in enumerate(zip(storage.children,call['children'])):
            result['children_checked']+=1
            if actual['kind']!=expected['kind']:result['differences'].append(dict(kind='printf-child-kind',call=index,child=child))
            for phase in ('before','after'):
                if set(actual[phase])!=set(expected[phase]):result['differences'].append(dict(kind='printf-child-register-set',call=index,child=child,phase=phase))
                for name,value in expected[phase].items():
                    if actual[phase].get(name)!=value:result['differences'].append(dict(kind='printf-child-register',call=index,child=child,phase=phase,name=name,actual=actual[phase].get(name),original=value))
                    result['child_registers_checked']+=1
    return result


def selected_indices(count,shard=1,shards=1):
    if isinstance(shard,bool)or isinstance(shards,bool)or not isinstance(shard,int)or not isinstance(shards,int)or not 1<=shard<=shards<=count:raise ValueError('Require 1 <= shard <= shards <= histories')
    return list(range(shard-1,count,shards))


def run(fixture,*,shard=1,shards=1):
    indices=selected_indices(len(fixture['cases']),shard,shards);cases=[fixture['cases'][i]for i in indices];results=[]
    for case in cases:
        r=compare(fixture,case);results.append(r);print(f"{case['label']}/{case['cache_mode']}: {r['calls_checked']} FILE helper calls, {len(r['differences'])} differences",flush=True)
    report=dict(total_cases=len(fixture['cases']),shard=shard,shards=shards,case_indices=indices,cases=len(results),cases_without_calls=sum(not c['printf_calls']for c in cases),native_terminal_counts=dict(collections.Counter(c['signal']for c in cases)),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('calls_checked','words_checked','registers_checked','fp_bytes_checked','children_checked','child_registers_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_file_original.manifest.json');p.add_argument('--output',type=Path);p.add_argument('--shard',type=int,default=1);p.add_argument('--shards',type=int,default=1);args=p.parse_args();f=read_fixture(args.fixture);report=run(f,shard=args.shard,shards=args.shards)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

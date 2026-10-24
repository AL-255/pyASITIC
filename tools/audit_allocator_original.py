"""Strict address/free-list comparison from captured native allocator states.

Initial snapshots and external object pointers are test inputs, not runtime
corrections. Every allocation after scope entry comes from the source plan.
"""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage
from reasitic.heap import Heap,SystemAllocationRequired


def state_differences(heap,state):
    differences=[]
    raw=bytes.fromhex(state['arena_bytes'])
    bitmap=[int.from_bytes(raw[offset:offset+4],'little')for offset in range(1080,1096,4)]
    if heap.binmap!=bitmap:differences.append(dict(kind='binmap',boundary=state['label'],actual=heap.binmap,original=bitmap))
    maximum=int.from_bytes(raw[1112:1116],'little')
    if heap.max_system_mem!=maximum:differences.append(dict(kind='max-system-memory',boundary=state['label'],actual=heap.max_system_mem,original=maximum))
    for field,actual in [('top',heap.top),('last_remainder',heap.last_remainder),('have_fastchunks',int(heap.have_fastchunks)),('system_mem',heap.system_mem),('bins',heap.bins[1:]),('fastbins',heap.fastbins),('tcache',[[p+8 for p in b]for b in heap.tcache])]:
        if actual!=state[field]:differences.append(dict(kind='state',boundary=state['label'],field=field,actual=actual,original=state[field]))
    original={c['address']:c for c in state['chunks']}
    if set(heap.chunks)!=set(original):differences.append(dict(kind='chunk-addresses',boundary=state['label'],extra=sorted(set(heap.chunks)-set(original)),missing=sorted(set(original)-set(heap.chunks))))
    for address in heap.chunks.keys()&original.keys():
        actual=heap.chunks[address];native=original[address];word=actual.size|int(actual.previous_in_use)
        if word!=native['size_word']:differences.append(dict(kind='chunk-header',boundary=state['label'],address=address,actual=word,original=native['size_word']))
        if not actual.previous_in_use and actual.previous!=native['prev_size']:differences.append(dict(kind='previous-size',boundary=state['label'],address=address,actual=actual.previous,original=native['prev_size']))
    if 'mapping_policy'in state:
        for field,original in state['parameters'].items():
            if heap.parameters[field]!=original:differences.append(dict(kind='malloc-parameter',boundary=state['label'],field=field,actual=heap.parameters[field],original=original))
        mapped=[dict(address=p,prev_size=c.previous,size_word=c.size|2)for p,c in sorted(heap.mapped.items())]
        native=[{key:c[key]for key in ('address','prev_size','size_word')}for c in state['mapped_chunks']]
        if mapped!=native:differences.append(dict(kind='mapped-chunks',boundary=state['label'],actual=mapped,original=native))
        def merge(ranges):
            result=[]
            for start,end in sorted(ranges):
                if result and start<=result[-1][1]:result[-1][1]=max(result[-1][1],end)
                else:result.append([start,end])
            return result
        actual=merge(heap.address_space.ranges);original=merge((m['start'],m['end'])for m in state['maps'])
        if actual!=original:differences.append(dict(kind='mapped-ranges',boundary=state['label'],actual=actual,original=original))
    return differences


def compare(case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],allocations_checked=0,events_checked=0,boundaries_checked=[],targets=[],differences=[],system_boundary=None,native_metadata_errors=[])
    states=case['allocator_states'];heap=Heap(states[0]);via=case['via']
    if states[0]['errors']:raise ValueError('Invalid initial allocator snapshot')
    addresses={}
    for i,group in enumerate(case['contact_groups']):
        addresses[f'contact_group.{i}']=group['address']
        addresses.update((f'contact.{i}.{j}',address)for j,address in enumerate(group['contacts']))
    addresses['geometry.descriptor']=via['shape_address']
    addresses.update((f'geometry.segment.{i}',address)for i,address in enumerate(via['segment_addresses']))
    plan=iter(combined_network_storage([len(g['contacts'])for g in case['contact_groups']],via['matrix']['size'],case['matrices']['ind_full']['size'],len(via['indices']),clone_segments=len(via['segments'])))
    boundaries={s['event_count']:s for s in states}
    for index,event in enumerate(case['events']):
        if event['kind']in('allocate','free'):
            expected=next(plan)
            if expected.action!=event['kind']or expected.allocator!=event['allocator']:raise ValueError('Source lifetime differs from capture')
            try:
                if expected.action=='allocate':
                    if expected.size!=event['request']:raise ValueError('Source request differs from capture')
                    address=heap.malloc(expected.size);addresses[expected.name]=address
                    result['allocations_checked']+=1
                    if address!=event['address']:result['differences'].append(dict(kind='address',index=index,name=expected.name,actual=address,original=event['address']))
                else:
                    address=addresses[expected.name]
                    if address!=event['address']:raise ValueError('Free identity differs from prediction')
                    chunk=heap.mapped.get(address-8)or heap.chunks[address-8]
                    if chunk.size!=event['chunk_size']:result['differences'].append(dict(kind='free-chunk-size',index=index,name=expected.name,actual=chunk.size,original=event['chunk_size']))
                    heap.free(address)
            except SystemAllocationRequired as error:
                result['system_boundary']=dict(index=index,name=expected.name,reason=str(error));break
            result['events_checked']+=1
            if result['differences']:break
        elif event['kind']=='via_write':
            address=addresses['ind.output']+16*event['index']*(via['matrix']['stride']+1)
            delta=address-addresses['cap.output'];n=via['matrix']['size']
            mapped=heap.address_space.contains(address,16)
            result['targets'].append(dict(index=event['index'],address=address,inside_cap=0<=delta<16*n*n and delta%16==0,mapped=mapped))
            if address!=event['address']:
                result['differences'].append(dict(kind='via-address',index=index,actual=address,original=event['address']));break
            if mapped!=(event['before']is not None):
                result['differences'].append(dict(kind='via-mapping',index=index,address=address,actual=mapped,original=event['before']is not None));break
        if index+1 in boundaries:
            state=boundaries[index+1]
            result['native_metadata_errors'].extend(dict(boundary=state['label'],**e)for e in state['errors'])
            result['differences'].extend(state_differences(heap,state))
            result['boundaries_checked'].append(state['label'])
            if result['differences']:break
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/allocator_state_original.json.gz');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[compare(c)for c in fixture['cases']]
    unresolved=[c for c in results if c['differences']or c['system_boundary']or c['native_metadata_errors']]
    report=dict(cases=len(results),allocations_checked=sum(c['allocations_checked']for c in results),events_checked=sum(c['events_checked']for c in results),boundary_counts=collections.Counter(b for c in results for b in c['boundaries_checked']),unresolved_cases=len(unresolved),results=results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(unresolved)))


if __name__=='__main__':main()

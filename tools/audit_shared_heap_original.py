"""Exact via stores, shared CAP aliases and raw native tcache interactions.

Byte initialization at via entry is a component-test precondition. It is not
runtime fixture lookup or a claim to derive preceding numerical writes.
"""
import argparse,collections,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.allocation_plan import combined_network_storage
from reasitic.bridge import _frequency
from reasitic.heap import Heap
from reasitic.memory import Memory,MemoryFault,UnknownMemory,ComplexView
from reasitic.vias import stamp_memory
from audit_allocator_original import state_differences


def seed(memory,state):
    for region in state['memory_regions']:memory.write(region['address'],bytes.fromhex(region['data']))
    memory.write(state['arena_address'],bytes.fromhex(state['arena_bytes']))


def via_records(case):
    technology=Technology.from_text(case['request']['technology']);group=0;records=[]
    for raw in case['via']['segments']:
        segment=bytes.fromhex(raw);metal=struct.unpack_from('<i',segment,0xdc)[0]
        if metal<len(technology.metals):group+=1;continue
        via=technology.vias[metal-len(technology.metals)]
        lo,hi=(struct.unpack_from('<d',segment,offset)[0]for offset in (16,40))
        nx,ny=struct.unpack_from('<2i',segment,0xe0)
        records.append((group,[_frequency(case['request']),lo,hi,via.width,via.resistance,nx,ny]))
    assert [index for index,record in records]==case['via']['indices']
    return records


def ported_capacitance(case):
    """Generate CAP from current Python geometry and numerical algorithms."""
    from reasitic.bridge import _shapes,_mesh
    from reasitic.solver import discretize
    from reasitic.potential import solve_capacitance
    from reasitic.network import _join_for_pads
    from reasitic.retained_scalar import Real as R
    request=case['request'];technology=Technology.from_text(request['technology'])
    shapes=_shapes(request,technology);mesh=_mesh(request,technology);boundary=None
    if request['action']=='pi2':shape=discretize(shapes[request['winding']],mesh['capacitance_length_cell'],mesh['length_cell']);ground=None
    else:
        first,second=(discretize(shapes[request[key]],mesh['capacitance_length_cell'],mesh['length_cell'])for key in ('first_winding','second_winding'))
        boundary=sum(segment.metal<len(technology.metals)for segment in first.segments)
        second.segments.reverse();shape=_join_for_pads(first,second);ground=shape
    result=solve_capacitance(shape,technology,_frequency(request),ground=ground,length_cell=mesh['capacitance_length_cell'],width_cell=mesh['capacitance_width_cell'])['matrix']
    if boundary is not None:
        result[boundary][boundary][0]=float(R(1e15)+R(result[boundary][boundary][0]));result[boundary][boundary][1]+=0.
    return result


def normalized_errors(errors):
    result=[]
    for error in errors:
        value={key:error[key]for key in ('section','address','count','observed')if key in error}
        reason=error['reason'];value['reason']='unmapped'if reason.startswith('Cannot access memory')else reason
        result.append(value)
    return result


def compare(case,*,invert=False,capacitance=None):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],allocations_checked=0,events_checked=0,stores_checked=0,faults_checked=0,cache_boundaries=0,cache_words_checked=0,cap_input_words_checked=0,cap_words_checked=0,ind_words_checked=0,predicted_cache_errors=[],differences=[])
    states=case['allocator_states'];heap=Heap(states[0]);via=case['via'];memory=None;records=via_records(case)
    external={}
    for i,group in enumerate(case['contact_groups']):
        external[f'contact_group.{i}']=group['address']
        external.update((f'contact.{i}.{j}',address)for j,address in enumerate(group['contacts']))
    external['geometry.descriptor']=via['shape_address'];external.update((f'geometry.segment.{i}',address)for i,address in enumerate(via['segment_addresses']))
    addresses=external.copy();n=via['matrix']['size']
    plan=iter(combined_network_storage([len(g['contacts'])for g in case['contact_groups']],n,case['matrices']['ind_full']['size'],len(via['indices']),clone_segments=len(via['segments'])))
    boundaries={state['event_count']:state for state in states}
    for index,event in enumerate(case['events']):
        if event['kind']in ('allocate','free'):
            expected=next(plan)
            assert (expected.action,expected.allocator)==(event['kind'],event['allocator'])
            if expected.action=='allocate':
                assert expected.size==event['request'];address=heap.malloc(expected.size);addresses[expected.name]=address;result['allocations_checked']+=1
                if address!=event['address']:result['differences'].append(dict(kind='address',index=index,actual=address,original=event['address']))
            else:
                address=addresses[expected.name];assert address==event['address'];heap.free(address)
            result['events_checked']+=1
        elif event['kind']=='via_write':
            assert memory is not None
            predicted_index,record=records[event['ordinal']];assert predicted_index==event['index']
            address=addresses['ind.output']+16*predicted_index*(via['matrix']['stride']+1)
            assert address==event['address']
            try:before=memory.read(address,16)
            except MemoryFault:
                assert event['before']is None
                try:stamp_memory(memory,address,record)
                except MemoryFault as error:
                    if error.address!=address:raise
                    result['faults_checked']+=1
                else:result['differences'].append(dict(kind='missing-native-load-fault',index=index))
                continue
            if before.hex()!=event['before']:result['differences'].append(dict(kind='before-store',index=index,actual=before.hex(),original=event['before']))
            stamp_memory(memory,address,record);after=memory.read(address,16).hex();result['stores_checked']+=1
            if after!=event['after']:result['differences'].append(dict(kind='after-store',index=index,actual=after,original=event['after']))
        elif event['kind']=='via_return'and invert:
            from reasitic.symmetric import inverse_symmetric
            view=ComplexView(memory,addresses['ind.output'],n,via['matrix']['stride'])
            matrix=inverse_symmetric([[view.get(i,j)for j in range(n)]for i in range(n)])
            for j in range(n):
                for i in range(n):view.set(i,j,matrix[i][j])
        if index+1 in boundaries:
            state=boundaries[index+1]
            if state['label']=='via_entry':
                memory=Memory(heap.address_space);seed(memory,state)
                heap.attach_cache_memory(memory,state['tcache_key'])
                if capacitance is not None:
                    view=ComplexView(memory,addresses['cap.output'],n)
                    original=memory.read(addresses['cap.output'],16*n*n)
                    for j in range(n):
                        for i in range(n):view.set(i,j,complex(*capacitance[i][j]))
                    actual=memory.read(addresses['cap.output'],16*n*n);result['cap_input_words_checked']+=len(actual)//8
                    for offset in range(0,len(actual),8):
                        if actual[offset:offset+8]!=original[offset:offset+8]:result['differences'].append(dict(kind='cap-input-word',offset=offset,actual=actual[offset:offset+8].hex(),original=original[offset:offset+8].hex()))
            result['differences'].extend(state_differences(heap,state))
            if memory is not None:
                result['cache_boundaries']+=1
                actual_errors=normalized_errors(heap.cache_state()[1]);original_errors=normalized_errors(state['errors'])
                if actual_errors!=original_errors:result['differences'].append(dict(kind='cache-errors',boundary=state['label'],actual=actual_errors,original=original_errors))
                result['predicted_cache_errors'].extend(dict(boundary=state['label'],**error)for error in actual_errors)
                original_memory=Memory(heap.address_space);seed(original_memory,state)
                ranges=[(state['tcache_address'],384)]if state['tcache_address']else[]
                ranges.extend((p,8)for chain in state['tcache']for p in chain)
                for address,size in ranges:
                    actual=memory.read(address,size);original=original_memory.read(address,size);result['cache_words_checked']+=size//4
                    if actual!=original:result['differences'].append(dict(kind='cache-bytes',boundary=state['label'],address=address,actual=actual.hex(),original=original.hex()))
                if state['label']=='node':
                    for name,key,enabled in (('cap.output','capacitance',True),('ind.output','inductance',invert)):
                        if not enabled:continue
                        actual=memory.read(addresses[name],16*n*n);original=bytes.fromhex(case['node'][key]);result['cap_words_checked'if name=='cap.output'else'ind_words_checked']+=len(actual)//8
                        for offset in range(0,len(actual),8):
                            if actual[offset:offset+8]!=original[offset:offset+8]:result['differences'].append(dict(kind=key+'-word',offset=offset,actual=actual[offset:offset+8].hex(),original=original[offset:offset+8].hex()))
            if result['differences']:break
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/shared_heap_original.json.gz');parser.add_argument('--inverse',action='store_true');parser.add_argument('--ported-cap',action='store_true');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        cap=ported_capacitance(case)if options.ported_cap else None
        results.append(compare(case,invert=options.inverse,capacitance=cap))
        if options.ported_cap:print(case['label']+'/'+case['cache_mode']+': '+str(len(results[-1]['differences']))+' differences',flush=True)
    report={key:sum(case[key]for case in results)for key in ('allocations_checked','events_checked','stores_checked','faults_checked','cache_boundaries','cache_words_checked','cap_input_words_checked','cap_words_checked','ind_words_checked')}
    report.update(cases=len(results),predicted_cache_errors=sum(len(case['predicted_cache_errors'])for case in results),differences=sum(len(case['differences'])for case in results),results=results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

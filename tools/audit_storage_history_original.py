"""Replay numerical/cache stores from earlier free bytes, without via seeding."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage
from reasitic.bridge import _mesh
from reasitic.memory import UnknownMemory,MemoryFault
from reasitic.storage_history import StorageHistory,symmetric_inverse_storage
from reasitic.vias import stamp_memory
from audit_cap_prelude_original import compare as prelude,dimensions
from audit_cap_storage_original import ported_buffers
from audit_contact_storage_original import ported_records
from audit_shared_heap_original import ported_impedance,via_records,seed,normalized_errors
from audit_allocator_original import state_differences


def compare(case,initial_regions=(),*,context=None,return_state=False,console=None):
    memory=None
    if context is None:prefix,heap,addresses=prelude(case,return_state=True)
    else:
        if initial_regions:raise ValueError('A continuing history cannot replace its initial bytes')
        prefix,heap,addresses,memory=context
    result=dict(label=case['label'],cache_mode=case['cache_mode'],differences=list(prefix['differences']),
                events_checked=0,allocations_checked=0,stores_checked=0,faults_checked=0,unknown_targets=0,cap_words_checked=0,ind_words_checked=0,cache_words_checked=0,cap_input_words_checked=0,ind_input_words_checked=0,cache_boundaries=0,predicted_cache_errors=[],
                workspace_arrays_checked=0,workspace_bytes_checked=0,heap_words_checked=0,unknown_heap_bytes=0,heap_boundaries_checked=0)
    if result['differences']:return (result,heap,addresses,memory)if return_state else result
    prepared=ported_impedance(case);contacts=ported_records(case);inverse_storage={}
    if context is None:buffers=ported_buffers(case,inverse_storage=inverse_storage);producer=None
    else:
        from reasitic.cache_storage import CacheStorage
        from reasitic import Technology
        from reasitic.bridge import _frequency
        tables=CacheStorage(memory,case['cache_inputs'],Technology.from_text(case['request']['technology']),_frequency(case['request']))
        buffers={}
        producer=lambda view:ported_buffers(case,inverse_storage=inverse_storage,table_provider=tables,potential_view=view)
    inverse_storage.update(symmetric_inverse_storage(prepared.full,'ind.full_inverse'))
    from reasitic import Technology
    technology=Technology.from_text(case['request']['technology']);records=via_records(case);boundary=None
    if case['request']['action']=='calctrans':
        from reasitic.bridge import _shapes
        from reasitic.solver import discretize
        shapes=_shapes(case['request'],technology);mesh=_mesh(case['request'],technology)
        first=discretize(shapes[case['request']['first_winding']],mesh['capacitance_length_cell'],mesh['length_cell'])
        boundary=sum(s.metal<len(technology.metals)for s in first.segments)
    scope=next(s for s in case['allocator_states']if s['label']=='scope')
    if records:inverse_storage.update(symmetric_inverse_storage(prepared.reduced_y,'ind.reduced_inverse'))
    if context is None:
        addresses['geometry.descriptor']=case['via']['shape_address'];addresses.update((f'geometry.segment.{i}',p)for i,p in enumerate(case['via']['segment_addresses']))
        key=scope['tcache_key']
    else:
        key=heap._cache_key
        heap.require_cache_memory(memory,key);heap.attach_cache_memory(memory,key)
    geometry_addresses=[addresses[f'geometry.segment.{i}']for i in range(len(prepared.meshed.segments))]
    history=StorageHistory(heap,addresses,initial_regions=initial_regions,key=key,contacts=contacts,capacitance=buffers,impedance=prepared,technology=technology,mesh=_mesh(case['request'],technology),geometry_addresses=geometry_addresses,via_records=records,termination_boundary=boundary,termination_ohm=float(case['request'].get('termination_ohm',0)),inverse_storage=inverse_storage,geometry_shape_address=addresses['geometry.descriptor'],memory=memory,capacitance_producer=producer)
    memory=history.memory;counts,*_=dimensions(case)
    plan=iter(combined_network_storage(counts,len(prepared.groups),prepared.filaments,len(records),clone_segments=len(prepared.meshed.segments)))
    workspaces={r['event_index']:r for r in case.get('workspace_storage',())}if context is not None else{}
    def check_bytes(address,native,kind,**identity):
        try:actual=memory.read(address,len(native))
        except UnknownMemory:actual=None
        if actual==native:return
        for offset in range(0,len(native),4):
            size=min(4,len(native)-offset)
            try:word=actual[offset:offset+size]if actual is not None else memory.read(address+offset,size)
            except UnknownMemory:
                if kind=='heap-word':result['unknown_heap_bytes']+=size
                result['differences'].append(dict(kind='unknown-'+kind,address=address+offset,size=size,**identity));continue
            if word!=native[offset:offset+size]:result['differences'].append(dict(kind=kind,address=address+offset,offset=offset,actual=word.hex(),original=native[offset:offset+size].hex(),**identity))
    def check_cache(state):
        if heap._cache_key!=state['tcache_key']:result['differences'].append(dict(kind='cache-key',boundary=state['label'],actual=heap._cache_key,original=state['tcache_key']))
        result['differences'].extend(state_differences(heap,state,memory=memory if context is not None else None));errors=heap.cache_state()[1]
        native_errors=[e for e in state['errors']if e['section'].startswith('tcache.')]
        if normalized_errors(errors)!=normalized_errors(native_errors):result['differences'].append(dict(kind='cache-errors',boundary=state['label']))
        other_errors=[e for e in state['errors']if e['section']!='chunks'and not e['section'].startswith('tcache.')]
        if other_errors:result['differences'].append(dict(kind='unsupported-allocator-errors',boundary=state['label'],original=other_errors))
        result['predicted_cache_errors'].extend(dict(boundary=state['label'],**error)for error in errors)
        expected=type(memory)(heap.address_space);seed(expected,state)
        ranges=[(heap.cache_address,384)]if heap.tcache_enabled else[]
        ranges.extend((p,8)for chain in state['tcache']for p in chain)
        for address,size in ranges:
            actual=memory.read(address,size);native=expected.read(address,size);result['cache_words_checked']+=size//4
            if actual!=native:result['differences'].append(dict(kind='cache-word',boundary=state['label'],address=address,actual=actual.hex(),original=native.hex()))
        result['cache_boundaries']+=1
        if context is not None:
            for region in state['memory_regions']:
                native=bytes.fromhex(region['data']);check_bytes(region['address'],native,'heap-word',boundary=state['label'])
                result['heap_words_checked']+=len(native)//4
            result['heap_boundaries_checked']+=1
        return expected
    begun=False;stamping=False
    for event_index,event in enumerate(case['events']):
        if event['kind']in ('allocate','free'):
            expected=next(plan);assert (expected.action,expected.allocator)==(event['kind'],event['allocator'])
            if console is not None:
                console.position['events']=event_index;console.before_numerical(expected,prepared.filaments,bool(records))
            history.before(expected)
            if expected.action=='allocate':
                assert expected.size==event['request']
                try:address=heap.malloc(expected.size)
                except UnknownMemory as error:
                    result['differences'].append(dict(kind='unknown-allocator-read',name=expected.name,address=error.address));break
                addresses[expected.name]=address;history.allocated(expected,address);result['allocations_checked']+=1
                if address!=event['address']:result['differences'].append(dict(kind='allocation-address',name=expected.name,actual=address,original=event['address']))
            else:
                address=addresses[expected.name];assert address==event['address']
                if event_index in workspaces:
                    observed=workspaces[event_index];assert observed['address']==address and observed['size']==history.sizes[expected.name]
                    native=bytes.fromhex(observed['data']);check_bytes(address,native,'workspace-word',name=expected.name)
                    result['workspace_arrays_checked']+=1;result['workspace_bytes_checked']+=len(native)
                try:heap.free(address)
                except UnknownMemory as error:
                    result['differences'].append(dict(kind='unknown-allocator-read',name=expected.name,address=error.address));break
            result['events_checked']+=1
            if console is not None:
                console.position['events']=event_index+1;console.after_numerical(expected)
        elif event['kind']=='via_entry':
            if context is not None:
                if addresses['geometry.descriptor']!=case['via']['shape_address']:result['differences'].append(dict(kind='via-shape-owner',actual=addresses['geometry.descriptor'],original=case['via']['shape_address']))
                if geometry_addresses!=case['via']['segment_addresses']:result['differences'].append(dict(kind='via-segment-owners',actual=geometry_addresses,original=case['via']['segment_addresses']))
            heap.attach_cache_memory(memory,key);begun=True
            expected=check_cache(next(s for s in case['allocator_states']if s['label']=='via_entry'));n=len(prepared.groups)
            for name,key in (('cap.output','cap_input_words_checked'),('ind.output','ind_input_words_checked')):
                actual=memory.read(addresses[name],16*n*n);native=expected.read(addresses[name],16*n*n)
                for offset in range(0,len(actual),8):
                    if actual[offset:offset+8]!=native[offset:offset+8]:result['differences'].append(dict(kind='input-word',name=name,offset=offset,actual=actual[offset:offset+8].hex(),original=native[offset:offset+8].hex()))
                result[key]+=len(actual)//8
        elif event['kind']=='via_write':
            assert begun
            if not stamping:history.begin_stamps();stamping=True
            index,record=records[event['ordinal']];address=addresses['ind.output']+16*index*(len(prepared.groups)+1)
            assert index==event['index']and address==event['address']
            try:before=memory.read(address,16)
            except UnknownMemory:
                result['unknown_targets']+=1;result['differences'].append(dict(kind='unknown-target',address=address,index=index));continue
            except MemoryFault:
                assert event['before']is None
                try:stamp_memory(memory,address,record)
                except MemoryFault as error:
                    assert error.address==address;result['faults_checked']+=1
                else:result['differences'].append(dict(kind='missing-native-fault',address=address))
                continue
            if before.hex()!=event['before']:result['differences'].append(dict(kind='before-store',address=address,index=index,actual=before.hex(),original=event['before']))
            stamp_memory(memory,address,record);after=memory.read(address,16).hex();result['stores_checked']+=1
            if after!=event['after']:result['differences'].append(dict(kind='after-store',address=address,index=index,actual=after,original=event['after']))
        elif event['kind']=='via_return':history.finish_stamps()
    if case['node']is not None and(context is not None or not result['differences']):
        state=next(s for s in case['allocator_states']if s['label']=='node')
        check_cache(state)
        n=len(prepared.groups)
        for name,key in (('cap.output','capacitance'),('ind.output','inductance')):
            actual=memory.read(addresses[name],16*n*n);native=bytes.fromhex(case['node'][key])
            for offset in range(0,len(actual),8):
                if actual[offset:offset+8]!=native[offset:offset+8]:result['differences'].append(dict(kind='node-word',name=name,offset=offset,actual=actual[offset:offset+8].hex(),original=native[offset:offset+8].hex()))
            result['cap_words_checked'if key=='capacitance'else'ind_words_checked']+=len(actual)//8
    if context is not None and result['workspace_arrays_checked']!=len(workspaces):result['differences'].append(dict(kind='workspace-count',actual=result['workspace_arrays_checked'],original=len(workspaces)))
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz').read_bytes()));initial=json.loads(gzip.decompress((ROOT/'tests/fixtures/initial_storage_memory_original.json.gz').read_bytes()))
    assert len(fixture['cases'])==len(initial['cases'])==130
    from project_initial_storage_memory_original import expand
    results=[]
    for case,entry in zip(fixture['cases'],initial['cases']):
        assert (case['label'],case['cache_mode'])==(entry['label'],entry['cache_mode'])
        result=compare(case,expand(initial,entry));results.append(result);print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','stores_checked','faults_checked','unknown_targets','cap_words_checked','ind_words_checked','cache_words_checked','cache_boundaries','cap_input_words_checked','ind_input_words_checked'):report[key]=sum(r[key]for r in results)
    report['predicted_cache_errors']=sum(len(r['predicted_cache_errors'])for r in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

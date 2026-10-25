"""Source filament tables, full lifetimes and cleanup on the earlier heap."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage
from reasitic.filament_storage import FilamentLayout
from reasitic.bridge import _mesh
from audit_geometry_setup_original import compare as geometry_setup
from audit_shared_heap_original import ported_inductance_geometry
from audit_cap_prelude_original import dimensions
from audit_allocator_original import state_differences

TABLES={'ind.extra_segments','ind.segments','ind.width_counts','ind.thickness_counts','ind.via_indices'}


def compare(case,*,return_state=False):
    prefix,heap,addresses,memory=geometry_setup(case,return_state=True)
    report=dict(label=case['label'],cache_mode=case['cache_mode'],differences=list(prefix['differences']),events_checked=0,allocations_checked=0,tables_checked=0,table_bytes_checked=0,released_tables_checked=0,released_table_bytes_checked=0,geometry_bytes_checked=0,cleanup_records_checked=0,allocator_boundaries_checked=0)
    def check(kind,actual,expected,**where):
        if actual!=expected:report['differences'].append(dict(kind=kind,actual=actual,original=expected,**where))
    if report['differences']:return report
    shape,technology=ported_inductance_geometry(case);layout=FilamentLayout(shape,len(technology.metals));mesh=_mesh(case['request'],technology)
    parents=[addresses[f'geometry.segment.{i}']for i in range(len(shape.segments))];pointers=layout.pointers(memory,parents,addresses=addresses)
    counts=layout.counts(mesh);filaments=sum(y*z for y,z in counts);contact_counts,*_=dimensions(case);eddy=case['request'].get('eddy',False)
    plan=iter(combined_network_storage(contact_counts,len(layout.conductors),filaments,len(layout.via_indices),clone_segments=len(shape.segments),group_segments=layout.group_segments,clone_children=layout.clone_children,eddy=eddy,eddy_matrix_size=layout.eddy_matrix_size(technology,int(eddy))))
    workspaces={w['event_index']:w for w in case['workspace_storage']};seen=False;produced={}
    for index,event in enumerate(case['events']):
        if event['kind']in('allocate','free'):
            expected=next(plan,None)
            if expected is None:report['differences'].append(dict(kind='filament-extra-native-event',event=index));break
            if(event['kind'],event['allocator'])!=(expected.action,expected.allocator):report['differences'].append(dict(kind='filament-interface',event=index,actual=expected.__dict__,original=event));break
            if expected.action=='allocate':
                layout.before(expected.name,memory,addresses,pointers,mesh)
                check('filament-request',expected.size,event['request'],event=index,name=expected.name)
                address=heap.malloc(expected.size);addresses[expected.name]=address;report['allocations_checked']+=1
            else:
                address=addresses[expected.name]
                if expected.name in TABLES:
                    observed=workspaces[index];target=bytes.fromhex(observed['data']);actual=memory.read(address,len(target))
                    check('filament-released-table-owner',address,observed['address'],name=expected.name)
                    check('filament-released-table',actual.hex(),target.hex(),name=expected.name)
                    report['released_tables_checked']+=1;report['released_table_bytes_checked']+=len(target)
                if expected.name.startswith('geometry.segment.'):report['cleanup_records_checked']+=1
                heap.free(address)
            check('filament-allocation-owner',address,event['address'],event=index,name=expected.name);report['events_checked']+=1
        elif event['kind']=='matrix'and event['label']=='ind_full':
            seen=True;native=case['filament_context']
            for key,actual in(('groups',len(layout.conductors)),('segment_count',len(layout.records)),('filaments',filaments),('via_count',len(layout.via_indices))):check('filament-'+key,actual,native[key])
            for name,table in native['arrays'].items():
                key='ind.'+name;address=addresses[key];target=bytes.fromhex(table['data']);actual=memory.read(address,len(target))
                produced[key]=actual
                check('filament-table-owner',address,table['address'],name=key);check('filament-table',actual.hex(),target.hex(),name=key)
                report['tables_checked']+=1;report['table_bytes_checked']+=len(target)
            geometry=native['geometry'];check('filament-shape-owner',addresses['geometry.descriptor'],geometry['address'])
            for record in[geometry,*[node for s in geometry['segments']for node in[s,*s['children']]]]:
                target=bytes.fromhex(record['data']);actual=memory.read(record['address'],len(target));check('filament-geometry',actual.hex(),target.hex(),address=record['address']);report['geometry_bytes_checked']+=len(target)
    check('filament-context-observed',seen,True)
    remaining=list(plan)
    if remaining:report['differences'].append(dict(kind='filament-missing-native-events',names=[e.name for e in remaining]))
    if case['node']is not None:
        report['differences'].extend(state_differences(heap,next(s for s in case['allocator_states']if s['label']=='node')));report['allocator_boundaries_checked']+=1
    if return_state:return report,heap,addresses,memory,layout,produced
    return report


def compare_branch_history(case,*,return_state=False):
    """Actual numerical stores through first node on the earlier geometry heap."""
    from reasitic.storage_history import StorageHistory,symmetric_inverse_storage
    from reasitic.contact_storage import write_prepared
    from reasitic.vias import stamp_memory
    from audit_shared_heap_original import ported_impedance,via_records
    from audit_cap_storage_original import ported_buffers
    from audit_contact_storage_original import ported_records
    prefix,heap,addresses,memory=geometry_setup(case,return_state=True)
    report=dict(label=case['label'],cache_mode=case['cache_mode'],differences=list(prefix['differences']),events_checked=0,workspace_arrays_checked=0,workspace_bytes_checked=0,node_words_checked=0,via_stores_checked=0,via_words_checked=0)
    if report['differences']:return report
    def check(kind,actual,expected,**where):
        if actual!=expected:report['differences'].append(dict(kind=kind,actual=actual,original=expected,**where))
    prepared=ported_impedance(case);shape,technology=ported_inductance_geometry(case);mesh=_mesh(case['request'],technology);contacts=ported_records(case);inverse={};buffers=ported_buffers(case,inverse_storage=inverse)
    inverse.update(symmetric_inverse_storage(prepared.full,'ind.full_inverse'))
    records=via_records(case);eddy=case['request'].get('eddy',False)
    if records or eddy:inverse.update(symmetric_inverse_storage(prepared.reduced_y,'ind.reduced_inverse'))
    boundary=None
    if case['request']['action']=='calctrans':
        from reasitic.bridge import _shapes
        from reasitic.solver import discretize
        first=discretize(_shapes(case['request'],technology)[case['request']['first_winding']],mesh['capacitance_length_cell'],mesh['length_cell'])
        boundary=sum(s.metal<len(technology.metals)for s in first.segments)
    write_prepared(memory,contacts,addresses)
    history=StorageHistory(heap,addresses,initial_regions=(),key=heap._cache_key,contacts=contacts,capacitance=buffers,impedance=prepared,technology=technology,mesh=mesh,geometry_addresses=[addresses[f'geometry.segment.{i}']for i in range(len(shape.segments))],via_records=records,termination_boundary=boundary,termination_ohm=float(case['request'].get('termination_ohm',0)),inverse_storage=inverse,geometry_shape_address=addresses['geometry.descriptor'],memory=memory)
    layout=history.filament_layout;plan=iter(combined_network_storage([len(g.contacts)for g in contacts],len(layout.conductors),prepared.filaments,len(records),clone_segments=len(shape.segments),group_segments=layout.group_segments,clone_children=layout.clone_children,eddy=eddy,eddy_matrix_size=layout.eddy_matrix_size(technology,int(eddy))))
    targets={w['event_index']:w for w in case['workspace_storage']};produced={};stamps=[];stamp_count=0
    for index,event in enumerate(case['events']):
        if event['kind']in('allocate','free'):
            item=next(plan);check('branch-history-interface',(item.action,item.allocator),(event['kind'],event['allocator']),event=index);history.before(item)
            if item.action=='allocate':
                check('branch-history-request',item.size,event['request'],name=item.name)
                address=heap.malloc(item.size);addresses[item.name]=address;history.allocated(item,address)
                if item.name=='ind.via_scratch':
                    history.begin_stamps()
                    # Execute every source via, independently of later native
                    # observer records. These stamps allocate/free no storage.
                    for group,record in records:
                        target=addresses['ind.output']+16*group*(len(prepared.groups)+1)
                        before=memory.read(target,16)
                        if stamp_memory(memory,target,record):stamps.append((group,target,before,memory.read(target,16)))
            else:
                address=addresses[item.name]
                if index in targets:
                    original=targets[index];check('branch-history-workspace-owner',address,original['address'],name=item.name)
                    check('branch-history-workspace-size',history.sizes[item.name],original['size'],name=item.name)
                    expected=bytes.fromhex(original['data']);actual=memory.read(address,len(expected));produced[item.name]=actual
                    check('branch-history-workspace',actual.hex(),expected.hex(),name=item.name)
                    report['workspace_arrays_checked']+=1;report['workspace_bytes_checked']+=len(expected)
                heap.free(address);history.released(item)
            check('branch-history-address',address,event['address'],name=item.name);report['events_checked']+=1
        elif event['kind']=='via_entry':
            check('branch-history-via-matrix-owner',addresses['ind.output'],case['via']['matrix']['data'])
            check('branch-history-via-matrix-size',len(prepared.groups),case['via']['matrix']['size'])
            check('branch-history-via-shape-owner',addresses['geometry.descriptor'],case['via']['shape_address'])
        elif event['kind']=='via_write':
            group,address,before,after=stamps[stamp_count];stamp_count+=1
            check('branch-history-via-ordinal',stamp_count-1,event['ordinal'])
            check('branch-history-via-index',group,event['index']);check('branch-history-via-owner',address,event['address'])
            check('branch-history-via-before',before.hex(),event['before']);check('branch-history-via-after',after.hex(),event['after']);report['via_stores_checked']+=1;report['via_words_checked']+=4
        elif event['kind']=='via_return':history.finish_stamps()
    check('branch-history-remaining-events',[e.name for e in plan],[])
    check('branch-history-workspace-count',report['workspace_arrays_checked'],len(targets))
    check('branch-history-via-count',report['via_stores_checked'],len(records))
    for name,key in(('cap.output','capacitance'),('ind.output','inductance')):
        target=bytes.fromhex(case['node'][key]);actual=memory.read(addresses[name],len(target))
        produced[name]=actual;check('branch-history-node',actual.hex(),target.hex(),name=name)
        report['node_words_checked']+=len(target)//8
    report['differences'].extend(state_differences(heap,next(s for s in case['allocator_states']if s['label']=='node')))
    if return_state:return report,heap,addresses,memory,produced
    return report


def run(fixture):
    results=[compare(case)for case in fixture['cases']];report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('events_checked','allocations_checked','tables_checked','table_bytes_checked','released_tables_checked','released_table_bytes_checked','geometry_bytes_checked','cleanup_records_checked','allocator_boundaries_checked'):report[key]=sum(r[key]for r in results)
    from audit_contact_storage_original import compare as contacts
    contact_results=[contacts(c)for c in fixture['cases']]
    report['contacts']=dict(cases=len(contact_results),differences=sum(len(r['differences'])for r in contact_results),results=contact_results)
    for key in('objects_checked','bytes_checked','unknown_bytes'):report['contacts'][key]=sum(r[key]for r in contact_results)
    histories=[compare_branch_history(c)for c in fixture['cases']]
    report['histories']=dict(cases=len(histories),differences=sum(len(r['differences'])for r in histories),results=histories)
    for key in('events_checked','workspace_arrays_checked','workspace_bytes_checked','node_words_checked','via_stores_checked','via_words_checked'):report['histories'][key]=sum(r[key]for r in histories)
    report['differences']+=report['contacts']['differences']+report['histories']['differences']
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_filament_storage_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],case['cache_mode'],len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k not in('results','contacts','histories')})
    for key in('contacts','histories'):print(key,{k:v for k,v in report[key].items()if k!='results'})
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

"""Strict node work arrays, whole heaps, output ports and first driver cleanup."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import node_storage
from reasitic.console_storage import ConsoleStorage
from reasitic.node_storage import NodeStorage
from reasitic.memory import UnknownMemory
from reasitic.heap import HeapCorruption
from reasitic.bridge import _frequency
from audit_driver_history_original import compare as driver
from audit_allocator_original import state_differences
from capture_node_history_original import expand_case


def compare(fixture,entry,*,return_state=False,console=None,initial_regions=()):
    if console is None:console=ConsoleStorage(entry['console_inputs'])
    console.position['post_events']=0
    before,heap,addresses,memory=driver(fixture,entry,return_state=True,console=console,initial_regions=initial_regions)
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],before=before,differences=list(before['differences']),events_checked=0,allocations_checked=0,buffers_checked=0,buffer_bytes_checked=0,heap_boundaries_checked=0,heap_words_checked=0,unknown_heap_bytes=0,port_words_checked=0,console_calls_checked=0,faults_checked=0)
    case=expand_case(fixture,entry)
    def check(address,native,kind,**identity):
        try:complete=memory.read(address,len(native))
        except UnknownMemory:complete=None
        if complete==native:return
        for offset in range(0,len(native),4):
            size=min(4,len(native)-offset)
            try:actual=complete[offset:offset+size]if complete is not None else memory.read(address+offset,size)
            except UnknownMemory:
                result['unknown_heap_bytes']+=size;result['differences'].append(dict(kind='unknown-'+kind,address=address+offset,**identity));continue
            if actual!=native[offset:offset+size]:result['differences'].append(dict(kind=kind,address=address+offset,actual=actual.hex(),original=native[offset:offset+size].hex(),**identity))
    def boundary(label):
        state=next(s for s in case['post_states']if s['label']==label)
        result['differences'].extend(state_differences(heap,state,memory=memory))
        for region in state['memory_regions']:
            native=bytes.fromhex(region['data']);check(region['address'],native,'post-heap-word',boundary=label);result['heap_words_checked']+=len(native)//4
        result['heap_boundaries_checked']+=1
    def ports(original,actual):
        for key,record in zip(('y11','y12','y21','y22'),original):
            z=actual[key];raw=struct.pack('<2d',z.real,z.imag);native=bytes.fromhex(record['data'])
            for offset in range(0,16,8):
                if raw[offset:offset+8]!=native[offset:offset+8]:result['differences'].append(dict(kind='node-port',name=key,offset=offset,actual=raw[offset:offset+8].hex(),original=native[offset:offset+8].hex()))
                result['port_words_checked']+=1
    if case['node']is not None and not result['differences']:
        # The source CAP output extent is the number of conductor groups,
        # reconstructed from earlier geometry, never the later node size.
        from audit_shared_heap_original import ported_inductance_geometry
        shape,technology=ported_inductance_geometry(case);n=sum(segment.metal<len(technology.metals)for segment in shape.segments)
        for key,actual in (('size',n),('cap_address',addresses['cap.output']),('ind_address',addresses['ind.output'])):
            if actual!=case['post_node'][key]:result['differences'].append(dict(kind='node-owner',field=key,actual=actual,original=case['post_node'][key]))
        history=NodeStorage(memory,addresses,n);plan=node_storage(n)
        console.position['events']=len(case['events']);console.begin_nodes(n)
        if len(plan)!=len(case['post_events']):result['differences'].append(dict(kind='post-event-count',actual=len(plan),original=len(case['post_events'])))
        buffers={record['event_index']:record for record in case['post_buffers']}
        solved=False
        for index,(event,native)in enumerate(zip(plan,case['post_events'])):
            if (event.action,event.allocator)!=(native['kind'],native['allocator']):result['differences'].append(dict(kind='post-interface',index=index));break
            console.position['post_events']=index
            try:
                if event.action=='allocate':
                    if event.size!=native['request']:result['differences'].append(dict(kind='post-request',index=index,actual=event.size,original=native['request']));break
                    address=heap.malloc(event.size);addresses[event.name]=address;history.allocated(event,address);result['allocations_checked']+=1
                    if address!=native.get('address'):result['differences'].append(dict(kind='post-address',name=event.name,actual=address,original=native.get('address')))
                else:
                    if not solved:
                        history.solve();solved=True;boundary('node_release')
                    if event.name=='ind.output':
                        boundary('node_return');ports(case['post_output']['ports'],history.ports)
                        if case['post_output']['status']!=1:result['differences'].append(dict(kind='node-status',actual=1,original=case['post_output']['status']))
                        cap=bytes.fromhex(case['post_output']['capacitance']);check(addresses['cap.output'],cap,'node-cap-word')
                        console.report_nodes(history.ports,_frequency(case['request']),transformer=case['request']['action']=='calctrans')
                    address=addresses[event.name]
                    if address!=native['address']:result['differences'].append(dict(kind='post-free-owner',name=event.name,actual=address,original=native['address']))
                    record=buffers[index];expected_size=history.sizes.get(event.name,16*n*n)
                    if record['address']!=address or record['size']!=expected_size:result['differences'].append(dict(kind='post-buffer-owner',name=event.name))
                    check(address,bytes.fromhex(record['data']),'node-buffer-word',name=event.name);result['buffers_checked']+=1;result['buffer_bytes_checked']+=record['size']
                    heap.free(address)
            except HeapCorruption as error:
                if case['signal']!=6 or native.get('returned'):result['differences'].append(dict(kind='unexpected-allocator-fault',reason=str(error)))
                else:result['faults_checked']+=1;boundary('post_fault')
                break
            except (ValueError,NotImplementedError)as error:
                result['differences'].append(dict(kind='post-runtime',reason=str(error),name=event.name));break
            result['events_checked']+=1;console.position['post_events']=index+1
        if case['post_driver']is not None and result['events_checked']==len(plan):
            boundary('driver_return');ports(case['post_driver']['ports'],history.ports)
            if case['post_driver']['status']!=1:result['differences'].append(dict(kind='driver-status',actual=1,original=case['post_driver']['status']))
        if result['buffers_checked']!=len(buffers):result['differences'].append(dict(kind='post-buffer-count',actual=result['buffers_checked'],original=len(buffers)))
    original=case['console_calls'];result['console_calls_checked']=min(len(console.calls),len(original))
    if len(console.calls)!=len(original):result['differences'].append(dict(kind='console-call-count',actual=len(console.calls),original=len(original)))
    for index,(actual,expected)in enumerate(zip(console.calls,original)):
        if actual!=expected:result['differences'].append(dict(kind='console-call',index=index,actual=actual,original=expected))
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/node_history_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','buffers_checked','buffer_bytes_checked','heap_boundaries_checked','heap_words_checked','unknown_heap_bytes','port_words_checked','console_calls_checked','faults_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

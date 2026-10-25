"""One source heap through consecutive native JOINSHUNT command returns."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.geometry_storage import GeometryStorage
from reasitic.heap import Heap
from reasitic.memory import Memory
from audit_allocator_original import state_differences


def compare(case,*,return_state=False):
    context=case['context'];initial=case['allocator_states'][0];heap=Heap(initial);memory=Memory(heap.address_space)
    for region in context['memory_regions']:memory.write(region['address'],bytes.fromhex(region['data']))
    memory.write(initial['arena_address'],bytes.fromhex(initial['arena_bytes']))
    key=next((memory.u32(chain[0]+4)for chain in initial['tcache']if chain),None)
    if key is None:raise ValueError('Initial cache key must be observed before this component')
    heap.observe_cache_stores(memory,key);heap.observe_header_stores(memory)
    geometry=GeometryStorage(heap,memory,context['head'],selected=context['selected'])
    result=dict(label=case['label'],commands_checked=0,events_checked=0,allocations_checked=0,geometry_bytes_checked=0,phase_words_checked=0,allocator_boundaries_checked=0,differences=[])
    differences=result['differences']
    def check(kind,actual,expected,**where):
        if actual!=expected:differences.append(dict(kind=kind,actual=actual,original=expected,**where))
    def check_bytes(record,command):
        target=bytes.fromhex(record['data']);actual=memory.read(record['address'],len(target));result['geometry_bytes_checked']+=len(target)
        for offset in range(0,len(target),4):check('shunt-dispatch-word',actual[offset:offset+4].hex(),target[offset:offset+4].hex(),command=command,address=record['address'],offset=offset)
    check('shunt-dispatch-return-count',len(case['outputs']),len(case['commands']))
    for index,names in enumerate(case['commands']):
        # Names are public command inputs. Later native parser pointers and
        # snapshots never choose an owner or repair this continuing heap.
        arguments=[next(address for address in geometry.shapes()if geometry.text(address)==name.encode())for name in names]
        check('shunt-dispatch-arguments',arguments,case['command_inputs'][index]['arguments'],command=index)
        check('shunt-dispatch-entry-events',len(geometry.events),case['command_inputs'][index]['event_count'],command=index)
        geometry.dispatch_shunt(arguments,f'shunt.{index}');result['commands_checked']+=1
        native=case['outputs'][index]
        check('shunt-dispatch-events',len(geometry.events),native['event_count'],command=index)
        check('shunt-dispatch-head',geometry.head,native['head'],command=index);check('shunt-dispatch-selected',geometry.selected,native['selected'],command=index)
        check('shunt-dispatch-shapes',list(geometry.shapes()),[s['address']for s in native['shapes']],command=index)
        for shape in native['shapes']:
            check_bytes(shape,index);phase=struct.unpack_from('<I',bytes.fromhex(shape['data']),0xac)[0];check('shunt-dispatch-phase',memory.u32(shape['address']+0xac),phase,command=index,address=shape['address']);result['phase_words_checked']+=1
            check('shunt-dispatch-primary-owners',list(geometry.segments(shape['address'])),[s['address']for s in shape['segments']],command=index)
            for segment in shape['segments']:
                check_bytes(segment,index);check('shunt-dispatch-secondary-owners',list(geometry.children(segment['address'])),[s['address']for s in segment['children']],command=index,parent=segment['address'])
                for child in segment['children']:check_bytes(child,index)
        differences.extend(state_differences(heap,case['allocator_states'][index+1],memory=memory));result['allocator_boundaries_checked']+=1
    check('shunt-dispatch-total-events',len(geometry.events),len(case['events']))
    for index,((event,address),native)in enumerate(zip(geometry.events,case['events'])):
        check('shunt-dispatch-interface',[event.action,event.allocator],[native['kind'],native['allocator']],event=index)
        if event.action=='allocate':check('shunt-dispatch-request',event.size,native['request'],event=index);result['allocations_checked']+=1
        check('shunt-dispatch-address',address,native['address'],event=index);result['events_checked']+=1
    if return_state:return result,geometry,heap,memory
    return result


def run(fixture):
    results=[compare(c)for c in fixture['cases']];report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('commands_checked','events_checked','allocations_checked','geometry_bytes_checked','phase_words_checked','allocator_boundaries_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_dispatch_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

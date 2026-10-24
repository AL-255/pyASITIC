"""Predict contact/cache lifetimes and every address from an earlier boundary."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.allocation_plan import capacitance_prelude_storage
from reasitic.heap import Heap
from audit_allocator_original import state_differences


def dimensions(case):
    from reasitic.bridge import _shapes,_mesh
    from reasitic.solver import discretize
    from reasitic.network import _join_for_pads
    from reasitic.potential import _contacts
    request=case['request'];technology=Technology.from_text(request['technology']);shapes=_shapes(request,technology);mesh=_mesh(request,technology)
    if request['action']=='pi2':shape=discretize(shapes[request['winding']],mesh['capacitance_length_cell'],mesh['length_cell'])
    else:
        first,second=(discretize(shapes[request[key]],mesh['capacitance_length_cell'],mesh['length_cell'])for key in ('first_winding','second_winding'))
        second.segments.reverse();shape=_join_for_pads(first,second)
    chip=technology.chip;nx=int(chip['fftx']);ny=int(chip['ffty'])
    groups=_contacts(shape,technology,nx,ny,float(chip['chipx']),float(chip['chipy']),mesh['capacitance_length_cell'],mesh['capacitance_width_cell'])
    return [len(group)for group in groups],len(technology.metals),len(technology.substrate),nx


def compare(case,*,return_state=False,heap=None):
    states=case['allocator_states'];initial=states[0];final=next(s for s in states if s['label']=='scope')
    assert initial['label']=='contacts_entry';counts,metals,substrates,nx=dimensions(case);abi=initial['io_abi']
    file_bytes=abi['file_plus']+abi['lock']+abi['wide_data']
    block=abi['filesystem_block_size'];buffer_bytes=min(abi['buffer_default'],block)if block>0 else abi['buffer_default']
    plan=capacitance_prelude_storage(counts,metals,substrates,nx,cache_mode=case.get('prelude_cache_mode',case['cache_mode']),file_bytes=file_bytes,buffer_bytes=buffer_bytes)
    observed=case['prefix_events'];heap=Heap(initial)if heap is None else heap;addresses={};live=set();differences=[]
    if len(plan)!=len(observed):differences.append(dict(kind='event-count',actual=len(plan),original=len(observed)))
    allocations=0
    for index,(expected,event)in enumerate(zip(plan,observed)):
        if (expected.action,expected.allocator)!=(event['kind'],event['allocator']):differences.append(dict(kind='interface',index=index,actual=expected.__dict__,original=event));break
        if expected.action=='allocate':
            if expected.size!=event['request']:differences.append(dict(kind='request',index=index,name=expected.name,actual=expected.size,original=event['request']));break
            address=heap.malloc(expected.size);addresses[expected.name]=address;live.add(expected.name);allocations+=1
            if address!=event['address']:differences.append(dict(kind='address',index=index,name=expected.name,actual=address,original=event['address']));break
        else:
            address=addresses[expected.name]
            if address!=event['address']:differences.append(dict(kind='free-identity',index=index,name=expected.name,actual=address,original=event['address']));break
            chunk=heap.mapped.get(address-8)or heap.chunks[address-8]
            if chunk.size!=event['chunk_size']:differences.append(dict(kind='chunk-size',index=index,name=expected.name,actual=chunk.size,original=event['chunk_size']));break
            heap.free(address);live.remove(expected.name)
    if not differences:
        differences.extend(state_differences(heap,final))
        expected_live=set()
        for i,group in enumerate(case['contact_groups']):
            for name,address in [(f'contact_group.{i}',group['address']),*((f'contact.{i}.{j}',address)for j,address in enumerate(group['contacts']))]:
                expected_live.add(name)
                if addresses.get(name)!=address:differences.append(dict(kind='contact-owner',name=name,actual=addresses.get(name),original=address))
        if live!=expected_live:differences.append(dict(kind='live-owners',actual=sorted(live),original=sorted(expected_live)))
    result=dict(label=case['label'],cache_mode=case['cache_mode'],events=len(plan),allocations_checked=allocations,contact_groups=len(counts),contacts=sum(counts),differences=differences)
    if return_state:return result,heap,{name:addresses[name]for name in live}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/cap_prelude_original.json.gz');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[compare(case)for case in fixture['cases']]
    report=dict(cases=len(results),events=sum(c['events']for c in results),allocations_checked=sum(c['allocations_checked']for c in results),differences=sum(len(c['differences'])for c in results),results=results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

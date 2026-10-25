"""Source clone/COPY/JOIN bytes and one heap through CAP matrix entry."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.bridge import _mesh
from reasitic.heap import Heap
from reasitic.memory import Memory
from reasitic.geometry_storage import GeometryStorage
from reasitic.legacy_strings import LegacyStrings
from audit_allocator_original import state_differences
from audit_cap_prelude_original import compare as prelude


def compare(case,*,return_state=False,include_prelude=True,observe_headers=False,initial_regions=()):
    context=case['setup_context'];output=case['setup_output'];initial=case['allocator_states'][0]
    assert initial['label']=='driver_entry'
    heap=Heap(initial);memory=Memory(heap.address_space)
    for region in context['memory_regions']:memory.write(region['address'],bytes.fromhex(region['data']))
    memory.write(initial['arena_address'],bytes.fromhex(initial['arena_bytes']))
    for address,data in initial_regions:memory.write(address,data)
    strings=context['strings'];memory.write(strings['address'],bytes.fromhex(strings['data']))
    geometry=GeometryStorage(heap,memory,context['head'])
    geometry.strings=LegacyStrings(memory,geometry.string_allocate,geometry.release,nil_address=strings['nil_address'],pool_address=strings['pool_address'])
    # The initial tcache is caller state. Subsequent cache stores and geometry
    # stores share these bytes; there is no contacts-entry byte reset.
    key=None
    for chain in initial['tcache']:
        if chain:
            key=memory.u32(chain[0]+4);break
    if key is None:raise ValueError('Capture needs an initial tcache key observation')
    heap.observe_cache_stores(memory,key)
    if observe_headers:heap.observe_header_stores(memory)
    mesh=_mesh(case['request'],Technology.from_text(case['request']['technology']))
    first,second=geometry.setup(context['driver'],context['arguments'],cap_length=mesh['capacitance_length_cell'],length=mesh['length_cell'])
    result=dict(label=case['label'],cache_mode=case['cache_mode'],events_checked=0,allocations_checked=0,geometry_bytes_checked=0,string_bytes_checked=0,prefix=None,differences=[])
    differences=result['differences'];observed=case['setup_events']
    if len(geometry.events)!=len(observed):differences.append(dict(kind='event-count',actual=len(geometry.events),original=len(observed)))
    for index,((event,address),native)in enumerate(zip(geometry.events,observed)):
        if (event.action,event.allocator)!=(native['kind'],native['allocator']):differences.append(dict(kind='interface',index=index,actual=event.__dict__,original=native));break
        if event.action=='allocate':
            result['allocations_checked']+=1
            if event.size!=native['request']:differences.append(dict(kind='request',index=index,name=event.name,actual=event.size,original=native['request']))
        if address!=native['address']:differences.append(dict(kind='address',index=index,name=event.name,actual=address,original=native['address']))
        result['events_checked']+=1
    for field,actual in (('first',first),('second',second),('head',geometry.head)):
        original=output[field]['address']if field!='head'else output[field]
        if actual!=original:differences.append(dict(kind='shape-owner',field=field,actual=actual,original=original))
    def check(address,data,key):
        native=bytes.fromhex(data);actual=memory.read(address,len(native));result[key]+=len(native)
        for offset in range(0,len(native),4):
            if actual[offset:offset+4]!=native[offset:offset+4]:differences.append(dict(kind='memory',address=address,offset=offset,actual=actual[offset:offset+4].hex(),original=native[offset:offset+4].hex()))
    if not differences:
        seen=set()
        for field in ('first','second'):
            shape=output[field]
            if shape['address']in seen:continue
            seen.add(shape['address']);check(shape['address'],shape['data'],'geometry_bytes_checked')
            actual=list(geometry.segments(shape['address']));native=[s['address']for s in shape['segments']]
            if actual!=native:differences.append(dict(kind='segment-owners',field=field,actual=actual,original=native))
            for segment in shape['segments']:
                check(segment['address'],segment['data'],'geometry_bytes_checked')
                actual=list(geometry.children(segment['address']));native=[s['address']for s in segment['children']]
                if actual!=native:differences.append(dict(kind='secondary-owners',field=field,parent=segment['address'],actual=actual,original=native))
                for child in segment['children']:check(child['address'],child['data'],'geometry_bytes_checked')
        strings=output['strings'];check(strings['address'],strings['data'],'string_bytes_checked')
        for chain in strings['chains']:
            for entry in chain:check(entry['address'],entry['data'],'string_bytes_checked')
        differences.extend(state_differences(heap,next(s for s in case['allocator_states']if s['label']=='contacts_entry')))
    if not differences and include_prelude:
        prefix,heap,contacts=prelude(case,heap=heap,return_state=True);result['prefix']=prefix;differences.extend(prefix['differences'])
        addresses={**geometry.addresses,**contacts}
    else:addresses=geometry.addresses
    addresses['geometry.descriptor']=first
    addresses.update((f'geometry.segment.{i}',address)for i,address in enumerate(geometry.segments(first)))
    if return_state:return result,heap,addresses,memory
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/geometry_setup_original.json.gz');p.add_argument('--output',type=Path);options=p.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[compare(case)for case in fixture['cases']]
    report=dict(cases=len(results),differences=sum(len(c['differences'])for c in results),results=results)
    for key in ('events_checked','allocations_checked','geometry_bytes_checked','string_bytes_checked'):report[key]=sum(c[key]for c in results)
    for field,key in (('events','prefix_events'),('allocations_checked','prefix_allocations')):report[key]=sum(c['prefix'][field]for c in results if c['prefix']is not None)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

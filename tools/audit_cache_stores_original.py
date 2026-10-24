"""Generate cache bytes from earlier metadata and allocation/free history."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage
from reasitic.bridge import _mesh
from reasitic.heap import Heap
from reasitic.memory import Memory
from reasitic.solver import filament_counts
from audit_allocator_original import state_differences
from audit_cap_prelude_original import compare as prelude,dimensions
from audit_shared_heap_original import ported_inductance_geometry,via_records,seed


def compare(case,*,return_state=False):
    initial=case['allocator_states'][0];assert initial['label']=='contacts_entry'
    heap=Heap(initial);memory=Memory(heap.address_space)
    heap.observe_cache_stores(memory,initial['tcache_key'])
    report=dict(label=case['label'],cache_mode=case['cache_mode'],differences=[],boundaries=0,cache_words_checked=0,events_checked=0,allocations_checked=0)
    def check(state):
        expected=Memory(heap.address_space);seed(expected,state)
        ranges=[(heap.cache_address,384)]if heap.tcache_enabled else[]
        ranges.extend((p+8,8)for chain in heap.tcache for p in chain)
        for address,size in ranges:
            actual=memory.read(address,size);original=expected.read(address,size)
            report['cache_words_checked']+=size//4
            if actual!=original:report['differences'].append(dict(kind='cache-bytes',boundary=state['label'],address=address,actual=actual.hex(),original=original.hex()))
        report['differences'].extend(state_differences(heap,state));report['boundaries']+=1
    check(initial)
    prefix,heap,addresses=prelude(case,return_state=True,heap=heap)
    report['differences'].extend(prefix['differences']);report['events_checked']+=prefix['events'];report['allocations_checked']+=prefix['allocations_checked']
    if report['differences']:return (report,heap,memory)if return_state else report
    check(next(s for s in case['allocator_states']if s['label']=='scope'))
    counts,*_=dimensions(case);shape,technology=ported_inductance_geometry(case);mesh=_mesh(case['request'],technology)
    conductors=[s for s in shape.segments if s.metal<len(technology.metals)]
    filaments=sum(y*z for segment in conductors for y,z in [filament_counts(segment,mesh['width_cell'],mesh['thickness_cell'],mesh.get('max_width_cells',500))])
    plan=iter(combined_network_storage(counts,len(conductors),filaments,len(via_records(case)),clone_segments=len(shape.segments)))
    for event in case['events']:
        if event['kind']=='via_entry':break
        if event['kind']not in ('allocate','free'):continue
        expected=next(plan)
        assert (expected.action,expected.allocator)==(event['kind'],event['allocator'])
        if expected.action=='allocate':
            assert expected.size==event['request'];address=heap.malloc(expected.size);addresses[expected.name]=address;report['allocations_checked']+=1
            if address!=event['address']:report['differences'].append(dict(kind='allocation-address',name=expected.name,actual=address,original=event['address']))
        else:
            address=addresses[expected.name];assert address==event['address'];heap.free(address)
        report['events_checked']+=1
    check(next(s for s in case['allocator_states']if s['label']=='via_entry'))
    return (report,heap,memory)if return_state else report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[compare(case)for case in fixture['cases']]
    report=dict(cases=len(results),differences=sum(len(c['differences'])for c in results),results=results)
    for key in ('boundaries','cache_words_checked','events_checked','allocations_checked'):report[key]=sum(c[key]for c in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

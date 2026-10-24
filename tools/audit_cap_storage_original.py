"""Regenerate complete CAP buffers and store them at predicted guest addresses."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import capacitance_storage
from reasitic.bridge import _mesh,_frequency
from reasitic.potential import solve_capacitance
from reasitic.memory import Memory,ComplexView
from audit_cap_prelude_original import compare as prelude,dimensions
from audit_shared_heap_original import ported_inductance_geometry


def ported_buffers(case,*,inverse_storage=None):
    shape,technology=ported_inductance_geometry(case);request=case['request'];mesh=_mesh(request,technology)
    result={}
    data=solve_capacitance(shape,technology,_frequency(request),ground=shape if request['action']=='calctrans'else None,
                      length_cell=mesh['capacitance_length_cell'],width_cell=mesh['capacitance_width_cell'],
                      observe_storage=lambda name,matrix:result.__setitem__(name,matrix),include_potential=inverse_storage is not None)
    if inverse_storage is not None:
        from reasitic.linear import factor_general
        potential=[[complex(*value)for value in row]for row in data['potential_matrix']]
        lu,pivots=factor_general(potential);n=len(lu)
        inverse_storage['cap.inverse.pivots']=tuple(p+1 for p in pivots)
        inverse_storage['cap.inverse.work']=(complex(n*64 if n>64 else n,0),*(lu[i][0]for i in range(1,n)))
    return result


def compare(case):
    prefix,heap,addresses=prelude(case,return_state=True)
    report=dict(label=case['label'],cache_mode=case['cache_mode'],differences=list(prefix['differences']),
                allocations_checked=0,events_checked=0,matrices_checked=0,words_checked=0)
    if report['differences']:return report
    buffers=ported_buffers(case);counts,*_=dimensions(case)
    plan=capacitance_storage(counts,len(buffers['cap.output']))
    observed=iter(e for e in case['events']if e['kind']in ('allocate','free'))
    for expected in plan:
        if expected.name.startswith('contact'):break
        event=next(observed)
        if (expected.action,expected.allocator)!=(event['kind'],event['allocator']):
            report['differences'].append(dict(kind='interface',name=expected.name));return report
        if expected.action=='allocate':
            if expected.size!=event['request']:report['differences'].append(dict(kind='request',name=expected.name));return report
            address=heap.malloc(expected.size);addresses[expected.name]=address;report['allocations_checked']+=1
            if address!=event['address']:report['differences'].append(dict(kind='address',name=expected.name,actual=address,original=event['address']));return report
        else:
            address=addresses[expected.name]
            if address!=event['address']:report['differences'].append(dict(kind='free-identity',name=expected.name));return report
            heap.free(address)
        report['events_checked']+=1
    # All four buffers are live here, before contact/matrix cleanup. No captured
    # numerical word initializes this guest memory or the generated matrices.
    memory=Memory(heap.address_space)
    for name,matrix in buffers.items():
        n=len(matrix);address=addresses[name];original=case['cap_storage'][name.replace('.','_')]
        if (n,n,address)!=(original['size'],original['stride'],original['data']):
            report['differences'].append(dict(kind='descriptor',name=name,actual=[n,n,address],original=[original['size'],original['stride'],original['data']]));continue
        ComplexView(memory,address,n).write(matrix)
        actual=memory.read(address,16*n*n);expected=bytes.fromhex(original['data_bytes'])
        assert len(actual)==len(expected)
        for offset in range(0,len(actual),8):
            if actual[offset:offset+8]!=expected[offset:offset+8]:report['differences'].append(dict(kind='word',name=name,offset=offset,actual=actual[offset:offset+8].hex(),original=expected[offset:offset+8].hex()))
        report['matrices_checked']+=1;report['words_checked']+=len(actual)//8
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/cap_storage_original.json.gz');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        result=compare(case);results.append(result)
        print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('allocations_checked','events_checked','matrices_checked','words_checked'):report[key]=sum(r[key]for r in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

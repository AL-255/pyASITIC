"""Generate native pre-CAP FFT/stream buffers from production math and libio."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.bridge import _frequency
from reasitic.allocation_plan import capacitance_prelude_storage
from reasitic.heap import Heap
from reasitic.memory import Memory
from reasitic.prelude_storage import table_storage,complex_bytes,store_file_buffer
from audit_cap_prelude_original import dimensions
from project_prelude_storage_original import expand_case


def compare(case):
    initial=next(s for s in case['allocator_states']if s['label']=='contacts_entry')
    counts,metals,substrates,nx=dimensions(case);abi=initial['io_abi'];block=abi['filesystem_block_size']
    plan=capacitance_prelude_storage(counts,metals,substrates,nx,cache_mode=case['cache_mode'],file_bytes=abi['file_plus']+abi['lock']+abi['wide_data'],buffer_bytes=min(abi['buffer_default'],block)if block>0 else abi['buffer_default'])
    names={e.name:e for e in plan if e.action=='allocate'}
    selected={i:e for i,e in enumerate(plan)if e.action=='free'and(e.name.startswith('cache.fft.')or e.name.endswith('.buffer'))}
    observed={r['event_index']:r for r in case['prelude_storage']}
    technology=Technology.from_text(case['request']['technology'])
    report=dict(label=case['label'],cache_mode=case['cache_mode'],workspaces_checked=0,file_buffers_checked=0,bytes_checked=0,differences=[])
    for index,event in selected.items():
        native=observed[index]
        if event.name.startswith('cache.fft.'):
            source,target=map(int,event.name.split('.')[-2:]);*tables,scratch=table_storage(technology,_frequency(case['request']),source,target)
            actual=complex_bytes(scratch);report['workspaces_checked']+=1
        else:
            memory=Memory(Heap(initial).address_space)
            store_file_buffer(memory,native['address'],native['size'],case['cache_mode'],technology,_frequency(case['request']))
            actual=memory.read(native['address'],native['size']);report['file_buffers_checked']+=1
        expected=bytes.fromhex(native['data'])
        assert len(actual)==names[event.name].size==native['size']
        for offset in range(0,len(actual),8):
            if actual[offset:offset+8]!=expected[offset:offset+8]:report['differences'].append(dict(kind='workspace-word',name=event.name,offset=offset,actual=actual[offset:offset+8].hex(),original=expected[offset:offset+8].hex()))
        report['bytes_checked']+=len(actual)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/prelude_storage_original.json.gz');p.add_argument('--output',type=Path);options=p.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        case=expand_case(fixture,entry)
        result=compare(case);results.append(result);print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(c['differences'])for c in results),workspaces_checked=sum(c['workspaces_checked']for c in results),file_buffers_checked=sum(c['file_buffers_checked']for c in results),bytes_checked=sum(c['bytes_checked']for c in results),results=results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

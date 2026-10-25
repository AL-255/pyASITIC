"""Strict same-memory shunt cache, numerical, console and complete heap replay."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_console_storage_original import compare as console_history
from capture_driver_history_original import expand_case
from reasitic.memory import UnknownMemory
from reasitic.contact_stack import contact_frames


def compare(fixture,entry,*,return_state=False,console=None,initial_regions=(),observe_boundary=None):
    case=expand_case(fixture,entry);differences=[];words=boundaries=unknown=0
    initial=next(s for s in case['allocator_states']if s['label']=='driver_entry')
    if 'esp'not in initial:raise ValueError('Complete contact replay requires the earlier driver ESP')
    frames=contact_frames(case['setup_context']['driver'],initial['esp'])
    def boundary(label,heap,addresses,memory):
        nonlocal words,boundaries,unknown
        state=next(s for s in case['allocator_states']if s['label']==label)
        for region in state['memory_regions']:
            native=bytes.fromhex(region['data']);address=region['address'];words+=len(native)//4
            try:actual=memory.read(address,len(native))
            except UnknownMemory:actual=None
            if actual==native:continue
            for offset in range(0,len(native),4):
                try:value=actual[offset:offset+4]if actual is not None else memory.read(address+offset,4)
                except UnknownMemory:
                    unknown+=4;differences.append(dict(kind='unknown-early-heap-word',boundary=label,address=address+offset));continue
                if value!=native[offset:offset+4]:differences.append(dict(kind='early-heap-word',boundary=label,address=address+offset,actual=value.hex(),original=native[offset:offset+4].hex()))
        boundaries+=1
        if observe_boundary is not None:observe_boundary(label,heap,addresses,memory)
    result,heap,addresses,memory=console_history(fixture,entry,return_state=True,observe_boundary=boundary,console=console,check_calls=console is None,initial_regions=initial_regions)
    contact_entry=next(s for s in case['allocator_states']if s['label']=='contacts_entry')
    if frames['contacts_entry']!=contact_entry['esp']:differences.append(dict(kind='contact-entry-esp',actual=frames['contacts_entry'],original=contact_entry['esp']))
    for index,observed in enumerate(case['contact_stack_entries']):
        for name,key in(('builder_entry','esp'),('contacts_frame','ebp'),('index_address','index_address'),('index','index')):
            if frames[name]!=observed[key]:differences.append(dict(kind='contact-builder-stack',entry=index,field=key,actual=frames[name],original=observed[key]))
    result['differences'].extend(differences);result.update(early_heap_words_checked=words,early_heap_boundaries_checked=boundaries,early_unknown_heap_bytes=unknown)
    result.update(contact_stack_entries_checked=len(case['contact_stack_entries']),contact_stack_words_checked=4*len(case['contact_stack_entries']))
    if return_state:return result,heap,addresses,memory
    return result


def run(fixture):
    results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result)
        print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('events_checked','allocations_checked','stores_checked','faults_checked','unknown_targets','cap_words_checked','ind_words_checked','cache_words_checked','cache_boundaries','cap_input_words_checked','ind_input_words_checked','workspace_arrays_checked','workspace_bytes_checked','heap_words_checked','unknown_heap_bytes','heap_boundaries_checked','console_calls_checked','early_heap_words_checked','early_heap_boundaries_checked','early_unknown_heap_bytes','contact_stack_entries_checked','contact_stack_words_checked'):report[key]=sum(r[key]for r in results)
    for key in('events_checked','allocations_checked','bytes_checked','unknown_bytes','tables_checked','table_bytes_checked'):report['driver_'+key]=sum(r['driver'][key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_driver_history_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'})
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

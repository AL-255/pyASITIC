"""Two source solves and intervening command parsing on the same guest heap."""
import argparse,copy,gzip,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_shunt_command_transition_original import compare as first
from audit_libio_storage_original import compare as prelude
from audit_storage_history_original import compare as numerical
from audit_node_history_original import compare as nodes
from audit_allocator_original import state_differences
from reasitic.geometry_storage import GeometryStorage
from reasitic.legacy_strings import LegacyStrings
from reasitic.contact_stack import contact_frames
from reasitic.memory import UnknownMemory
from reasitic.bridge import _frequency
from reasitic import Technology
from reasitic.cache_storage import CacheStorage
from capture_cache_storage_original import expand_files


def expand_second(fixture,entry):
    case=copy.deepcopy(entry['second'])
    def region(record,bank='driver_heap_pages'):
        if 'data'in record:return record
        data=b''.join(bytes.fromhex(fixture[bank][key])for key in record['pages'])
        assert len(data)==record['size']and hashlib.sha256(data).hexdigest()==record['sha256']
        return dict(record,data=data.hex())
    for field in('allocator_states','post_states'):
        for state in case[field]:state['memory_regions']=[region(r)for r in state['memory_regions']]
    case['post_buffers']=[region(r)for r in case['post_buffers']]
    case['setup_context']['memory_regions']=[region(r)for r in case['setup_context']['memory_regions']]
    case['prelude_final_heap']=[region(r)for r in case['prelude_final_heap']or()]
    return dict(case,label=entry['label'],cache_mode=entry['cache_mode'])


def compare(fixture,entry,*,return_state=False,observe_continuation=None):
    continuing=[];cached={}
    def cache_completed(label,heap,addresses,memory):
        if label!='scope':return
        frequency=_frequency(entry['request']);cache=CacheStorage(memory,entry['cache_inputs'],Technology.from_text(entry['request']['technology']),frequency)
        if entry['cache_mode']=='cold':
            directory=bytes.fromhex(entry['console_inputs']['directory']).decode();name=bytes.fromhex(entry['console_inputs']['technology_name']).decode()
            if directory!='.':raise NotImplementedError('Other cache output directories need the continuing filesystem')
            files={name+f'_{frequency/1e9:2.2f}.dat':b''.join(data for start,stop,data in cache.stream('cold').chunks)}
        elif entry['cache_mode']=='warm':files=dict(expand_files(fixture,entry))
        else:raise NotImplementedError('Second solve needs an enabled successful earlier cache')
        cached.update(frequency=frequency,files=files)
    before,heap,old_addresses,memory=first(fixture,entry,return_state=True,observe_transition=continuing.append,observe_driver_boundary=cache_completed)
    if not continuing:raise ValueError('Second solve needs the source command transition')
    history=continuing[0];console=history.console;start=len(console.calls)
    source=history.result;frequency=struct.unpack('<d',memory.read(0x80d86a0,8))[0]
    if frequency!=cached.get('frequency'):raise NotImplementedError('Changed sweep frequency needs the continuing cache-file selection path')
    call=history.stack.driver_entry(source['driver'],source['arguments'],frequency,libc_base=entry['libio_inputs']['libc_base'])
    geometry=GeometryStorage(heap,memory,history.geometry.head)
    bindings=entry['setup_context']['strings']
    geometry.strings=LegacyStrings(memory,geometry.string_allocate,geometry.release,nil_address=bindings['nil_address'],pool_address=bindings['pool_address'])
    source_context=dict(geometry=geometry,driver=source['driver'],arguments=source['arguments'],driver_esp=call['esp'],io_abi=next(s for s in entry['allocator_states']if s['label']=='contacts_entry')['io_abi'])
    case=expand_second(fixture,entry)
    # Only earlier request/bindings and source parser frequency select the
    # numerical inputs. All second-entry heap/cache/console observations stay
    # assertion-only. The first successful solve left this frequency cached.
    request=dict(entry['request'],action=source['driver'],frequency_hz=frequency,frequency_ghz=None)
    request.pop('frequency_ghz');case.update(request=request,prelude_cache_mode='memory',cache_inputs=entry['cache_inputs'],libio_inputs=entry['libio_inputs'],console_inputs=entry['console_inputs'])
    console.position=dict(setup_events=0,prefix_events=0,events=0,post_events=0)
    differences=[];words=boundaries=unknown=0;cache_tables=cache_bytes=0
    def check_tables(records,*,initial=False):
        nonlocal cache_tables,cache_bytes
        actual=[]
        for name,group in entry['cache_inputs']['arrays'].items():
            for i in range(len(group['pointers'])):
                actual.append((name,i,memory.u32(group['pointer_address']+4*i),group['size']))
        if len(actual)!=len(records):differences.append(dict(kind='second-cache-count',initial=initial))
        for (name,i,address,size),record in zip(actual,records):
            if(address,size)!=(record['address'],record['size'])or(not initial and(name,i)!=(record['name'],record['index'])):differences.append(dict(kind='second-cache-owner',initial=initial,name=name,index=i))
            data=memory.read(address,size);digest=hashlib.sha256(data).hexdigest()
            if digest!=record['sha256']:differences.append(dict(kind='second-cache-table',initial=initial,name=name,index=i,actual=digest,original=record['sha256']))
            cache_tables+=1;cache_bytes+=size
    check_tables(entry['second']['cache_inputs']['initial_regions'],initial=True)
    files=entry['second']['cache_inputs']['files'];file_bytes=0
    if set(cached['files'])!={r['name']for r in files}:differences.append(dict(kind='second-cache-file-count'))
    for record in files:
        data=cached['files'].get(record['name'],b'');file_bytes+=len(data)
        if len(data)!=record['size']or hashlib.sha256(data).hexdigest()!=record['sha256']:differences.append(dict(kind='second-cache-file',name=record['name']))
    def boundary(label,h,a,m):
        nonlocal words,boundaries,unknown
        state=next(s for s in case['allocator_states']if s['label']==label)
        differences.extend(state_differences(h,state,memory=m))
        for r in state['memory_regions']:
            data=bytes.fromhex(r['data']);words+=len(data)//4
            try:actual=m.read(r['address'],len(data))
            except UnknownMemory:actual=None
            if actual==data:continue
            for offset in range(0,len(data),4):
                try:value=actual[offset:offset+4]if actual is not None else m.read(r['address']+offset,4)
                except UnknownMemory:unknown+=4;differences.append(dict(kind='unknown-second-heap-word',boundary=label,address=r['address']+offset));continue
                if value!=data[offset:offset+4]:differences.append(dict(kind='second-heap-word',boundary=label,address=r['address']+offset,actual=value.hex(),original=data[offset:offset+4].hex()))
        boundaries+=1
    boundary('driver_entry',heap,old_addresses,memory)
    expected=case['setup_context']['entry']
    for key,value in call.items():
        if expected[key]!=value:differences.append(dict(kind='second-entry',field=key,actual=value,original=expected[key]))
    raw=memory.read(call['esp']+4,len(expected['arguments_data'])//2)
    if raw.hex()!=expected['arguments_data']:differences.append(dict(kind='second-argument-bytes',actual=raw.hex(),original=expected['arguments_data']))
    def driver(*args,**kwargs):
        prefix,h,a,m=prelude(case,return_state=True,cache_files=(),console=console,observe_boundary=boundary,source_context=source_context)
        if prefix['differences']:return prefix,h,a,m
        check_tables(case['cache_outputs'])
        result,h,a,m=numerical(case,context=(prefix,h,a,m),return_state=True,console=console);result['driver']=prefix
        frames=contact_frames(source['driver'],call['esp'])
        contact=next(s for s in case['allocator_states']if s['label']=='contacts_entry')
        if frames['contacts_entry']!=contact['esp']:differences.append(dict(kind='second-contact-entry',actual=frames['contacts_entry'],original=contact['esp']))
        for i,record in enumerate(case['contact_stack_entries']):
            for name,key in(('builder_entry','esp'),('contacts_frame','ebp'),('index_address','index_address'),('index','index')):
                if frames[name]!=record[key]:differences.append(dict(kind='second-contact-frame',index=i,field=key,actual=frames[name],original=record[key]))
        return result,h,a,m
    result,heap,addresses,memory=nodes(fixture,entry,return_state=True,console=console,driver_compare=driver,expanded_case=case,console_start=start,report_model=source['driver']=='calctrans')
    result['differences'].extend(differences);result['differences'][:0]=before['differences']
    result.update(first=before,second_early_heap_words_checked=words,second_early_heap_boundaries_checked=boundaries,second_early_unknown_bytes=unknown,cache_tables_checked=cache_tables,cache_table_bytes_checked=cache_bytes,cache_files_checked=len(files),cache_file_bytes_checked=file_bytes)
    if observe_continuation is not None:observe_continuation(history)
    if return_state:return result,heap,addresses,memory
    return result


def run(fixture):
    results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('events_checked','allocations_checked','buffers_checked','buffer_bytes_checked','heap_boundaries_checked','heap_words_checked','unknown_heap_bytes','port_words_checked','port_memory_words_checked','unknown_port_bytes','console_calls_checked','faults_checked','second_early_heap_words_checked','second_early_heap_boundaries_checked','second_early_unknown_bytes','cache_tables_checked','cache_table_bytes_checked','cache_files_checked','cache_file_bytes_checked'):report[key]=sum(r[key]for r in results)
    for key in('events_checked','allocations_checked','stores_checked','workspace_arrays_checked','workspace_bytes_checked','cap_words_checked','ind_words_checked','heap_words_checked','heap_boundaries_checked','unknown_heap_bytes'):report['numerical_'+key]=sum(r['before'].get(key,0)for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_second_driver_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

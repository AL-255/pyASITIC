"""Replay every pre-CAP allocation and freed buffer from earlier guest state."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic import Technology
from reasitic.bridge import _frequency
from reasitic.allocation_plan import capacitance_prelude_storage
from reasitic.libio_storage import FileStorage,copy_cache_headers
from reasitic.contact_storage import write_prepared
from reasitic.prelude_storage import table_storage,complex_bytes,store_file_buffer
from reasitic.memory import UnknownMemory
from audit_geometry_setup_original import compare as geometry
from audit_contact_storage_original import ported_records
from audit_cap_prelude_original import dimensions
from audit_allocator_original import state_differences
from project_prelude_storage_original import expand_case


def compare(case,*,return_state=False,cache_files=None,console=None,initial_regions=(),observe_boundary=None):
    from reasitic.cache_storage import CacheStorage,initial_regions as cache_regions
    cached=cache_files is not None
    console_regions=console.initial_regions(tuple((r['address'],bytes.fromhex(r['data']))for r in case['setup_context']['memory_regions']))if console is not None else()
    regions=tuple(cache_regions(case['cache_inputs'])if cached else())+console_regions+tuple(initial_regions)
    before,heap,addresses,memory=geometry(case,return_state=True,include_prelude=False,observe_headers=True,initial_regions=regions)
    result=dict(label=case['label'],cache_mode=case['cache_mode'],geometry=before,events_checked=0,allocations_checked=0,file_records_checked=0,header_arrays_checked=0,workspaces_checked=0,file_buffers_checked=0,bytes_checked=0,unknown_bytes=0,differences=list(before['differences']))
    if result['differences']:return result
    initial=next(s for s in case['allocator_states']if s['label']=='contacts_entry')
    counts,metals,substrates,nx=dimensions(case);abi=initial['io_abi'];block=abi['filesystem_block_size']
    plan=capacitance_prelude_storage(counts,metals,substrates,nx,cache_mode=case['cache_mode'],file_bytes=abi['file_plus']+abi['lock']+abi['wide_data'],buffer_bytes=min(abi['buffer_default'],block)if block>0 else abi['buffer_default'])
    objects={e.name:e for e in plan if e.action=='allocate'};observed={r['event_index']:r for r in case['prelude_storage']}
    inputs=case['libio_inputs'];stdio=case.get('transition_inputs',{}).get('stdio_context',{});errno_address=None
    if stdio.get('printf_abi'):
        tls=case['transition_inputs']['loader_context']['tls_base'];got=inputs['libc_base']+0x22fe34
        errno_address=(memory.u32(tls)+memory.u32(got+0xa0))&0xffffffff
    files=FileStorage(memory,inputs,errno_address=errno_address)
    technology=Technology.from_text(case['request']['technology']);frequency=_frequency(case['request']);contacts=ported_records(case);prepared=False
    driver=next(s for s in case['allocator_states']if s['label']=='driver_entry');history_index=None
    if 'esp'in driver:
        from reasitic.contact_stack import contact_frames
        history_index=contact_frames(case['setup_context']['driver'],driver['esp'])['index']
    cache=CacheStorage(memory,case['cache_inputs'],technology,frequency,cache_files)if cached else None
    if console is not None:
        console.bind(memory);console.position['setup_events']=before['events_checked'];console.begin_capacitance(frequency)
    if observe_boundary is not None:observe_boundary('contacts_entry',heap,addresses,memory)
    if len(plan)!=len(case['prefix_events']):result['differences'].append(dict(kind='event-count',actual=len(plan),original=len(case['prefix_events'])))
    for index,(event,native)in enumerate(zip(plan,case['prefix_events'])):
        name=event.name
        if (event.action,event.allocator)!=(native['kind'],native['allocator']):result['differences'].append(dict(kind='interface',index=index));break
        if not prepared and name.startswith('cache.'):
            write_prepared(memory,contacts,addresses,history_index=history_index);prepared=True
            if cache is not None and 'coefficient_address'in case['cache_inputs']:cache.write_coefficients()
            if console is not None:console.contacts_ready(sum(counts))
        if event.action=='allocate':
            if event.size!=native['request']:result['differences'].append(dict(kind='request',index=index));break
            if cache is not None and name.startswith('cache.fft.'):
                if console is not None:console.begin_table()
                source,target=map(int,name.split('.')[-2:]);cache.begin(source,target)
                if console is not None:console.table_ready()
            address=heap.malloc(event.size);addresses[name]=address;result['allocations_checked']+=1
            if name.endswith('.file'):files.initialize(address)
            if name=='cache.reader.buffer':
                if cache is not None:
                    # These histories have one earlier external input file.
                    # Resolve that explicit path, not its frequency payload.
                    matches=inputs['cache_files']
                else:
                    prefix=struct.pack('<iid',int(technology.chip['fftx']),int(technology.chip['ffty']),frequency)
                    matches=[r for r in inputs['cache_files']if bytes.fromhex(r['header']).startswith(prefix)]
                if len(matches)!=1:raise ValueError('Missing or ambiguous earlier cache-file header')
                header=cache.input_file(matches[0]['name'])if cache is not None else bytes.fromhex(matches[0]['header'])
                copy_cache_headers(memory,addresses['cache.header.substrates'],addresses['cache.header.metals'],header,substrates,metals)
                if cache is not None:cache.load(matches[0]['name'])
            if name=='cache.writer.buffer'and console is not None:
                console.position['prefix_events']=index+1;console.warning('Writing data...')
        else:
            address=addresses[name]
            if name.endswith('.file'):
                if name=='cache.reader.file'and case['cache_mode']=='cold':
                    error=None
                    if errno_address is not None:
                        # Earlier inputs declare the current directory and
                        # its complete initial .dat manifest. The requested
                        # cache file is absent; Linux open returns ENOENT.
                        if inputs['cache_files']or bytes.fromhex(case['console_inputs']['directory'])!=b'.':raise NotImplementedError('Other failed cache paths need their earlier filesystem error')
                        error=2
                    files.failed_open(address,error_number=error)
                else:files.closed_byte_stream(address)
                key='file_records_checked'
            elif name.startswith('cache.header.'):key='header_arrays_checked'
            elif name.startswith('cache.fft.'):
                if cache is not None:cache.transform(address)
                else:
                    source,target=map(int,name.split('.')[-2:]);*tables,scratch=table_storage(technology,frequency,source,target)
                    memory.write(address,complex_bytes(scratch))
                key='workspaces_checked'
            elif name.endswith('.buffer'):
                if cache is not None:cache.file_buffer(address,objects[name].size,case['cache_mode'])
                else:store_file_buffer(memory,address,objects[name].size,case['cache_mode'],technology,frequency)
                key='file_buffers_checked'
            else:raise ValueError('Unimplemented pre-CAP free store: '+name)
            record=observed[index];assert record['address']==address and record['size']==objects[name].size
            expected=bytes.fromhex(record['data']);result[key]+=1
            for offset in range(0,len(expected),4):
                size=min(4,len(expected)-offset)
                try:actual=memory.read(address+offset,size)
                except UnknownMemory:
                    result['unknown_bytes']+=size;result['differences'].append(dict(kind='unknown-bytes',name=name,offset=offset,size=size));continue
                result['bytes_checked']+=size
                if actual!=expected[offset:offset+size]:result['differences'].append(dict(kind='bytes',name=name,offset=offset,actual=actual.hex(),original=expected[offset:offset+size].hex()))
            heap.free(address)
            if name=='cache.reader.file'and case['cache_mode']=='cold'and console is not None:console.position['prefix_events']=index+1;console.missing_cache()
            if cache is not None and name.startswith('cache.fft.'):cache.finish()
        if address!=native['address']:result['differences'].append(dict(kind='address',index=index,name=name,actual=address,original=native['address']))
        result['events_checked']+=1
        if console is not None:console.position['prefix_events']=result['events_checked']
    result['differences'].extend(state_differences(heap,next(s for s in case['allocator_states']if s['label']=='scope'),memory=memory if cached else None))
    if observe_boundary is not None:observe_boundary('scope',heap,addresses,memory)
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/libio_storage_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        case=expand_case(fixture,entry);result=compare(case);results.append(result)
        print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','file_records_checked','header_arrays_checked','workspaces_checked','file_buffers_checked','bytes_checked','unknown_bytes'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

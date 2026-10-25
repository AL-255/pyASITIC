"""Strict continuing S record, FILE/global bytes, fclose and export return."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_shunt_second_driver_original import compare as second
from audit_allocator_original import state_differences
from reasitic.port_output_storage import PortOutputStorage,SCATTERING_ADDRESSES
from reasitic.memory import UnknownMemory


def expand_tail(fixture,entry):
    def region(record):
        data=b''.join(bytes.fromhex(fixture['driver_heap_pages'][key])for key in record['pages'])
        assert len(data)==record['size']and hashlib.sha256(data).hexdigest()==record['sha256']
        return dict(record,data=data)
    tail=entry['port_tail']
    return dict(tail,states=[dict(s,memory_regions=[region(r)for r in s['memory_regions']])for s in tail['states']],buffers=[region(r)for r in tail['buffers']])


def compare(fixture,entry,*,return_state=False,observe_continuation=None):
    continuing=[]
    before,heap,addresses,memory=second(fixture,entry,return_state=True,observe_continuation=continuing.append)
    if len(continuing)!=1:raise ValueError('Port output requires the continuing second driver')
    history=continuing[0];tail=expand_tail(fixture,entry)
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],before=before,differences=list(before['differences']),events_checked=0,buffers_checked=0,buffer_bytes_checked=0,heap_boundaries_checked=0,heap_words_checked=0,component_bytes_checked=0,printf_calls_checked=0,printf_argument_bytes_checked=0,files_checked=0,file_bytes_checked=0,unknown_bytes=0)
    def check(address,original,kind):
        try:complete=memory.read(address,len(original))
        except UnknownMemory:complete=None
        if complete==original:return
        for offset in range(0,len(original),4):
            try:actual=complete[offset:offset+4]if complete is not None else memory.read(address+offset,min(4,len(original)-offset))
            except UnknownMemory:result['unknown_bytes']+=min(4,len(original)-offset);result['differences'].append(dict(kind='unknown-'+kind,address=address+offset));continue
            if actual!=original[offset:offset+4]:result['differences'].append(dict(kind=kind,address=address+offset,actual=actual.hex(),original=original[offset:offset+4].hex()))
    index=0
    def observe(label,storage):
        nonlocal index
        if index>=len(tail['states']):result['differences'].append(dict(kind='tail-extra-boundary',label=label));return
        state=tail['states'][index];index+=1
        if(label,len(storage.events))!=(state['label'],state['tail_event_count']):result['differences'].append(dict(kind='tail-boundary',actual=(label,len(storage.events)),original=(state['label'],state['tail_event_count'])))
        result['differences'].extend(state_differences(heap,state,memory=memory))
        for region in state['memory_regions']:
            check(region['address'],region['data'],'tail-heap-word');result['heap_words_checked']+=len(region['data'])//4
        result['heap_boundaries_checked']+=1
        expected=[(storage.stream.address,304),(storage.stream.buffer,4096),(storage.abi['libc_symbols']['_IO_list_all']['address'],4),*((a,16)for a in SCATTERING_ADDRESSES.values())]
        actual=[(r['address'],len(r['data'])//2)for r in state['component_regions']]
        if actual!=expected:result['differences'].append(dict(kind='tail-component-owners',actual=expected,original=actual))
        for region in state['component_regions']:
            data=bytes.fromhex(region['data']);check(region['address'],data,'tail-component-word');result['component_bytes_checked']+=len(data)
    storage=PortOutputStorage(history,observe=observe)
    try:storage.run()
    except(ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='tail-runtime',reason=str(error)))
    if tail['signal']:result['differences'].append(dict(kind='tail-native-fault',signal=tail['signal']))
    if index!=len(tail['states']):result['differences'].append(dict(kind='tail-boundary-count',actual=index,original=len(tail['states'])))
    if len(storage.events)!=len(tail['events']):result['differences'].append(dict(kind='tail-event-count',actual=len(storage.events),original=len(tail['events'])))
    for actual,expected in zip(storage.events,tail['events']):
        if actual!=expected:result['differences'].append(dict(kind='tail-event',actual=actual,original=expected))
        result['events_checked']+=1
    if len(storage.freed)!=len(tail['buffers']):result['differences'].append(dict(kind='tail-buffer-count'))
    for actual,expected in zip(storage.freed,tail['buffers']):
        if(actual['event_index'],actual['address'],actual['size'])!=(expected['event_index'],expected['address'],expected['size']):result['differences'].append(dict(kind='tail-buffer-owner'))
        if actual['data']!=expected['data']:result['differences'].append(dict(kind='tail-freed-buffer',address=actual['address']))
        result['buffers_checked']+=1;result['buffer_bytes_checked']+=actual['size']
    if len(storage.printf_calls)!=len(tail['printf']):result['differences'].append(dict(kind='tail-printf-count'))
    for actual,expected in zip(storage.printf_calls,tail['printf']):
        normalized={k:(v.hex()if isinstance(v,bytes)else v)for k,v in actual.items()}
        if normalized!=expected:result['differences'].append(dict(kind='tail-printf',actual=normalized,original=expected))
        result['printf_calls_checked']+=1;result['printf_argument_bytes_checked']+=len(actual['arguments'])
    files=[]if tail['end']is None else tail['end']['files']
    if len(files)!=1:result['differences'].append(dict(kind='tail-file-count'))
    for expected in files:
        if storage.name.decode()!=expected['name']or bytes(storage.stream.data).hex()!=expected['data']:result['differences'].append(dict(kind='tail-file',name=expected['name'],actual=bytes(storage.stream.data).hex(),original=expected['data']))
        result['files_checked']+=1;result['file_bytes_checked']+=len(expected['data'])//2
    if observe_continuation is not None:observe_continuation(history)
    if return_state:return result,heap,addresses,memory
    return result


def run(fixture):
    results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('events_checked','buffers_checked','buffer_bytes_checked','heap_boundaries_checked','heap_words_checked','component_bytes_checked','printf_calls_checked','printf_argument_bytes_checked','files_checked','file_bytes_checked','unknown_bytes'):report[key]=sum(r[key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_port_tail_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

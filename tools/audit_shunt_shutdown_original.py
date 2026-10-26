"""Strict shutdown audit: missing continuation targets remain failures."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_shunt_port_tail_original import compare as port_tail
from audit_allocator_original import state_differences
from reasitic.script_eof_storage import ScriptEOFStorage
from reasitic.memory import UnknownMemory


def expand_shutdown(fixture,entry):
    def region(record):
        data=b''.join(bytes.fromhex(fixture['driver_heap_pages'][key])for key in record['pages'])
        if len(data)!=record['size']or hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Changed native shutdown region')
        return dict(record,data=data)
    def component(r):
        if 'data'in r:return r
        from audit_loader_lookup_original import data
        return dict(r,data=data(fixture,r).hex())
    shutdown=entry['shutdown']
    return dict(shutdown,states=[dict(s,memory_regions=[region(r)for r in s['memory_regions']],component_regions=[component(r)for r in s['component_regions']])for s in shutdown['states']],buffers=[region(r)for r in shutdown['buffers']])


def compare(fixture,entry,*,return_state=False,continue_repl=False,observe_malloc=None,observe_cleanup=None):
    continuing=[]
    before,heap,addresses,memory=port_tail(fixture,entry,return_state=True,observe_continuation=continuing.append)
    if len(continuing)!=1:raise ValueError('Shutdown requires the actual continuing port history')
    history=continuing[0];native=expand_shutdown(fixture,entry)
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],before=before,differences=list(before['differences']),events_checked=0,buffers_checked=0,buffer_bytes_checked=0,heap_boundaries_checked=0,heap_words_checked=0,component_bytes_checked=0,registers_checked=0,files_checked=0,file_bytes_checked=0,unknown_bytes=0,
                native_events=len(native['events']),native_buffers=len(native['buffers']),native_buffer_bytes=sum(r['size']for r in native['buffers']),native_boundaries=len(native['states']),native_registers=sum(len(s['registers'])for s in native['states']),native_exit=native['exit_code'])
    def check(address,original,kind):
        try:complete=memory.read(address,len(original))
        except UnknownMemory:complete=None
        if complete==original:return
        for offset in range(0,len(original),4):
            size=min(4,len(original)-offset)
            try:actual=complete[offset:offset+size]if complete is not None else memory.read(address+offset,size)
            except UnknownMemory:result['unknown_bytes']+=size;result['differences'].append(dict(kind='unknown-'+kind,address=address+offset));continue
            if actual!=original[offset:offset+size]:result['differences'].append(dict(kind=kind,address=address+offset,actual=actual.hex(),original=original[offset:offset+size].hex()))
    index=0
    def observe(label,storage):
        nonlocal index
        if index>=len(native['states']):result['differences'].append(dict(kind='shutdown-extra-boundary',label=label));return
        state=native['states'][index];index+=1
        if(label,len(storage.events))!=(state['label'],state['shutdown_event_count']):result['differences'].append(dict(kind='shutdown-boundary',actual=(label,len(storage.events)),original=(state['label'],state['shutdown_event_count'])))
        result['differences'].extend(state_differences(heap,state,memory=memory))
        for region in state['memory_regions']:
            check(region['address'],region['data'],'shutdown-heap-word');result['heap_words_checked']+=len(region['data'])//4
        result['heap_boundaries_checked']+=1
        expected=[(storage.stream.address,304),(storage.buffer,4096),(storage.abi['libc_symbols']['_IO_list_all']['address'],4),(history.inputs['workspace_address'],4460)]
        expected.extend((r['address'],r['size'])for r in history.inputs.get('stdio_context',{}).get('regions',()))
        owners=[(r['address'],len(r['data'])//2)for r in state['component_regions']]
        if owners!=expected:result['differences'].append(dict(kind='shutdown-component-owners',actual=expected,original=owners))
        for region in state['component_regions']:
            raw=bytes.fromhex(region['data']);check(region['address'],raw,'shutdown-component-word');result['component_bytes_checked']+=len(raw)
        # Semantic FILE operations do not yet execute their native register
        # or formatter-stack path. Never manufacture values or count them as
        # matched merely because the heap matches.
        registers=history.repl_registers if label=='interactive.parse'and hasattr(history,'repl_registers')else None
        if registers is None:result['differences'].append(dict(kind='shutdown-register-continuation-missing',label=label,original=state['registers']))
        else:
            for name,value in state['registers'].items():
                result['registers_checked']+=1
                if registers.get(name)!=value:result['differences'].append(dict(kind='shutdown-register',label=label,name=name,actual=registers.get(name),original=value))
        if 'stdin_position'in state and history.stdin_position!=state['stdin_position']:result['differences'].append(dict(kind='shutdown-stdin-position',label=label,actual=history.stdin_position,original=state['stdin_position']))
    storage=ScriptEOFStorage(history,observe=observe,observe_malloc=observe_malloc,observe_cleanup=observe_cleanup)
    console_start=len(history.console.calls)
    try:
        storage.run()
        if continue_repl:storage.resume_repl()
    except(ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='shutdown-runtime',reason=str(error)))
    for state in native['states'][index:]:
        result['differences'].append(dict(kind='shutdown-boundary-missing',label=state['label'],heap_bytes=sum(len(r['data'])for r in state['memory_regions']),component_bytes=sum(len(r['data'])//2 for r in state['component_regions']),registers=state['registers']))
    if len(storage.events)!=len(native['events']):result['differences'].append(dict(kind='shutdown-event-count',actual=len(storage.events),original=len(native['events'])))
    for actual,expected in zip(storage.events,native['events']):
        if actual!=expected:result['differences'].append(dict(kind='shutdown-event',actual=actual,original=expected))
        result['events_checked']+=1
    if len(storage.freed)!=len(native['buffers']):result['differences'].append(dict(kind='shutdown-buffer-count',actual=len(storage.freed),original=len(native['buffers'])))
    for actual,expected in zip(storage.freed,native['buffers']):
        if(actual['event_index'],actual['address'],actual['size'])!=(expected['event_index'],expected['address'],expected['size']):result['differences'].append(dict(kind='shutdown-buffer-owner'))
        if actual['data']!=expected['data']:result['differences'].append(dict(kind='shutdown-freed-buffer',address=actual['address']))
        result['buffers_checked']+=1;result['buffer_bytes_checked']+=actual['size']
    # A full output file is retained by the original source OutputStream;
    # native shutdown must not change or silently truncate that artifact.
    for expected in native['files']:
        if history.port_name.decode()!=expected['name']or bytes(history.port_stream.data).hex()!=expected['data']:result['differences'].append(dict(kind='shutdown-file',name=expected['name']))
        result['files_checked']+=1;result['file_bytes_checked']+=len(expected['data'])//2
    if len(native['files'])!=1:result['differences'].append(dict(kind='shutdown-file-count'))
    generated=history.console.calls[console_start:]
    if not generated and native['calls']:result['differences'].append(dict(kind='shutdown-console-continuation-missing',original=native['calls']))
    elif generated:
        if len(generated)!=len(native['calls']):result['differences'].append(dict(kind='shutdown-console-count',actual=len(generated),original=len(native['calls'])))
        for actual,expected in zip(generated,native['calls']):
            keys=('kind','text','to_log')
            if{k:actual.get(k,False)for k in keys}!={k:expected.get(k,False)for k in keys}:result['differences'].append(dict(kind='shutdown-console',actual=actual,original=expected))
    result['differences'].append(dict(kind='shutdown-process-exit-missing',original=native['exit_code'],signal=native['signal']))
    if return_state:return result,heap,addresses,memory,storage
    return result


TOTALS=('events_checked','buffers_checked','buffer_bytes_checked','heap_boundaries_checked','heap_words_checked','component_bytes_checked','registers_checked','files_checked','file_bytes_checked','unknown_bytes','native_events','native_buffers','native_buffer_bytes','native_boundaries','native_registers')
def run(fixture):
    results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in TOTALS:report[key]=sum(r[key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/shunt_shutdown_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

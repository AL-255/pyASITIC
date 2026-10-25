"""Strict source script/port setup and every native next-entry/fault outcome."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.command_transition import CommandTransition
from reasitic.console_storage import ConsoleStorage
from reasitic.heap import HeapCorruption
from reasitic.memory import UnknownMemory
from reasitic.bridge import _mesh
from reasitic import Technology
from audit_node_history_original import compare as node
from audit_allocator_original import state_differences
from capture_command_transition_original import expand_case


def compare(fixture,entry,*,return_state=False):
    console=ConsoleStorage(entry['console_inputs']);inputs=entry['transition_inputs']
    initial=tuple((r['address'],bytes.fromhex(r['data']))for r in inputs['initial_regions'])
    if 'loader_context'in inputs:
        from audit_loader_lookup_original import data as loader_data
        initial+=tuple((r['address'],loader_data(fixture,r))for r in inputs['loader_context']['regions'])
    before,heap,addresses,memory=node(fixture,entry,return_state=True,console=console,initial_regions=initial)
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],before=before,differences=list(before['differences']),events_checked=0,buffers_checked=0,buffer_bytes_checked=0,heap_words_checked=0,component_words_checked=0,points_checked=0,point_words_checked=0,unknown_bytes=0,console_calls_checked=0,calendar_calls_checked=0,files_checked=0,file_bytes_checked=0,faults_checked=0,stdin_positions_checked=0)
    if entry['post_driver']is None:
        if entry['transition_events']or entry['transition_states']:result['differences'].append(dict(kind='transition-before-driver-return'))
        return (result,heap,addresses,memory)if return_state else result
    case=expand_case(fixture,entry)
    history=CommandTransition(heap,memory,console,inputs,head=case['setup_context']['head'],strings=case['setup_context']['strings'],libio=case['libio_inputs'],technology=case['cache_inputs']['technology'],cells=_mesh(case['request'],Technology.from_text(case['request']['technology'])),script=case['script'].encode(),cache_arrays=case['cache_inputs']['arrays'])
    start=len(console.calls)
    fault=None
    try:history.run()
    except HeapCorruption as error:fault=str(error)
    except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='transition-runtime',reason=str(error)))
    if fault is not None:
        if case['signal']!=6:result['differences'].append(dict(kind='unexpected-transition-fault',reason=fault))
        else:
            result['faults_checked']+=1
            if fault+'\n'not in case['stderr']:result['differences'].append(dict(kind='transition-fault-message',actual=fault,original=case['stderr']))
    elif case['signal']:result['differences'].append(dict(kind='missing-transition-fault',original=case['signal']))
    native=case['transition_events'];actual=history.events
    if len(actual)!=len(native):result['differences'].append(dict(kind='transition-event-count',actual=len(actual),original=len(native)))
    for index,(a,b)in enumerate(zip(actual,native)):
        keys=('kind','allocator','request','address','returned')
        if {k:a[k]for k in keys if k in a}!={k:b[k]for k in keys if k in b}:result['differences'].append(dict(kind='transition-event',index=index,actual=a,original=b))
        result['events_checked']+=1
    def check(address,expected,kind,actual=None,**identity):
        if actual is None:
            try:actual=memory.read(address,len(expected))
            except UnknownMemory:pass
        if actual==expected:return
        if actual is not None and len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',address=address,actual=len(actual),original=len(expected),**identity))
        for offset in range(0,len(expected),4):
            size=min(4,len(expected)-offset)
            try:word=actual[offset:offset+size]if actual is not None else memory.read(address+offset,size)
            except UnknownMemory:result['unknown_bytes']+=size;result['differences'].append(dict(kind='unknown-'+kind,address=address+offset,**identity));continue
            if word!=expected[offset:offset+size]:result['differences'].append(dict(kind=kind,address=address+offset,actual=word.hex(),original=expected[offset:offset+size].hex(),**identity))
    for a,b in zip(history.freed,case['transition_buffers']):
        if (a['event_index'],a['address'],a['size'])!=(b['event_index'],b['address'],b['size']):result['differences'].append(dict(kind='transition-buffer-owner'))
        check(a['address'],bytes.fromhex(b['data']),'transition-free-word',actual=a['data']);result['buffers_checked']+=1;result['buffer_bytes_checked']+=b['size']
    if len(history.freed)!=len(case['transition_buffers']):result['differences'].append(dict(kind='transition-buffer-count',actual=len(history.freed),original=len(case['transition_buffers'])))
    for index,(a,b)in enumerate(zip(history.points,case['transition_points'])):
        result['points_checked']+=1
        if 'stdin_position'in b:
            result['stdin_positions_checked']+=1
            if a.get('stdin_position')!=b['stdin_position']:
                result['differences'].append(dict(kind='transition-point-stdin-position',point=index,actual=a.get('stdin_position'),original=b['stdin_position']))
        if (a['kind'],a['events'])!=(b['kind'],b['events']):result['differences'].append(dict(kind='transition-point',index=index,actual=(a['kind'],a['events']),original=(b['kind'],b['events'])))
        if len(a['regions'])!=len(b['regions']):result['differences'].append(dict(kind='transition-point-region-count',index=index))
        for actual,original in zip(a['regions'],b['regions']):
            if actual['address']!=original['address']:result['differences'].append(dict(kind='transition-point-owner',index=index))
            check(original['address'],bytes.fromhex(original['data']),'transition-point-word',actual=actual['data'],point=index)
            result['point_words_checked']+=len(original['data'])//8
    if len(history.points)!=len(case['transition_points']):result['differences'].append(dict(kind='transition-point-count',actual=len(history.points),original=len(case['transition_points'])))
    for state in case['transition_states']:
        if 'stdin_position'in state:
            result['stdin_positions_checked']+=1
            if history.stdin_position!=state['stdin_position']:
                result['differences'].append(dict(kind='transition-final-stdin-position',actual=history.stdin_position,original=state['stdin_position']))
        result['differences'].extend(state_differences(heap,state,memory=memory))
        for r in state['memory_regions']:
            data=bytes.fromhex(r['data']);check(r['address'],data,'transition-heap-word');result['heap_words_checked']+=len(data)//4
        for r in state['component_regions']:
            data=bytes.fromhex(r['data']);check(r['address'],data,'transition-component-word');result['component_words_checked']+=len(data)//4
    if case['transition_end']is not None:
        if history.result!=dict(driver=case['transition_end']['driver'],arguments=case['transition_end']['arguments']):result['differences'].append(dict(kind='transition-next-driver',actual=history.result,original=case['transition_end']))
        for a,b in zip(history.files,case['transition_end']['files']):
            if a['name'].decode()!=b['name']or a['data']!=bytes.fromhex(b['data']):result['differences'].append(dict(kind='transition-file',name=b['name'],actual=a['data'].hex(),original=b['data']))
            result['files_checked']+=1;result['file_bytes_checked']+=len(b['data'])//2
        if len(history.files)!=len(case['transition_end']['files']):result['differences'].append(dict(kind='transition-file-count'))
    for a,b in zip(history.calendar_calls,case['transition_calendar']):
        if a!={key:b[key]for key in a}:result['differences'].append(dict(kind='transition-calendar',actual=a,original=b))
        result['calendar_calls_checked']+=1
    if len(history.calendar_calls)!=len(case['transition_calendar']):result['differences'].append(dict(kind='transition-calendar-count'))
    generated=console.calls[start:]
    for index,(a,b)in enumerate(zip(generated,case['transition_calls'])):
        if a!=b:result['differences'].append(dict(kind='transition-console',index=index,actual=a,original=b))
        result['console_calls_checked']+=1
    if len(generated)!=len(case['transition_calls']):result['differences'].append(dict(kind='transition-console-count',actual=len(generated),original=len(case['transition_calls'])))
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/command_transition_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','buffers_checked','buffer_bytes_checked','heap_words_checked','component_words_checked','points_checked','point_words_checked','unknown_bytes','console_calls_checked','calendar_calls_checked','files_checked','file_bytes_checked','faults_checked','stdin_positions_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

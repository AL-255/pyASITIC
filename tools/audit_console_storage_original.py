"""Strict source console trace and complete continuous driver heap comparison."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.console_storage import ConsoleStorage
from audit_driver_history_original import compare as driver


def compare(fixture,entry,*,return_state=False):
    console=ConsoleStorage(entry['console_inputs'])
    result,heap,addresses,memory=driver(fixture,entry,return_state=True,console=console)
    original=entry['console_calls'];result['console_calls_checked']=min(len(original),len(console.calls))
    if len(console.calls)!=len(original):result['differences'].append(dict(kind='console-call-count',actual=len(console.calls),original=len(original)))
    for index,(actual,expected)in enumerate(zip(console.calls,original)):
        if actual!=expected:result['differences'].append(dict(kind='console-call',index=index,actual=actual,original=expected))
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/console_storage_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result)
        print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','stores_checked','faults_checked','unknown_targets','cap_words_checked','ind_words_checked','cache_words_checked','cache_boundaries','cap_input_words_checked','ind_input_words_checked','workspace_arrays_checked','workspace_bytes_checked','heap_words_checked','unknown_heap_bytes','heap_boundaries_checked','console_calls_checked'):
        report[key]=sum(r[key]for r in results)
    for key in ('events_checked','allocations_checked','bytes_checked','unknown_bytes','tables_checked','table_bytes_checked'):
        report['driver_'+key]=sum(r['driver'][key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

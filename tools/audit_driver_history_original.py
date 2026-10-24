"""One source-produced heap/memory from driver entry through native node input."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_cache_storage_original import compare as cache
from audit_storage_history_original import compare as numerical
from capture_driver_history_original import expand_case


def compare(fixture,entry,*,return_state=False,console=None,initial_regions=()):
    context=cache(fixture,entry,return_state=True,console=console,initial_regions=initial_regions)
    result,heap,addresses,memory=numerical(expand_case(fixture,entry),context=context,return_state=True,console=console)
    result['driver']=context[0]
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/driver_history_original.json.gz')
    parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result)
        print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','stores_checked','faults_checked','unknown_targets','cap_words_checked','ind_words_checked','cache_words_checked','cache_boundaries','cap_input_words_checked','ind_input_words_checked','workspace_arrays_checked','workspace_bytes_checked','heap_words_checked','unknown_heap_bytes','heap_boundaries_checked'):
        report[key]=sum(r[key]for r in results)
    for key in ('events_checked','allocations_checked','bytes_checked','unknown_bytes','tables_checked','table_bytes_checked'):
        report['driver_'+key]=sum(r['driver'][key]for r in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

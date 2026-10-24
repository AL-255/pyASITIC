"""Earlier allocator state through regenerated matrices and native via effects."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import audit_cap_prelude_original as prelude
import audit_shared_heap_original as shared


def compare(case,*,ported=False):
    prefix,heap,contacts=prelude.compare(case,return_state=True)
    result=dict(label=case['label'],cache_mode=case['cache_mode'],prefix=prefix,body=None,differences=list(prefix['differences']))
    if result['differences']:return result
    cap=shared.ported_capacitance(case)if ported else None
    prepared=shared.ported_impedance(case)if ported else None
    body=shared.compare(case,heap=heap,contact_addresses=contacts,invert=ported,capacitance=cap,impedance=None if prepared is None else prepared.reduced_z)
    result['body']=body;result['differences'].extend(body['differences'])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/cap_prelude_shared_original.json.gz');parser.add_argument('--ported',action='store_true');parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress(options.fixture.read_bytes()));results=[]
    for case in fixture['cases']:
        result=compare(case,ported=options.ported);results.append(result)
        if options.ported:print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),prefix_events=sum(c['prefix']['events']for c in results),prefix_allocations=sum(c['prefix']['allocations_checked']for c in results),differences=sum(len(c['differences'])for c in results),results=results)
    for key in ('allocations_checked','events_checked','stores_checked','faults_checked','via_records_checked','via_index_words_checked','cache_words_checked','cap_input_words_checked','ind_input_words_checked','cap_words_checked','ind_words_checked'):
        report[key]=sum(c['body'][key]for c in results if c['body']is not None)
    report['total_events']=report['prefix_events']+report['events_checked'];report['total_allocations']=report['prefix_allocations']+report['allocations_checked']
    report['predicted_cache_errors']=sum(len(c['body']['predicted_cache_errors'])for c in results if c['body']is not None)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

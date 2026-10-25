"""Strict branch driver continuation through nodes, model output and cleanup."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_node_history_original import compare as node
from audit_shunt_driver_history_original import compare as driver


def compare(fixture,entry,*,return_state=False,console=None,initial_regions=(),observe_driver_boundary=None):
    def producer(*args,**kwargs):return driver(*args,**kwargs,observe_boundary=observe_driver_boundary)
    return node(fixture,entry,return_state=return_state,driver_compare=producer,console=console,initial_regions=initial_regions)


def run(fixture):
    results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result)
        print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('events_checked','allocations_checked','buffers_checked','buffer_bytes_checked','heap_boundaries_checked','heap_words_checked','unknown_heap_bytes','port_words_checked','port_memory_words_checked','unknown_port_bytes','console_calls_checked','faults_checked'):report[key]=sum(r[key]for r in results)
    for key in('events_checked','allocations_checked','stores_checked','workspace_arrays_checked','workspace_bytes_checked','cap_words_checked','ind_words_checked','heap_words_checked','heap_boundaries_checked','early_heap_words_checked','early_heap_boundaries_checked','early_unknown_heap_bytes','unknown_heap_bytes','contact_stack_entries_checked','contact_stack_words_checked'):report['before_'+key]=sum(r['before'][key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_node_history_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'})
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

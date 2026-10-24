"""Strict shared cache-table/heap writes, not isolated padded table outputs."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_libio_storage_original import compare as prelude
from capture_cache_storage_original import expand_files
from project_prelude_storage_original import expand_case


def compare(fixture,entry,*,return_state=False,console=None):
    case=expand_case(fixture,entry);result,heap,addresses,memory=prelude(case,return_state=True,cache_files=tuple(expand_files(fixture,case)),console=console)
    result.update(tables_checked=0,table_bytes_checked=0)
    for record in case['cache_outputs']:
        group=case['cache_inputs']['arrays'][record['name']]
        address=memory.u32(group['pointer_address']+4*record['index']);size=group['size']
        if (address,size)!=(record['address'],record['size']):result['differences'].append(dict(kind='cache-table-owner',name=record['name'],index=record['index'],actual=[address,size],original=[record['address'],record['size']]))
        data=memory.read(address,size);actual=hashlib.sha256(data).hexdigest()
        if actual!=record['sha256']:result['differences'].append(dict(kind='cache-table',name=record['name'],index=record['index'],address=address,actual=actual,original=record['sha256']))
        result['tables_checked']+=1;result['table_bytes_checked']+=len(data)
    if return_state:return result,heap,addresses,memory
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/cache_storage_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture=json.loads(gzip.decompress(args.fixture.read_bytes()));results=[]
    for entry in fixture['cases']:
        result=compare(fixture,entry);results.append(result);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('events_checked','allocations_checked','bytes_checked','unknown_bytes','tables_checked','table_bytes_checked'):report[key]=sum(r[key]for r in results)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

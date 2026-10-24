"""Derive native pivot and workspace arrays from the same matrix algorithms."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.allocation_plan import combined_network_storage
from reasitic.storage_history import symmetric_inverse_storage
from reasitic.vias import stamp
from audit_cap_storage_original import ported_buffers
from audit_cap_prelude_original import dimensions
from audit_shared_heap_original import ported_impedance,via_records


def ported_stores(case):
    prepared=ported_impedance(case);stores={};ported_buffers(case,inverse_storage=stores)
    stores.update(symmetric_inverse_storage(prepared.full,'ind.full_inverse'))
    stores.update(symmetric_inverse_storage(prepared.reduced_y,'ind.reduced_inverse'))
    final=[row.copy()for row in prepared.reduced_z]
    for index,record in via_records(case):
        if index<len(final):
            value=final[index][index];final[index][index]=stamp([[*record,value.real,value.imag]])[0]
    stores.update(symmetric_inverse_storage(final,'ind.final_inverse'))
    return stores


def compare(case):
    stores=ported_stores(case);counts,*_=dimensions(case)
    # Dimensions are also independently checked against request geometry by
    # the existing full preparation/storage comparisons.
    plan=iter(combined_network_storage(counts,case['via']['matrix']['size'],case['matrices']['ind_full']['size'],len(via_records(case)),clone_segments=len(case['via']['segments'])))
    captured={item['event_index']:item for item in case['workspace_storage']}
    result=dict(label=case['label'],cache_mode=case['cache_mode'],differences=[],arrays_checked=0,bytes_checked=0)
    for index,event in enumerate(case['events']):
        if event['kind']not in ('allocate','free'):continue
        expected=next(plan);assert (expected.action,expected.allocator)==(event['kind'],event['allocator'])
        if event['kind']!='free'or expected.name not in stores:continue
        original=captured[index];assert original['address']==event['address']
        values=stores[expected.name]
        actual=b''.join(struct.pack('<i',value)for value in values)if expected.name.endswith('.pivots')else b''.join(struct.pack('<2d',z.real,z.imag)for z in values)
        native=bytes.fromhex(original['data']);assert len(actual)==len(native)==original['size']
        step=4 if expected.name.endswith('.pivots')else 8
        for offset in range(0,len(actual),step):
            if actual[offset:offset+step]!=native[offset:offset+step]:result['differences'].append(dict(name=expected.name,offset=offset,actual=actual[offset:offset+step].hex(),original=native[offset:offset+step].hex()))
        result['arrays_checked']+=1;result['bytes_checked']+=len(actual)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);options=parser.parse_args()
    fixture=json.loads(gzip.decompress((ROOT/'tests/fixtures/workspace_storage_original.json.gz').read_bytes()));results=[]
    assert len(fixture['cases'])==130
    for case in fixture['cases']:
        result=compare(case);results.append(result);print(case['label']+'/'+case['cache_mode']+': '+str(len(result['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in ('arrays_checked','bytes_checked'):report[key]=sum(r[key]for r in results)
    if options.output:options.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items()if key!='results'},separators=(',',':')))
    raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

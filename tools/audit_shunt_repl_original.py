"""All shutdown targets, including new stdio owners and actual printf/IO ABI."""
import argparse,gzip,json,sys
from pathlib import Path
import audit_shunt_shutdown_original as parent
from audit_loader_lookup_original import data

ROOT=Path(__file__).resolve().parents[1]


def compare(fixture,entry,*,return_state=False,observe_malloc=None,observe_cleanup=None):
    result,heap,addresses,memory,storage=parent.compare(fixture,entry,return_state=True,continue_repl=True,observe_malloc=observe_malloc,observe_cleanup=observe_cleanup)
    result.update(printf_calls_checked=0,printf_registers_checked=0,native_io_calls=len(entry['shutdown']['io']),io_calls_checked=0,io_words_checked=0,io_registers_checked=0,io_positions_checked=0,io_unknown_bytes=0)
    actual=storage.history.printf_calls;native=entry['shutdown']['printf']
    if len(actual)!=len(native):result['differences'].append(dict(kind='repl-printf-count',actual=len(actual),original=len(native)))
    for a,b in zip(actual,native):
        result['printf_calls_checked']+=1
        if a['kind']!=b['kind']:result['differences'].append(dict(kind='repl-printf-kind',actual=a['kind'],original=b['kind']))
        for phase in('before','after'):
            if phase not in a or phase not in b:result['differences'].append(dict(kind='repl-printf-phase',phase=phase));continue
            if set(a[phase])!=set(b[phase]):result['differences'].append(dict(kind='repl-printf-register-set',phase=phase))
            for name,value in b[phase].items():
                result['printf_registers_checked']+=1
                if a[phase].get(name)!=value:result['differences'].append(dict(kind='repl-printf-register',phase=phase,name=name,actual=a[phase].get(name),original=value))
    actual_io=storage.io_calls
    for index,call in enumerate(entry['shutdown']['io']):
        # Every complete later target is checked; no call snapshot supplies
        # source state, even when the corresponding execution is missing.
        for phase in('before','after'):
            if phase in call:
                for r in call[phase]['regions']:data(fixture,r)
        if index>=len(actual_io):result['differences'].append(dict(kind='repl-io-continuation-missing',call=call['kind']));continue
        actual=actual_io[index];result['io_calls_checked']+=1
        if actual['kind']!=call['kind']:result['differences'].append(dict(kind='repl-io-kind',call=index,actual=actual['kind'],original=call['kind']))
        for phase in('before','after'):
            if phase not in call or phase not in actual:result['differences'].append(dict(kind='repl-io-phase-missing',call=index,phase=phase));continue
            a,b=actual[phase],call[phase]
            if [(r['address'],r['size'])for r in a['regions']]!=[(r['address'],r['size'])for r in b['regions']]:result['differences'].append(dict(kind='repl-io-region-owners',call=index,phase=phase))
            for left,right in zip(a['regions'],b['regions']):
                expected=data(fixture,right);raw=left['data']
                if raw!=expected:
                    for offset in range(0,len(expected),4):
                        word=raw[offset:offset+4]if raw is not None else left['words'][offset//4]
                        if word is None:result['io_unknown_bytes']+=min(4,len(expected)-offset);result['differences'].append(dict(kind='repl-io-unknown-word',call=index,phase=phase,address=right['address']+offset))
                        elif word!=expected[offset:offset+4]:result['differences'].append(dict(kind='repl-io-word',call=index,phase=phase,address=right['address']+offset,actual=word.hex(),original=expected[offset:offset+4].hex()))
                result['io_words_checked']+=(len(expected)+3)//4
            if set(a['registers'])!=set(b['registers']):result['differences'].append(dict(kind='repl-io-register-set',call=index,phase=phase))
            for name,value in b['registers'].items():
                result['io_registers_checked']+=1
                if a['registers'].get(name)!=value:result['differences'].append(dict(kind='repl-io-register',call=index,phase=phase,name=name,actual=a['registers'].get(name),original=value))
            result['io_positions_checked']+=1
            if a['stdin_position']!=b['stdin_position']:result['differences'].append(dict(kind='repl-io-position',call=index,phase=phase,actual=a['stdin_position'],original=b['stdin_position']))
    if len(actual_io)>len(entry['shutdown']['io']):result['differences'].append(dict(kind='repl-io-extra-calls',actual=len(actual_io)))
    if return_state:return result,heap,addresses,memory,storage
    return result


def run(fixture):
    results=[]
    for entry in fixture['cases']:
        r=compare(fixture,entry);results.append(r);print(entry['label']+'/'+entry['cache_mode']+': '+str(len(r['differences']))+' differences',flush=True)
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in(*parent.TOTALS,'printf_calls_checked','printf_registers_checked','native_io_calls','io_calls_checked','io_words_checked','io_registers_checked','io_positions_checked','io_unknown_bytes'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/shunt_repl_original.json.gz');p.add_argument('--output',type=Path);a=p.parse_args()
    report=run(json.loads(gzip.decompress(a.fixture.read_bytes())))
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

"""Strict once-initialized kill -> signal delivery, including all inner states."""
import argparse,collections,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from reasitic.kill_delivery import deliver_from_kill
from reasitic.signal_frame import legacy_x87

COUNTERS=('calls_checked','boundaries_checked','words_checked','registers_checked','fp_bytes_checked','legacy_bytes_checked','masks_checked')


def compare(fixture,case):
    result=dict(label=case['label'],cache_mode=case['cache_mode'],**dict.fromkeys(COUNTERS,0),differences=[])
    for index,call in enumerate(case['kill_calls']):
        a=call['entry'];m=memory_for(fixture,a);seen=[]
        def check(actual,expected,kind,*,phase,address=0,unit=4):
            if len(actual)!=len(expected):result['differences'].append(dict(kind=kind+'-size',call=index,phase=phase))
            for offset in range(0,len(expected),unit):
                if actual[offset:offset+unit]!=expected[offset:offset+unit]:result['differences'].append(dict(kind=kind,call=index,phase=phase,address=address+offset,actual=actual[offset:offset+unit].hex(),original=expected[offset:offset+unit].hex()))
        def observe(phase,registers,fp,mask):
            seen.append(phase)
            if phase not in call:result['differences'].append(dict(kind='kill-delivery-missing-boundary',call=index,phase=phase));return
            b=call[phase];result['boundaries_checked']+=1
            if[(r['address'],r['size'])for r in a['regions']]!=[(r['address'],r['size'])for r in b['regions']]:result['differences'].append(dict(kind='kill-delivery-region-owners',call=index,phase=phase))
            for region in b['regions']:
                native=data(fixture,region);check(m.read(region['address'],region['size']),native,'kill-delivery-memory-word',phase=phase,address=region['address']);result['words_checked']+=(len(native)+3)//4
            if set(registers)!=set(b['registers']):result['differences'].append(dict(kind='kill-delivery-register-set',call=index,phase=phase))
            for name,value in b['registers'].items():
                result['registers_checked']+=1
                if registers.get(name)!=value:result['differences'].append(dict(kind='kill-delivery-register',call=index,phase=phase,name=name,actual=registers.get(name),original=value))
            check(fp,bytes.fromhex(b['xstate']),'kill-delivery-fp-byte',phase=phase,unit=1);result['fp_bytes_checked']+=len(b['xstate'])//2
            check(legacy_x87(fp,registers),bytes.fromhex(b['fpregs']),'kill-delivery-legacy-byte',phase=phase,unit=1);result['legacy_bytes_checked']+=len(b['fpregs'])//2
            result['masks_checked']+=1
            if mask!=b['mask']:result['differences'].append(dict(kind='kill-delivery-mask',call=index,phase=phase,actual=mask,original=b['mask']))
        check(legacy_x87(bytes.fromhex(a['xstate']),a['registers']),bytes.fromhex(a['fpregs']),'kill-delivery-legacy-byte',phase='entry',unit=1);result['legacy_bytes_checked']+=len(a['fpregs'])//2
        try:
            deliver_from_kill(m,a['registers'],bytes.fromhex(a['xstate']),**{k:a[k]for k in('libc_base','tls_base','number','mask','action','process','thread','vdso')},cpu=fixture['kill_delivery_provenance']['cpu'],observer=observe)
        except (ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='kill-delivery-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        if seen!=['vdso','kernel','interrupted','handler']:result['differences'].append(dict(kind='kill-delivery-boundary-order',call=index,actual=seen))
    if case.get('signal_pending')is not None:result['differences'].append(dict(kind='kill-delivery-pending'))
    return result


def run(fixture):
    results=[compare(fixture,c)for c in fixture['cases']]
    report=dict(cases=len(results),cases_without_kill=sum(not c['kill_calls']for c in fixture['cases']),native_terminal_counts=dict(collections.Counter(c['signal']for c in fixture['cases'])),differences=sum(len(r['differences'])for r in results),results=results)
    for key in COUNTERS:report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/kill_delivery_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

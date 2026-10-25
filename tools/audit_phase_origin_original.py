"""Derive capacitor phase words from earlier native strcmp lazy binding."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_plt_fixup_original import compare as resolver
from audit_loader_lookup_original import memory_for
from reasitic.plt_fixup_storage import PltFixup


def compare(fixture,case):
    result=resolver(fixture,dict(case,cache_mode='startup'));result['phase_words_checked']=0
    differences=result['differences'];context=case['phase_context'];final=case['final_context']
    def check(kind,actual,expected):
        if actual!=expected:differences.append(dict(kind=kind,actual=actual,original=expected))
    check('phase-resolver-count',len(case['plt_calls']),1)
    if len(case['plt_calls'])!=1:return result
    call=case['plt_calls'][0];before=call['before'];memory=memory_for(fixture,before)
    engine=PltFixup(memory,before['loader_base'],tls_base=before['tls_base'])
    # Resolve entirely from earlier ELF, CPU, TLS and frame inputs. A later
    # constructor address is used only to inspect/assert the generated store.
    engine.resolve(before['registers']);slot=before['registers']['esp']-140;phase=memory.u32(slot)
    check('phase-slot-owner',slot,context['address']);check('phase-intervening-changes',context['write_count'],0)
    check('phase-ELF-symbol-name',memory.read(phase,7).hex(),b'strcmp\0'.hex())
    for key,target in(('constructor',context['phase']),('descriptor',final['phase'])):
        check('phase-'+key,phase,target);result['phase_words_checked']+=1
    for key,raw in(('constructor',context['argument_data']),('descriptor',final['descriptor'])):
        check('phase-'+key+'-raw',phase,struct.unpack_from('<I',bytes.fromhex(raw),0xac)[0]);result['phase_words_checked']+=1
    return result


def run(fixture):
    results=[compare(fixture,c)for c in fixture['cases']]
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('calls_checked','words_checked','registers_checked','fp_bytes_checked','phase_words_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();report=run(json.loads(gzip.decompress((ROOT/'tests/fixtures/phase_origin_original.json.gz').read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

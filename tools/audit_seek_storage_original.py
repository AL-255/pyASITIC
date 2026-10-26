"""Independent seek/sync component assertions; never a continuation seed."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from audit_loader_lookup_original import data,memory_for
from reasitic.seek_storage import SeekStorage
from reasitic.flush_storage import FlushStorage
from reasitic.plt_fixup_storage import PltFixup


def engine(fixture,entry,call):
    ctx=entry['transition_inputs']['loader_context'];before=call['before']
    # This is an isolated component test with its own earlier call input.
    # The complete process audit never loads these per-call regions.
    m=memory_for(fixture,dict(regions=ctx['regions']+before['regions']))
    base=entry['libio_inputs']['libc_base'];positions={0:before['stdin_position']}
    if call['kind']in('fflush','sync'):
        storage=FlushStorage(m,PltFixup(m,ctx['loader_base'],tls_base=ctx['tls_base']),ctx,libc_base=base,tls_base=ctx['tls_base'],positions=positions)
    else:storage=SeekStorage(m,libc_base=base,tls_base=ctx['tls_base'],positions=positions)
    return m,storage


def compare(fixture,entry):
    result=dict(label=entry['label'],cache_mode=entry['cache_mode'],differences=[],calls_checked=0,words_checked=0,registers_checked=0,positions_checked=0)
    for index,call in enumerate(entry['shutdown']['io']):
        if call['kind']not in('llseek','file_seek','fflush','sync'):continue
        if 'after'not in call:result['differences'].append(dict(kind='seek-missing-return',call=index));continue
        before,after=call['before'],call['after'];m,storage=engine(fixture,entry,call)
        try:actual=getattr(storage,'_sync'if call['kind']=='sync'else'flush'if call['kind']=='fflush'else call['kind'])(before['registers'])
        except(ValueError,NotImplementedError)as error:result['differences'].append(dict(kind='seek-runtime',call=index,reason=str(error)));continue
        result['calls_checked']+=1
        if [(r['address'],r['size'])for r in before['regions']]!=[(r['address'],r['size'])for r in after['regions']]:result['differences'].append(dict(kind='seek-region-owners',call=index))
        for region in after['regions']:
            expected=data(fixture,region);raw=m.read(region['address'],len(expected))
            if raw!=expected:
                for offset in range(0,len(expected),4):
                    if raw[offset:offset+4]!=expected[offset:offset+4]:result['differences'].append(dict(kind='seek-memory-word',call=index,address=region['address']+offset,actual=raw[offset:offset+4].hex(),original=expected[offset:offset+4].hex()))
            result['words_checked']+=(len(expected)+3)//4
        if set(actual)!=set(after['registers']):result['differences'].append(dict(kind='seek-register-set',call=index))
        for name,value in after['registers'].items():
            result['registers_checked']+=1
            if actual.get(name)!=value:result['differences'].append(dict(kind='seek-register',call=index,name=name,actual=actual.get(name),original=value))
        result['positions_checked']+=1
        if storage.positions[0]!=after['stdin_position']:result['differences'].append(dict(kind='seek-position',call=index,actual=storage.positions[0],original=after['stdin_position']))
    return result


def run(fixture):
    results=[compare(fixture,c)for c in fixture['cases']]
    report=dict(cases=len(results),differences=sum(len(r['differences'])for r in results),results=results)
    for key in('calls_checked','words_checked','registers_checked','positions_checked'):report[key]=sum(r[key]for r in results)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    f=json.loads(gzip.decompress((ROOT/'tests/fixtures/shunt_repl_original.json.gz').read_bytes()));report=run(f)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

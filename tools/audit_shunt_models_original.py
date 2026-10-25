"""Strict complete original JOINSHUNT model and both node-input matrices."""
import argparse,gzip,json,math,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.bridge import handle
from reasitic.network_metrics import PI_KEYS
from reasitic.transformer import MODEL_KEYS
from reasitic.retained_scalar import Real


def compare(case):
    report=dict(label=case['label'],matrix_words_checked=0,output_words_checked=0,undefined_metrics_checked=0,differences=[])
    try:result=handle(dict(case['request'],include_matrices=True))
    except (ValueError,NotImplementedError)as error:report['differences'].append(dict(kind='shunt-model-runtime',reason=str(error)));return report
    def check(value,target,kind,where):
        expected=struct.unpack('<d',bytes.fromhex(target))[0]
        if value is None and not math.isfinite(expected):report['undefined_metrics_checked']+=1;return
        actual=struct.pack('<d',value).hex()if value is not None else None
        if actual!=target:report['differences'].append(dict(kind=kind,where=where,actual=actual,original=target))
    for ni,node in enumerate(case['nodes']):
        for name,key in(('capacitance','capacitance_matrix'),('inductance','inductive_admittance_matrix')):
            n=node['size'];target=bytes.fromhex(node[name]);actual=result[key]
            if len(actual)!=n or any(len(row)!=n for row in actual):report['differences'].append(dict(kind='shunt-matrix-size',matrix=key,node=ni));continue
            if len(target)!=16*n*n:raise ValueError('Incomplete native shunt node matrix')
            for j in range(n):
                for i in range(n):
                    for k in range(2):
                        at=16*(j*n+i)+8*k;check(actual[i][j][k],target[at:at+8].hex(),key,[ni,i,j,k]);report['matrix_words_checked']+=1
    y=result['admittance_matrix'];values=[v for cell in(y[1][1],y[1][0],y[0][1],y[0][0])for v in cell]
    if case['request']['action']=='calctrans':
        z=result['impedance_matrix'];values.extend(v for cell in(z[0][0],z[0][1],z[1][0],z[1][1])for v in cell);values.extend(result['model'][key]for key in MODEL_KEYS);targets=case['raw_output_bits'][:23];scattering=case['records'][0]['S']
        if case['raw_output_bits'][:23]!=case['raw_output_bits'][23:]:report['differences'].append(dict(kind='shunt-native-repeated-model'))
    else:
        targets=case['model']['Y']+case['model']['M'];values.extend([result['frequency_hz'],*[result['pi'][key]for key in PI_KEYS]]);scattering=case['scattering']['S']
        raw=bytes.fromhex(case['resonance']['extended_bits']);lo,hi,exp=struct.unpack('<IIH',raw);expected=struct.pack('<d',float(Real.from_words(lo,hi,exp))).hex();check(result['pi']['resonant_frequency_hz'],expected,'resonance',0);report['output_words_checked']+=1
        if case['scattering']['Y']!=case['model']['Y']:report['differences'].append(dict(kind='shunt-native-repeated-model'))
    if len(values)!=len(targets):report['differences'].append(dict(kind='shunt-output-size'))
    for i,(value,target)in enumerate(zip(values,targets)):check(value,target,'model',i);report['output_words_checked']+=1
    values=[v for row in result['scattering_matrix']for cell in row for v in cell]
    for i,(value,target)in enumerate(zip(values,scattering)):check(value,target,'scattering',i);report['output_words_checked']+=1
    return report


def run(fixture):
    results=[]
    for case in fixture['cases']:results.append(compare(case))
    report=dict(cases=len(results),differences=sum(len(c['differences'])for c in results),results=results)
    for key in('matrix_words_checked','output_words_checked','undefined_metrics_checked'):report[key]=sum(c[key]for c in results)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/shunt_sessions_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args();report=run(json.loads(gzip.decompress(args.fixture.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k!='results'});raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

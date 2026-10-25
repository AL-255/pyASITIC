"""Strict original upper impedance entries for all eight UNJOIN model sessions."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.impedance import assemble
from reasitic.inductance import segment_mutual


def compare(case):
    if len(case['records'])!=case['n']:raise ValueError('Incomplete native filament records')
    wires=[struct.unpack('<8d',bytes.fromhex(r['wire_bits']))for r in case['records']]
    pairs=[segment_mutual(first,second)for i,first in enumerate(wires)for second in wires[i+1:]]
    matrix=assemble(wires,[(r['sheet_resistance'],r['thickness_count'])for r in case['records']],pairs,case['frequency'])
    expected=bytes.fromhex(case['upper_bits']);at=0;differences=[]
    if len(expected)!=case['n']*(case['n']+1)//2*16:raise ValueError('Incomplete native upper matrix')
    for j in range(case['n']):
        for i in range(j+1):
            actual=struct.pack('<2d',matrix[i][j].real,matrix[i][j].imag)
            if actual!=expected[at:at+16]:differences.append(dict(kind='upper-entry',first=i,second=j,actual=actual.hex(),original=expected[at:at+16].hex()))
            at+=16
    return dict(label=case['label'],filaments=case['n'],upper_entries_checked=at//16,differences=differences)


def compare_traces(fixture):
    from audit_mutual_command_traces_original import doubles,f64,instruction,raw
    from reasitic.mutual_geometry import canonical,planar,spatial
    from reasitic.parallel import segment_self_inductance,cross_section_log_integral,effective_separation,parallel_segment_mutual
    from reasitic.polygon import _trig
    counts={};differences=[]
    for case in fixture['cases']:
        def check(kind,actual,expected,where):
            counts[kind]=counts.get(kind,0)+1
            if actual!=expected:differences.append(dict(label=case['label'],first=case['first'],second=case['second'],kind=kind,where=where,actual=actual,original=expected))
        args=doubles(case['input_bits']);check('complete-pair',f64(segment_mutual(args[:8],args[8:])),case['output_bits'],'segment_mutual')
        for index,event in enumerate(case['events']):
            kind=event['kind']
            if kind=='canonical':
                first,second=doubles(event['first_bits']),doubles(event['second_bits']);status=canonical(first,second)
                check('canonical-status',status,event['status'],index);check('canonical-coordinates',struct.pack('<16d',*first,*second).hex(),event['first_output_bits']+event['second_output_bits'],index)
            elif kind in('parallel','planar','spatial'):
                first,second=doubles(event['first_bits']),doubles(event['second_bits'])
                if kind=='parallel':
                    status,value=parallel_segment_mutual(first,second,doubles(event['separation_bits'])[0]);check('parallel-status',status,event['status'],index)
                else:value=(planar if kind=='planar'else spatial)(first,second)
                check(kind,f64(value),event['output_bits'],index)
            else:
                value={'self':segment_self_inductance,'crosslog':cross_section_log_integral,'separation':effective_separation}[kind](*doubles(event['input_bits']));check(kind,raw(value),event['extended_bits'],index)
            for op in event.get('math',[]):
                if op['operation']=='fsin':
                    from audit_mutual_command_traces_original import operand
                    value=_trig(operand(op['input_words'][0]),False)
                else:value=instruction(op)
                check(op['operation'],raw(value),op['output_words'],op['address'])
    return dict(cases=len(fixture['cases']),counts=counts,differences=differences)


def compare_model(case,assembly):
    """Observe actual production inputs/results; native values only assert them."""
    from unittest.mock import patch
    from reasitic.bridge import handle
    from reasitic import solver
    from reasitic.transformer import MODEL_KEYS
    counts={};differences=[];calls=[];original=solver.assemble_impedance
    def observe(wires,metadata,pairs,frequency):
        result=original(wires,metadata,pairs,frequency)
        calls.append((wires,metadata,result));return result
    with patch.object(solver,'assemble_impedance',observe):result=handle(dict(case['request'],include_matrices=True))
    def check(kind,actual,expected,where):
        counts[kind]=counts.get(kind,0)+1
        if actual!=expected:differences.append(dict(kind=kind,where=where,actual=actual,original=expected))
    check('assembly-calls',len(calls),1,'prepare_impedance')
    if calls:
        wires,metadata,upper=calls[0];check('filament-count',len(wires),assembly['n'],'prepare_impedance')
        for i,(wire,material,native)in enumerate(zip(wires,metadata,assembly['records'])):
            check('filament-input',struct.pack('<8d',*wire).hex(),native['wire_bits'],i)
            check('filament-material',struct.pack('<2d',*material).hex(),struct.pack('<2d',native['sheet_resistance'],native['thickness_count']).hex(),i)
        target=bytes.fromhex(assembly['upper_bits']);at=0
        for j in range(assembly['n']):
            for i in range(j+1):
                check('production-upper',struct.pack('<2d',upper[i][j].real,upper[i][j].imag).hex(),target[at:at+16].hex(),[i,j]);at+=16
    for native,key in(('capacitance','capacitance_matrix'),('inductance','inductive_admittance_matrix')):
        target=bytes.fromhex(case['nodes'][0][native]);n=case['nodes'][0]['size'];matrix=result[key]
        if len(matrix)!=n or any(len(row)!=n for row in matrix):raise ValueError('Production matrix dimensions differ from native nodes')
        for j in range(n):
            for i in range(n):
                for k in range(2):
                    at=16*(j*n+i)+8*k;check(key,struct.pack('<d',matrix[i][j][k]).hex(),target[at:at+8].hex(),[i,j,k])
    y=result['admittance_matrix'];z=result['impedance_matrix']
    values=[v for cell in(y[1][1],y[1][0],y[0][1],y[0][0],z[0][0],z[0][1],z[1][0],z[1][1])for v in cell]+[result['model'][key]for key in MODEL_KEYS]
    for i,(value,target)in enumerate(zip(values,case['raw_output_bits'][:23])):check('model',struct.pack('<d',value).hex(),target,i)
    for i,(value,target)in enumerate(zip((v for row in result['scattering_matrix']for cell in row for v in cell),case['records'][0]['S'])):check('scattering',struct.pack('<d',value).hex(),target,i)
    return dict(label=case['label'],counts=counts,differences=differences)


def run(fixture):
    results=[compare(c)for c in fixture['cases']]
    return dict(cases=len(results),upper_entries_checked=sum(r['upper_entries_checked']for r in results),differences=sum(len(r['differences'])for r in results),results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/unjoin_assembly_original.json.gz');parser.add_argument('--traces',type=Path,default=ROOT/'tests/fixtures/unjoin_mutual_traces_original.json.gz');parser.add_argument('--models',type=Path,default=ROOT/'tests/fixtures/unjoin_sessions_original.json.gz');parser.add_argument('--output',type=Path);args=parser.parse_args()
    fixture,traces,models=(json.loads(gzip.decompress(p.read_bytes()))for p in(args.fixture,args.traces,args.models));report=run(fixture);report['traces']=compare_traces(traces)
    labels={c['label']for c in traces['cases']}
    if len(labels)!=1:raise ValueError('This production diagnostic requires one complete traced model')
    label=labels.pop();model=next(c for c in models['cases']if c['label']==label);assembly=next(c for c in fixture['cases']if c['label']==label);report['model']=compare_model(model,assembly)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['results']:print(case['label'],case['upper_entries_checked'],'upper entries;',len(case['differences']),'differences')
    print({k:v for k,v in report.items()if k not in('results','traces','model')})
    for key in('traces','model'):print(key,report[key]['counts'],'differences',len(report[key]['differences']))
    raise SystemExit(int(bool(report['differences']or report['traces']['differences']or report['model']['differences'])))


if __name__=='__main__':main()

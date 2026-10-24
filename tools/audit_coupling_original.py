"""Strict complete COUPLING replay; optional pair traces and previous-runtime comparison."""
import argparse,collections,gzip,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_coupling_original import shapes,bits,raw
from reasitic.coupling_metrics import retained_coupling


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pairs',action='store_true');parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
    cases=json.loads(gzip.decompress((ROOT/'tests/fixtures/coupling_original.json.gz').read_bytes()))['cases'];counts=collections.Counter();different=collections.Counter();details=[];old=None
    if args.baseline:
        source=subprocess.check_output(['git','show','4ba28b787be3c103ace55bdbb34cc794aae26a89:src/reasitic/inductance.py'],cwd=ROOT,text=True)
        namespace={'__name__':'reasitic._baseline_coupling','__package__':'reasitic'};exec(compile(source,'baseline_coupling','exec'),namespace);old=namespace['coupling_estimate']
    for c in cases:
        if not c['calls']:counts['native_rejected_histories']+=1;continue
        tech,initial=shapes(c);by_name={s.name:s for s in initial}
        if old is not None:_,before=shapes(c);baseline={s.name:s for s in before}
        for index,(e,report)in enumerate(zip(c['calls'],c['reports'])):
            def compare(kind,actual,want):
                category=kind.split('/',1)[0];counts[category]+=1
                if actual!=want:different[category]+=1;details.append((c['label'],index,kind,actual,want))
            names=[e[side+'_before']['name']for side in('first','second')];a,b=(by_name[n]for n in names);seen=[]
            if old is not None:
                m,k=old(*(baseline[n]for n in names),tech);counts['baseline_M_differences']+=bits(m)!=report['mutual_bits'];counts['baseline_k_differences']+=bits(k)!=report['coefficient_bits']
            m,k=retained_coupling(a,b,tech,seen.append if args.pairs else None)
            compare('M_F64',bits(m),report['mutual_bits']);compare('k_F64',bits(k),report['coefficient_bits']);compare('k_R80',raw(k),e['extended_bits'])
            for side,shape in[('first',a),('second',b)]:
                expected=e[side+'_after'];actual=struct.pack('<'+'d'*6*len(shape.segments),*(v for p in shape.segments for point in(p.start,p.end)for v in point)).hex();compare(side+'_centerlines',actual,''.join(p['endpoints_bits']for p in expected['segments']))
            if args.pairs:
                compare('pair_count',len(seen),len(e['pairs']));ia=[i for i,p in enumerate(e['first_before']['segments'])if not p['via']];ib=[i for i,p in enumerate(e['second_before']['segments'])if not p['via']]
                for pair_index,(got,want)in enumerate(zip(seen,e['pairs'])):
                    compare('pair_indices',(ia[got['first']],ib[got['second']]),(want['first'],want['second']));compare('pair_inputs',struct.pack('<16d',*got['inputs']).hex(),want['input_bits']);compare('pair_F64/'+str(pair_index),bits(got['value']),want['value_bits']);compare('pair_sum_F64',bits(got['sum']),want['sum_bits'])
    print('Original COUPLING audit:',dict(counts));print('Strict differences:',dict(different))
    for detail in details:print(detail)
    raise SystemExit(bool(different))


if __name__=='__main__':main()

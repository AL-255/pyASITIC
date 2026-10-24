"""Strict native FYL2X/FYL2XP1 audit; exits nonzero for every remaining difference.

The instruction driver is separate from the unchanged ASITIC captures. Its 67
shared operands must reproduce those original instruction words exactly.
The optional P5/P6 experiment is never used by the application.
"""
import argparse,collections,gzip,hashlib,importlib.util,json,struct,sys
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.retained_scalar import Real as R
from reasitic.impedance import _log
LN2=Fraction(0xb17217f7d1cf79ac,1<<64)


def operand(words):return R.from_words(*struct.unpack('<IIH',bytes.fromhex(words)))
def raw(value):return struct.pack('<IIH',*value.words()).hex()


def guarded(x,y,*,plus=False):
    """Current guarded arithmetic; natural log calls the actual Python helper."""
    if not plus and y.value==LN2:return _log(x)
    if plus and not x.value:return R(-0. if x.negative^y.negative else 0.)
    with localcontext()as context:
        context.prec=100;v=Decimal(x.value.numerator)/Decimal(x.value.denominator)
        if plus:
            # Same guarded series as the current native-atanh log1p branch,
            # evaluated at the captured FYL2XP1 input without an extra spill.
            z=v/(Decimal(2)+v);square=z*z;power=total=z
            for i in range(1,65):power*=square;total+=power/(2*i+1)
            value=2*total/Decimal(2).ln()
        else:value=v.ln()/Decimal(2).ln()
        return R._result(Fraction(value)*y.value,negative=x.negative^y.negative)


def load_fixture():
    root=ROOT/'tests/fixtures';f=json.loads(gzip.decompress((root/'log_instructions_native.json.gz').read_bytes()))
    assert f['control_before']==f['control_after']==0x37f
    assert hashlib.sha256(f['source'].encode()).hexdigest()==f['source_sha256']
    parents={}
    for name,digest in f['parents'].items():
        data=(root/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest;parents[name]=json.loads(data)
    for row in f['cases']:
        if 'parent'in row:
            name,ci,ei,mi=row['parent'];source=parents[name]['cases'][ci]['events'][ei]['math'][mi]
            assert row['input_words']==source['input_words']
            assert row['output_words']==row['original_output_words']==source['output_words']
    return f


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--p6-experiment',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    algorithms={'guarded':guarded}
    if a.p6_experiment:
        path=ROOT/'tools/experiments/p6_log/candidate.py';spec=importlib.util.spec_from_file_location('p6_log_candidate',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);algorithms['p6_experiment']=module.logarithm
    f=load_fixture();counts={name:collections.Counter()for name in algorithms};differences=[]
    for i,row in enumerate(f['cases']):
        x,y=map(operand,row['input_words']);expected=operand(row['output_words'])
        for name,calculate in algorithms.items():
            actual=calculate(x,y,plus=bool(row['operation']));c=counts[name];c['total']+=1
            if raw(actual)!=row['output_words']:
                c['raw_differences']+=1;c['label/'+row['label']]+=1
                if struct.pack('<d',float(actual))!=struct.pack('<d',float(expected)):c['binary64_differences']+=1
                differences.append(dict(index=i,algorithm=name,label=row['label'],operation=row['operation'],input_words=row['input_words'],actual_words=raw(actual),native_words=row['output_words']))
    result=dict(cpu=f['cpu'],counts=counts,differences=differences)
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    else:
        for difference in differences:print(json.dumps(difference,separators=(',',':')))
    print(json.dumps(dict(cpu=f['cpu'],counts=counts),separators=(',',':')))
    raise SystemExit(int(bool(differences)))


if __name__=='__main__':main()

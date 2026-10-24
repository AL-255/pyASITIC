"""Strict native trig audit, including an explicitly experimental rounding model.

The 68-bit intermediate hypothesis is motivated by the separately captured
logarithm multiplier lattice, not by a correction for any selected angle.
It is not used by the application. Every remaining difference fails the audit.
"""
import argparse,collections,gzip,hashlib,json,struct,sys
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from reasitic.retained_scalar import Real as R,_exponent,_power
from reasitic.polygon import _trig,NATIVE_PI,TRUE_PI
from audit_log_instructions_native import operand,raw


def load_fixture():
    root=ROOT/'tests/fixtures';f=json.loads(gzip.decompress((root/'trig_instructions_native.json.gz').read_bytes()))
    assert f['control_before']==f['control_after']==0x37f
    assert hashlib.sha256(f['source'].encode()).hexdigest()==f['source_sha256']
    parents={}
    for name,digest in f['parents'].items():
        data=(root/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        parents[name]=json.loads(gzip.decompress(data)if name.endswith('.gz')else data)
    anchors=0
    for row in f['cases']:
        if 'parent'in row:
            name,ci,ei,mi=row['parent'];source=parents[name]['cases'][ci]['events'][ei]['math'][mi]
            assert row['input_words']==source['input_words']
            assert row['output_words']==row['original_output_words']==source['output_words'];anchors+=1
    assert anchors==f['original_anchor_count']
    return f


def ideal(x,cosine,*,scaled=True):
    """Guarded Fraction result before the final retained-significand rounding."""
    with localcontext()as context:
        context.prec=100
        if scaled:
            q=R._result(abs(x).value/(NATIVE_PI/2)).value
            n,r=divmod(q.numerator,q.denominator)
            if 2*r>q.denominator or(2*r==q.denominator and n&1):n+=1
            reduced=(abs(x).value-n*NATIVE_PI/2)/NATIVE_PI
            z=Decimal(reduced.numerator)/Decimal(reduced.denominator)*TRUE_PI
        else:
            v=Decimal(abs(x).value.numerator)/Decimal(abs(x).value.denominator)
            n=int((v/(TRUE_PI/2)).to_integral_value(rounding=ROUND_HALF_EVEN));z=v-Decimal(n)*TRUE_PI/2
        evaluate_cosine=not n%2 if cosine else bool(n%2)
        term=Decimal(1)if evaluate_cosine else z;total=term;square=-z*z
        for i in range(1,65):
            term=term*square/((2*i-1)*(2*i)if evaluate_cosine else(2*i)*(2*i+1));total+=term
        negate=(n%4 in(1,2))if cosine else(n%4 in(2,3))
        if negate!= (not cosine and x.negative):total=-total
        return Fraction(total)


def rounded(value,bits):
    if not value:return value
    sign=-1 if value<0 else 1;v=abs(value);step=_power(_exponent(v)-bits+1)
    scaled=v/step;q,r=divmod(scaled.numerator,scaled.denominator)
    if 2*r>scaled.denominator or(2*r==scaled.denominator and q&1):q+=1
    return sign*q*step


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();f=load_fixture()
    names=('current_scaled','unscaled_ideal','scaled_68_intermediate')
    counts={name:collections.Counter()for name in names};differences=[]
    for index,row in enumerate(f['cases']):
        x=operand(row['input_words'][0]);cosine=not row['operation'];expected=operand(row['output_words'])
        current=_trig(x,cosine)
        if not x.value or abs(x)>=R(2.**63):actuals=dict.fromkeys(names,current)
        else:
            scaled=ideal(x,cosine);assert raw(R._result(scaled))==raw(current),'Guarded audit must reproduce current runtime'
            actuals=dict(current_scaled=current,unscaled_ideal=R._result(ideal(x,cosine,scaled=False)),scaled_68_intermediate=R._result(rounded(scaled,68)))
        for name,actual in actuals.items():
            c=counts[name];c['total']+=1
            if raw(actual)!=row['output_words']:
                c['raw_differences']+=1;c['label/'+row['label']]+=1
                stored=struct.pack('<d',float(actual));native=struct.pack('<d',float(expected))
                if stored!=native:c['binary64_differences']+=1
                differences.append(dict(index=index,algorithm=name,label=row['label'],operation=row['operation'],input_words=row['input_words'],actual_words=raw(actual),native_words=row['output_words'],actual_binary64=stored.hex(),native_binary64=native.hex()))
    report=dict(cpu=f['cpu'],counts=counts,differences=differences)
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cpu=f['cpu'],counts=counts),separators=(',',':')))
    raise SystemExit(int(bool(differences)))


if __name__=='__main__':main()

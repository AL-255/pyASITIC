"""Infer native logarithm width under a single final nearest-even multiply model.

This is an instruction-evidence audit. It neither substitutes captured values
into the simulator nor identifies the processor's polynomial or table rules.
"""
import argparse,collections,gzip,hashlib,json,struct,sys
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.retained_scalar import Real as R,_exponent


def operand(words):return R.from_words(*struct.unpack('<IIH',bytes.fromhex(words)))


def infer(rows):
    groups=collections.defaultdict(list)
    for row in rows:
        if 'group'in row:groups[row['group']].append(row)
    result=[]
    for group,records in sorted(groups.items()):
        lower=upper=None;lower_closed=upper_closed=False;signatures=set()
        for row in records:
            signatures.add((row['operation'],row['input_words'][0]))
            output=operand(row['output_words']);multiplier=operand(row['input_words'][1]);out=abs(output.value);y=multiplier.value
            assert not output.kind and not multiplier.kind and out and y>0
            e=_exponent(out);step=Fraction(2)**(e-63)
            down=step if out!=Fraction(2)**e else step/2
            lo=(out-down/2)/y;hi=(out+step/2)/y;closed=not(struct.unpack('<QH',bytes.fromhex(row['output_words']))[0]&1)
            if lower is None or lo>lower:lower,lower_closed=lo,closed
            elif lo==lower:lower_closed=lower_closed and closed
            if upper is None or hi<upper:upper,upper_closed=hi,closed
            elif hi==upper:upper_closed=upper_closed and closed
        assert len(signatures)==1
        nonempty=lower<upper or(lower==upper and lower_closed and upper_closed)
        lattices={}
        if nonempty:
            for bits in range(64,81):
                scale=Fraction(2)**(_exponent(upper)-bits+1);lo=-(-lower//scale);hi=upper//scale
                if not lower_closed and lo*scale==lower:lo+=1
                if not upper_closed and hi*scale==upper:hi-=1
                lattices[bits]=dict(count=max(0,int(hi-lo+1)),significand=hex(lo)if lo==hi else None,binary_exponent=_exponent(upper)-bits+1)
        result.append(dict(group=group,operation=records[0]['operation'],input_words=records[0]['input_words'][0],records=len(records),intersection_nonempty=nonempty,lattices=lattices))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    f=json.loads(gzip.decompress((ROOT/'tests/fixtures/log_multipliers_native.json.gz').read_bytes()))
    assert f['control_before']==f['control_after']==0x37f
    for name,digest in f['parents'].items():assert hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest()==digest
    groups=infer(f['cases']);assert len(groups)==10 and all(g['records']==1026 for g in groups)
    result=dict(model='One input-dependent logarithm followed by exact multiplication and nearest-even rounding to a 64-bit significand; masked exception flags excluded.',cpu=f['cpu'],groups=groups)
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    for g in groups:print(f"Group {g['group']}: intersection {g['intersection_nonempty']}; 67-bit candidates {g['lattices'].get(67,{}).get('count',0)}; 68-bit candidates {g['lattices'].get(68,{}).get('count',0)}")
    # These are consistency checks on the stated inference model, not a
    # simulator-equivalence gate. No recovered constants enter runtime code.
    assert all(g['intersection_nonempty']and g['lattices'][68]['count']==1 for g in groups)


if __name__=='__main__':main()

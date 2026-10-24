"""Audit consumed transition stores; --raw also requires finite ST0 parity."""
import collections,json,math,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.symmetric_inputs import transition


def main():
    cases=json.loads((ROOT/'tests/fixtures/transition_original.json').read_text())['cases']
    raw=collections.Counter();differences=[];count=0
    for i,c in enumerate(cases):
        if 'inner_gap'not in c['parameters']:continue
        result=transition(*(struct.unpack('<d',bytes.fromhex(c[k]))[0]for k in('width_bits','spacing_bits','gap_bits')));count+=1
        if result['reject']!=c['reject']:differences.append((i,'decision'))
        for key,field in [('radius64','radius_bits'),('acos64','acos_bits'),('tangent64','tangent_bits')]:
            expected=struct.unpack('<d',bytes.fromhex(c[field]))[0]
            if not(math.isnan(expected)and math.isnan(result[key]))and struct.pack('<d',result[key]).hex()!=c[field]:differences.append((i,key))
        fields=[('radius','radius80'),('angle','angle80'),('acos','acos80'),('half','half80'),('tangent','tan80')]
        fields.extend([('extent',('compare80',0)),('limit',('compare80',1))])
        for key,field in fields:
            expected=c['points'][field]if isinstance(field,str)else c['points'][field[0]][field[1]]
            _,exponent=struct.unpack('<QH',bytes.fromhex(expected))
            if exponent&0x7fff!=0x7fff and struct.pack('<IIH',*result[key].words()).hex()!=expected:raw[key]+=1
    print(f'{count} original explicit transition histories: {len(differences)} decision/binary64/class differences; finite raw retained differences {dict(raw)}.')
    if differences:print(differences)
    raise SystemExit(bool(differences or('--raw'in sys.argv and raw)))


if __name__=='__main__':main()

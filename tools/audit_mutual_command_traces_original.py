"""Strict replay of original complete-command mutual helper/instruction stores.

This diagnostic currently exits nonzero. It records remaining differences rather
than replacing native words with ideal mathematical results or accepting a
numeric tolerance. Helper replay uses each actual native call's inputs, which
separates an instruction difference from later propagation through cancellation.
"""
import collections,gzip,hashlib,json,struct,sys
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from reasitic.conductor_metrics import _operand
from reasitic.retained_scalar import Real as R
from reasitic.impedance import _log
from reasitic.inductance import segment_mutual
from reasitic.mutual_geometry import canonical,planar,spatial,angle
from reasitic.parallel import segment_self_inductance,cross_section_log_integral,effective_separation,parallel_segment_mutual
from reasitic.polygon import _trig


def raw(value):return struct.pack('<IIH',*value.words()).hex()
def f64(value):return struct.pack('<d',float(value)).hex()
def operand(value):return _operand(struct.unpack('<IIH',bytes.fromhex(value)))
def doubles(value):return list(struct.unpack('<'+'d'*(len(value)//16),bytes.fromhex(value)))


def instruction(event):
    op=event['operation'];args=list(map(operand,event['input_words']));x=args[0]
    if op=='fyl2x':
        # All captured log instructions load FLDLN2 as their second operand.
        assert raw(args[1])=='ac79cfd1f71772b1fe3f'
        return _log(x)
    if op=='fyl2xp1':
        assert raw(args[1])=='ac79cfd1f71772b1fe3f'
        # Same guarded log1p evaluation used in mutual_geometry.atanh, starting
        # at the native FYL2XP1 input rather than recomputing its upstream u.
        with localcontext()as context:
            context.prec=100;v=Decimal(x.value.numerator)/Decimal(x.value.denominator)
            z=v/(Decimal(2)+v);square=z*z;power=total=z
            for i in range(1,65):power*=square;total+=power/(2*i+1)
            return R._result(Fraction(2*total/Decimal(2).ln())*args[1].value,negative=x.negative)
    if op=='fpatan':return angle(args[1],x)
    if op=='fcos':return _trig(x,True)
    if op=='frndint':return R(round(x.value))
    if op=='fscale':return x*R(Fraction(2)**int(args[1].value))
    if op=='f2xm1':
        with localcontext()as context:
            context.prec=100;v=Decimal(x.value.numerator)/Decimal(x.value.denominator)
            return R._result(Fraction(Decimal(2)**v-1),negative=x.negative)
    raise ValueError('Unimplemented observed instruction '+op)


def main():
    from test_conductor_metrics_original import rows
    directory=ROOT/'tests/fixtures';fixture=json.loads((directory/'mutual_command_traces_original.json').read_text());parent=directory/'conductor_metrics_original.json'
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==fixture['parent_sha256']
    parents=json.loads(parent.read_text())['cases'];counts=collections.Counter();differences=collections.Counter();details=[];jobs=[]
    for c in fixture['cases']:
        p=parents[c['parent_case']];pair=p['inductance'][0]['pairs'][c['parent_pair']];records=rows(p)
        args=[[*records[pair[key]][:6],*records[pair[key]][14:16]]for key in('first','second')]
        assert bytes.fromhex(c['input_bits'])==struct.pack('<16d',*args[0],*args[1]);assert c['output_bits']==pair['value_bits']
        jobs.append((f"INDUCTANCE/{c['parent_case']}/{c['parent_pair']}",c,args))
    coupled=json.loads((directory/'coupling_command_traces_original.json').read_text());parent=directory/'coupling_original.json.gz'
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==coupled['parent_sha256'];parents=json.loads(gzip.decompress(parent.read_bytes()))['cases']
    for c in coupled['cases']:
        pair=parents[c['parent_case']]['calls'][c['parent_call']]['pairs'][c['parent_pair']]
        assert c['input_bits']==pair['input_bits'];assert c['output_bits']==pair['value_bits'];args=doubles(c['input_bits'])
        jobs.append((f"COUPLING/{c['parent_case']}/{c['parent_call']}/{c['parent_pair']}",c,[args[:8],args[8:]]))
    for label,c,expected_inputs in jobs:
        assert c['control_before']==c['control_after']==0x37f
        def compare(category,actual,want,where):
            counts[category]+=1
            if actual!=want:differences[category]+=1;details.append(dict(case=label,kind=category,where=where,actual=actual,original=want))
        compare('complete_pair_F64',f64(segment_mutual(*expected_inputs)),c['output_bits'],'segment_mutual')
        for index,e in enumerate(c['events']):
            kind=e['kind'];assert e['control_before']==e['control_after']==0x37f
            if kind=='canonical':
                a,b=doubles(e['first_bits']),doubles(e['second_bits']);status=canonical(a,b)
                compare('canonical_status',status,e['status'],index)
                compare('canonical_coordinates',struct.pack('<16d',*a,*b).hex(),e['first_output_bits']+e['second_output_bits'],index)
            elif kind in('parallel','planar','spatial'):
                a,b=doubles(e['first_bits']),doubles(e['second_bits'])
                if kind=='parallel':
                    status,value=parallel_segment_mutual(a,b,doubles(e['separation_bits'])[0]);compare('parallel_status',status,e['status'],index)
                else:value=(planar if kind=='planar'else spatial)(a,b)
                compare(kind+'_F64',f64(value),e['output_bits'],index)
            else:
                value={'self':segment_self_inductance,'crosslog':cross_section_log_integral,'separation':effective_separation}[kind](*doubles(e['input_bits']))
                compare(kind+'_R80',raw(value),e['extended_bits'],index)
            for op in e.get('math',[]):compare(op['operation']+'_R80',raw(instruction(op)),op['output_words'],op['address'])
    print('Original complete-command mutual replay:',dict(counts))
    print('Strict differences:',dict(differences))
    for detail in details:print(json.dumps(detail,separators=(',',':')))
    raise SystemExit(bool(differences))


if __name__=='__main__':main()

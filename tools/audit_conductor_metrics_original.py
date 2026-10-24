"""Strict command outputs; --intermediates also gates every captured inner word."""
import collections,json,math,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_conductor_metrics_original import rows
from reasitic import Technology
from reasitic.bridge import _shape
from reasitic.conductor_metrics import _self_and_dc,retained_estimates,qlf
from reasitic.inductance import segment_mutual
from reasitic.command_numbers import frequency_ghz


def main():
    cases=json.loads((ROOT/'tests/fixtures/conductor_metrics_original.json').read_text())['cases'];output=[];inner=collections.Counter();pairs=[];totals=[];baseline=None;old_l=old_q=0
    if '--baseline'in sys.argv:
        source=subprocess.check_output(['git','show','ced6e871c02b7b71e983c32869a8f10c32a1bd1a:src/reasitic/inductance.py'],cwd=ROOT,text=True)
        namespace={'__name__':'reasitic._baseline_conductor','__package__':'reasitic'};exec(compile(source,'baseline_conductor','exec'),namespace);baseline=namespace['inductance_estimate']
    for i,c in enumerate(cases):
        source=rows(c);seen=[];_self_and_dc(source,seen.append)
        for a,b in zip(seen,c['inductance'][0]['self_terms']):
            for key in('length','width','thickness','log_argument','log_return','accumulator'):
                if key in b and struct.pack('<IIH',*a[key].words()).hex()!=b[key]:inner[key]+=1
        for j,p in enumerate(c['inductance'][0]['pairs']):
            a,b=(source[p[key]]for key in('first','second'));actual=segment_mutual([*a[:6],a[14],a[15]],[*b[:6],b[14],b[15]])
            if struct.pack('<d',actual).hex()!=p['value_bits']:pairs.append((i,j,c['label']))
        t=Technology.from_text(c['technology']);shape=_shape(c['public'],t);l,dc=retained_estimates(shape,t)
        if struct.pack('<IIH',*l.words()).hex()!=c['inductance'][0]['extended_bits']:totals.append((i,c['label']))
        if struct.pack('<d',float(l)).hex()!=c['reports'][0]['output_bits']:output.append((i,'L'))
        if struct.pack('<IIH',*dc.words()).hex()!=c['dc'][0]['extended_bits']:output.append((i,'DC'))
        for g,e in zip(c['frequency_ghz'],c['reports'][1:]):
            if struct.pack('<d',qlf(l,dc,frequency_ghz(g))).hex()!=e['output_bits']:output.append((i,'Q',g))
        if baseline is not None:
            old=baseline(shape,t);old_l+=struct.pack('<d',old).hex()!=c['reports'][0]['output_bits']
            for g,e in zip(c['frequency_ghz'],c['reports'][1:]):old_q+=struct.pack('<d',2*math.pi*frequency_ghz(g)*old*1e-9/float(dc)).hex()!=e['output_bits']
    print(f'{len(cases)} complete original histories / 56 L and 392 QLF stores: {len(output)} public output differences. Intermediate differences: {dict(inner)}; {len(pairs)} pair binary64 stores; {len(totals)} retained complete L returns.')
    if pairs:print('Pair differences:',pairs)
    if totals:print('Retained total differences:',totals)
    if output:print('Output differences:',output)
    if baseline is not None:print(f'Prior ced6e87 runtime: {old_l} / 56 L and {old_q} / 392 QLF stores differ.')
    raise SystemExit(bool(output or('--intermediates'in sys.argv and(inner or pairs or totals))))


if __name__=='__main__':main()

"""Run the x87 instruction chain from its first input; all later bytes are targets."""
import argparse,gzip,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.x87_format_state import X87FormatState


def run(probe):
    initial=probe['steps'][0]['after'];state=X87FormatState(bytes.fromhex(probe['states'][initial['state']]),pointer_mode='masked-error-pointers');flags,eax,stored=(initial[k]for k in('eflags','eax','stored'));differences=[];checked=0;bytes_checked=0;registers=0
    kernel={point['step']:point for point in probe['kernel_observations']};initial_kernel=bytes.fromhex(kernel[0]['xstate']);kernel_state=X87FormatState(initial_kernel,pointer_mode='masked-error-pointers');kernel_bytes=0;kflags,keax,kstored=flags,eax,stored
    for i,step in enumerate(probe['steps'][1:],1):
        def execute(cpu,flags,eax,stored):
            kind=step['kind']
            if kind=='fldcw':cpu.fldcw(step['control'])
            elif kind=='fld64':cpu.fld64(step['word'])
            elif kind=='fld_st':cpu.fld_st(step['index'])
            elif kind=='fst64':stored=cpu.fst64()
            elif kind=='fstp64':stored=cpu.fst64(pop=True)
            elif kind=='fxch':cpu.fxch(step['index'])
            elif kind in('fucomi','fucomip'):flags=cpu.fucomi(step['index'],flags,pop=kind=='fucomip')
            elif kind=='fnstsw_ax':eax=cpu.fnstsw_ax(eax)
            elif kind in('fabs','fxam','fstp_st0'):getattr(cpu,kind)()
            else:raise ValueError('Unknown native instruction '+kind)
            return flags,eax,stored
        try:
            flags,eax,stored=execute(state,flags,eax,stored)
            kflags,keax,kstored=execute(kernel_state,kflags,keax,kstored)
        except (ValueError,NotImplementedError)as error:
            differences.append(dict(step=i,kind='runtime',reason=str(error)));break # No later target can restart this chain.
        checked+=1;actual=state.serialize();target=step['after'];expected=bytes.fromhex(probe['states'][target['state']]);bytes_checked+=len(expected)
        if actual!=expected:differences.extend(dict(step=i,kind='fp-byte',offset=p,actual=a,original=b)for p,(a,b)in enumerate(zip(actual,expected))if a!=b)
        for key,value in(('eflags',flags),('eax',eax),('stored',stored)):
            registers+=1
            if value!=target[key]:differences.append(dict(step=i,kind=key,actual=value,original=target[key]))
        if i in kernel:
            actual_kernel=kernel_state.serialize();expected_kernel=bytes.fromhex(kernel[i]['xstate']);kernel_bytes+=len(expected_kernel)
            if actual_kernel!=expected_kernel:differences.extend(dict(step=i,kind='kernel-fp-byte',offset=p,actual=a,original=b)for p,(a,b)in enumerate(zip(actual_kernel,expected_kernel))if a!=b)
    return dict(instructions_required=len(probe['steps'])-1,instructions_checked=checked,fp_bytes_checked=bytes_checked,registers_and_stores_checked=registers,kernel_fp_bytes_checked=kernel_bytes,differences=differences)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probe',type=Path,default=ROOT/'tests/fixtures/x87_formatter_instructions_native.json.gz');p.add_argument('--output',type=Path);args=p.parse_args()
    report=run(json.loads(gzip.decompress(args.probe.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='differences'},'differences',len(report['differences']));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

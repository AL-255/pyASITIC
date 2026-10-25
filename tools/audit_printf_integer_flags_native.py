"""Independent native instruction requests through the formatter's Python semantics."""
import argparse,gzip,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.printf_fp_flow import PrintfFPFlow,operand


class FormatterInputs:
    def __init__(self):
        self.m=Memory(AddressSpace([dict(start=0x1000,end=0x3000)]));self.m.zero(0x1000,0x2000);self.m.put_u32(0x2000,0x12345678);self.libc=0;self.tls=0
        self._write=None;self.padding=SimpleNamespace(pad=None);self.writer=SimpleNamespace(bytes=SimpleNamespace(memcpy=None,shr1_af=16));self.lengths=SimpleNamespace(length=None,bounded=None);self.file=SimpleNamespace(flush_to_file=None,switch=None)


def run(probe):
    inputs=FormatterInputs();flow=PrintfFPFlow(inputs,None);differences=[];checked=0
    for i,case in enumerate(probe['cases']):
        op=case['op'];args='ecx'if op in('mul','div','idiv')else'eax,ecx'if op=='imul'else'ebx,eax'if op in('bsr','tzcnt')else'eax,ebx,cl'if op in('shld','shrd')else'eax,cl'
        flow.code={0x1000:(1,op,tuple(operand(x)for x in args.split(','))),0x1001:(1,'ret',())}
        r=dict.fromkeys(('eax','ebx','ecx','edx','esi','edi','ebp'),0);r.update({k:case[k]for k in('eax','ebx','ecx','edx','eflags')});r.update(esp=0x2000,eip=0x1000)
        actual=flow.execute(r);checked+=1
        for name,value in case['original'].items():
            if actual[name]!=value:differences.append(dict(case=i,op=op,name=name,actual=actual[name],original=value))
    return dict(cases_required=len(probe['cases']),cases_checked=checked,registers_checked=checked*5,differences=differences)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probe',type=Path,default=ROOT/'tests/fixtures/printf_integer_flags_native.json.gz');p.add_argument('--output',type=Path);args=p.parse_args();report=run(json.loads(gzip.decompress(args.probe.read_bytes())))
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items()if k!='differences'},'differences',len(report['differences']));raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

"""Int32 text probes through the source formatter; full ASITIC gates stay separate."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from printf_archive import read_fixture
from printf_fixture import expand_state,data
from reasitic.heap import AddressSpace
from reasitic.memory import Memory
from reasitic.printf_file import PrintfFile
from reasitic.printf_format import PrintfFormat


class Inputs:
    """One earlier ELF image plus independently declared memory-buffer inputs.

    No native probe result, formatter return snapshot or call-specific later
    state initializes this source execution. All probe requests use these same
    earlier section bytes and the same synthetic stack/TLS/buffer contract.
    """
    def __init__(self,fixture):
        before=expand_state(fixture,fixture['cases'][0]['printf_calls'][0]['before']);self.registers=before['registers'];self.cpu=fixture['integer_cpu'];elf=next(e for e in before['format_inputs']['elf_data']if e['path'].endswith('/libc.so.6'));self.libc=elf['base'];self.libc_sha256=elf['elf_sha256'];self.sections=[]
        for s in elf['sections']:
            region=next(r for r in before['regions']if r['address']==s['address']and r['size']==s['size']);self.sections.append((s['address'],data(fixture,region)))

    def format(self,request):
        m=Memory(AddressSpace([dict(start=self.libc,end=self.libc+0x250000),dict(start=0x300000,end=0x302000),dict(start=0x500000,end=0x508000)]))
        for address,raw in self.sections:m.write(address,raw)
        m.zero(0x300000,0x2000);m.write(0x500000,b'\xa5'*0x8000);tls=0x300800;m.put_u32(tls,tls);m.put_u32(tls+20,0xc0ffee00)
        s=0x504000;args=s+128;fmt=s+256;buf=s+512;output=s+2048
        m.write(fmt,request['format'].encode('ascii')+b'\0');m.put_u32(args,request['value'])
        for offset,v in ((0,0x12345678),(4,buf),(8,fmt),(12,args),(16,0)):m.put_u32(s+offset,v)
        for offset,v in ((0,output),(4,output),(8,output+128),(12,0),(16,0),(20,2)):m.put_u32(buf+offset,v)
        file=PrintfFile(m,libc_base=self.libc,tls_base=tls,heap=None,io=None);storage=PrintfFormat(file,shr1_af=self.cpu['shr1_af']);r=dict(self.registers,esp=s,eip=self.libc+0x60530)
        result=storage.format(r)
        if result['esp']!=s+4 or result['eip']!=0x12345678:raise ValueError('Int32 source formatter return ABI mismatch')
        for name in ('ebp','edi','esi','ebx'):
            if result[name]!=r[name]:raise ValueError('Int32 source formatter changed callee-saved '+name)
        return m.read(output,m.u32(buf+4)-output)


def run(fixture,probe):
    inputs=Inputs(fixture);differences=[];checked=0
    if inputs.libc_sha256!=probe['libc_sha256']:raise ValueError('Independent int32 probe and earlier ELF input use different libc builds')
    for i,case in enumerate(probe['cases']):
        try:actual=inputs.format(case)
        except (ValueError,NotImplementedError)as error:differences.append(dict(case=i,request={k:case[k]for k in ('format','value')},kind='runtime',reason=str(error)));continue
        checked+=1
        if actual.hex()!=case['original']:differences.append(dict(case=i,request={k:case[k]for k in ('format','value')},kind='text',actual=actual.hex(),original=case['original']))
    return dict(cases_required=len(probe['cases']),cases_checked=checked,differences=differences)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/printf_format_original.manifest.json');p.add_argument('--probe',type=Path,default=ROOT/'tests/fixtures/printf_integer_original.json.gz');p.add_argument('--output',type=Path);args=p.parse_args()
    f=read_fixture(args.fixture);probe=json.loads(gzip.decompress(args.probe.read_bytes()));report=run(f,probe)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['cases_checked'],'/',report['cases_required'],'int32 cases,',len(report['differences']),'differences');raise SystemExit(int(bool(report['differences'])))


if __name__=='__main__':main()

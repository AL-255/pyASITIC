"""Independent integer instruction flags used by the pinned decimal ABI flow."""
import argparse,gzip,hashlib,json,os,random,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def requests():
    values=(0,1,2,3,7,15,16,31,127,128,255,256,0x7fffffff,0x80000000,0x80000001,0xffffffff)
    flags=(0x202,0xad7,0x212,0xa03);cases=[]
    def add(op,a,b=0,high=0,other=0x12345678):
        cases.extend(dict(op=op,eax=a,ecx=b,edx=high,ebx=other,eflags=f)for f in flags)
    for op in('mul','imul'):
        for a in values:
            for b in values:add(op,a,b)
    for op in('div','idiv'):
        for a in values:
            for b in(1,2,3,7,31,0x7fffffff):add(op,a,b,0 if op=='div'or a<1<<31 else 0xffffffff)
    for op in('bsr','tzcnt'):
        for a in sorted(set(values)|{1<<i for i in range(32)}):add(op,a)
    for op in('shl','shr','sar','shld','shrd'):
        for a in values:
            for count in(0,1,2,3,7,15,16,30,31,32,33,63,255):add(op,a,count)
    rng=random.Random(0x49333836)
    for i in range(256):
        for op in('mul','imul','bsr','tzcnt','shl','shr','sar','shld','shrd'):add(op,rng.getrandbits(32),rng.randrange(256)if'sh'in op or op=='sar'else rng.getrandbits(32),other=rng.getrandbits(32))
    return cases


def assembly(cases):
    lines=['.text','.globl _start','_start:']
    for i,c in enumerate(cases):
        lines.extend([f'pushl ${c["eflags"]}','popfl',*[f'movl ${c[r]},%{r}'for r in('eax','ebx','ecx','edx')]])
        op=c['op'];instruction={'mul':'mul %ecx','imul':'imul %ecx,%eax','div':'div %ecx','idiv':'idiv %ecx','bsr':'bsr %eax,%ebx','tzcnt':'tzcnt %eax,%ebx','shl':'shl %cl,%eax','shr':'shr %cl,%eax','sar':'sar %cl,%eax','shld':'shld %cl,%ebx,%eax','shrd':'shrd %cl,%ebx,%eax'}[op]
        lines.extend([instruction,'pushfl',f'popl output+{20*i}',*[f'movl %{r},output+{20*i+4+4*j}'for j,r in enumerate(('eax','ebx','ecx','edx'))]])
    lines.extend(['movl $4,%eax','movl $1,%ebx','movl $output,%ecx',f'movl ${20*len(cases)},%edx','int $0x80','movl $1,%eax','xorl %ebx,%ebx','int $0x80','.bss','.balign 16',f'output: .skip {20*len(cases)}'])
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/printf_integer_flags_native.json.gz');args=p.parse_args()
    cases=requests();source=assembly(cases);env=dict(PATH=os.defpath,HOME='/tmp',LANG='C',LC_ALL='C')
    with tempfile.TemporaryDirectory(prefix='pyasitic-printf-flags-')as directory:
        d=Path(directory);(d/'probe.s').write_text(source);commands=[['as','--32','-o',str(d/'probe.o'),str(d/'probe.s')],['ld','-m','elf_i386','-o',str(d/'probe'),str(d/'probe.o')]]
        for cmd in commands:subprocess.run(cmd,capture_output=True,check=True)
        result=subprocess.run([str(d/'probe')],env=env,capture_output=True,check=True,start_new_session=True,timeout=60);assert len(result.stdout)==20*len(cases)and not result.stderr
        for i,c in enumerate(cases):c['original']=dict(zip(('eflags','eax','ebx','ecx','edx'),struct.unpack_from('<5I',result.stdout,20*i)))
        cpu={k.strip():v.strip()for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines()if ':'in line for k,v in[line.split(':',1)]if k.strip()in('vendor_id','cpu family','model','stepping','model name','microcode')}
        record=dict(reference='Standalone static i386 program. All operands and incoming flags are declared before native execution. Every result register and full PUSHFL word is retained, including architecturally undefined condition bits. No ASITIC instruction, input, CPU control, affinity or result is changed. These CPU instruction targets supplement all full original formatter-state targets.',source=source,source_sha256=hashlib.sha256(source.encode()).hexdigest(),commands=commands,probe_sha256=hashlib.sha256((d/'probe').read_bytes()).hexdigest(),environment=env,cpu=cpu,cases=cases)
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(cases),'independent native integer/flags requests')


if __name__=='__main__':main()

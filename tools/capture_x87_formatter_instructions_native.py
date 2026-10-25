"""Independent i386 x87 load/store/classification states, never ASITIC patches."""
import argparse,gzip,hashlib,json,os,random,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def requests():
    values={0,1,(1<<52)-1,1<<52,(1<<52)+1,0x3fefffffffffffff,0x3ff0000000000000,0x3ff0000000000001,
            0x4004000000000000,0x7fefffffffffffff,0x7ff0000000000000,0x7ff0000000000001,0x7ff8000000000000,0x7fffffffffffffff}
    values=sorted(values|{v|(1<<63)for v in values})
    cases=[dict(word=v,rounding=r)for r in range(4)for v in values]
    for exponent in range(2048):
        cases.append(dict(word=((exponent&1)<<63)|(exponent<<52)|(0,1,(1<<52)-1)[exponent%3],rounding=exponent%4))
    rng=random.Random(0x583837)
    cases.extend(dict(word=rng.getrandbits(64),rounding=i%4)for i in range(256))
    return cases


def operations(case):
    # This is an independent instruction sequence, including both the outer
    # argument copy and the decimal core's normal classification sequence.
    # It deliberately executes every operation even for infinity/NaN; no
    # original branch or terminal target is replaced by this probe.
    return [dict(kind='fldcw',control=0x37f|(case['rounding']<<10)),dict(kind='fxam'),
            dict(kind='fld64',word=case['word']),dict(kind='fst64'),dict(kind='fstp64'),
            dict(kind='fld64',word=case['word']),dict(kind='fucomi',index=0),dict(kind='fld_st',index=0),
            dict(kind='fabs'),dict(kind='fld64',word=0x7fefffffffffffff),dict(kind='fst64'),
            dict(kind='fxch',index=1),dict(kind='fucomip',index=1),dict(kind='fstp_st0'),dict(kind='fxam'),
            dict(kind='fnstsw_ax'),dict(kind='fstp64')]


def assembly(cases):
    lines=['.text','.globl _start','_start:','movl $0xd,%eax','xorl %ecx,%ecx','cpuid','movl %eax,profile','movl %edx,profile+4','xorl %ecx,%ecx','xgetbv','movl %eax,profile+8','movl %edx,profile+12','movl $0xfeedbeef,%eax','pushl $0xad7','popfl']
    data=['.section .data','.balign 16','profile: .quad 0,0','stored: .quad 0x0123456789abcdef'];steps=[]
    def snapshot():
        n=len(steps);p=f'frames+{n*528}';lines.extend([f'.globl checkpoint_{n}',f'checkpoint_{n}:',f'fxsave {p}',f'pushfl',f'popl {p}+512',f'movl %eax,{p}+516','movl stored,%edx',f'movl %edx,{p}+520','movl stored+4,%edx',f'movl %edx,{p}+524'])
    snapshot();steps.append(dict(kind='bootstrap'))
    for ci,case in enumerate(cases):
        for op in operations(case):
            kind=op['kind'];label=f'operand_{len(steps)}'
            if kind=='fldcw':data.append(f'{label}: .word {op["control"]}');instruction=f'fldcw {label}'
            elif kind=='fld64':data.append(f'{label}: .quad 0x{op["word"]:016x}');instruction=f'fldl {label}'
            elif kind=='fst64':instruction='fstl stored'
            elif kind=='fstp64':instruction='fstpl stored'
            elif kind=='fld_st':instruction=f'fld %st({op["index"]})'
            elif kind=='fstp_st0':instruction='fstp %st(0)'
            elif kind=='fnstsw_ax':instruction='fnstsw %ax'
            elif kind in('fxch','fucomi','fucomip'):instruction=f'{kind} %st({op["index"]}),%st'if kind!='fxch'else f'fxch %st({op["index"]})'
            else:instruction=kind
            lines.append(instruction);snapshot();steps.append(dict(case=ci,**op))
    lines.extend(['movl $4,%eax','movl $1,%ebx','movl $profile,%ecx','movl $16,%edx','int $0x80','movl $4,%eax','movl $1,%ebx','movl $frames,%ecx',f'movl ${len(steps)*528},%edx','int $0x80','movl $1,%eax','xorl %ebx,%ebx','int $0x80'])
    data.extend(['.section .bss','.balign 16',f'frames: .skip {len(steps)*528}'])
    return '\n'.join(lines+data)+'\n',steps


OBSERVER=r'''
import ctypes,gdb,json
libc=ctypes.CDLL(None,use_errno=True)
class Iovec(ctypes.Structure):_fields_=[('base',ctypes.c_void_p),('size',ctypes.c_size_t)]
def xstate():
 data=ctypes.create_string_buffer(65536);vec=Iovec(ctypes.addressof(data),len(data))
 if libc.ptrace(0x4204,gdb.selected_inferior().pid,0x202,ctypes.byref(vec)):raise OSError(ctypes.get_errno())
 return data.raw[:vec.size].hex()
states=[]
class Point(gdb.Breakpoint):
 def __init__(self,index):self.index=index;super().__init__('checkpoint_'+str(index),internal=True)
 def stop(self):states.append(dict(step=self.index,xstate=xstate()));return False
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'tests/fixtures/x87_formatter_instructions_native.json.gz');args=p.parse_args()
    cases=requests();source,steps=assembly(cases);env=dict(PATH=os.defpath,HOME='/tmp',LANG='C',LC_ALL='C',TERM='dumb',INPUTRC='/dev/null')
    with tempfile.TemporaryDirectory(prefix='pyasitic-x87-formatter-')as directory:
        d=Path(directory);(d/'probe.s').write_text(source)
        commands=[['as','--32','-o',str(d/'probe.o'),str(d/'probe.s')],['ld','-m','elf_i386','-o',str(d/'probe'),str(d/'probe.o')]]
        for command in commands:subprocess.run(command,capture_output=True,check=True)
        result=subprocess.run([str(d/'probe')],env=env,capture_output=True,check=True,start_new_session=True,timeout=60)
        assert len(result.stdout)==16+528*len(steps)and not result.stderr
        supported,xcr0=struct.unpack_from('<QQ',result.stdout);raw=result.stdout[16:];features=supported&xcr0
        points=sorted({0,3,7,13}|{(i+1)*17 for i in range(len(cases))});observer=OBSERVER+'\nfor index in '+repr(points)+':Point(index)\n'
        script='set pagination off\nset confirm off\nset debuginfod enabled off\npython\n'+observer+'\nend\nrun > observed.bin\npython\nopen("observed.json","w").write(json.dumps(states))\nend\nquit\n'
        (d/'observe.gdb').write_text(script)
        observed=subprocess.run(['gdb','-q','-nx','-batch','-x',str(d/'observe.gdb'),str(d/'probe')],env=env,cwd=d,capture_output=True,check=True,start_new_session=True,timeout=60)
        kernel=json.loads((d/'observed.json').read_text());assert[p['step']for p in kernel]==points
        assert(d/'observed.bin').read_bytes()==result.stdout
        differences=[]
        for point in kernel:
            saved=bytearray(raw[528*point['step']:528*point['step']+512]);observed_state=bytes.fromhex(point['xstate'])
            # Linux NT_X86_XSTATE stores the enabled user-feature mask in
            # FXSAVE's software-owned bytes 464..471. Supply the actual
            # earlier CPUID/XGETBV result, keeping all raw hardware targets.
            struct.pack_into('<Q',saved,464,features)
            differences.extend(dict(step=point['step'],offset=i,fxsave=a,regset=b)for i,(a,b)in enumerate(zip(saved,observed_state[:512]))if a!=b)
        if differences:
            diagnostic=Path('/tmp/pyasitic-x87-kernel-comparison.json');diagnostic.write_text(json.dumps(dict(kernel_observations=kernel,differences=differences,fxsave=[raw[528*p['step']:528*p['step']+512].hex()for p in kernel]),indent=2)+'\n')
            raise ValueError(str(len(differences))+' FXSAVE/register-view differences; full evidence: '+str(diagnostic))
        snapshots=[];lookup={}
        for i,step in enumerate(steps):
            data=raw[528*i:528*(i+1)];image=data[:512].hex()
            if image not in lookup:lookup[image]=len(snapshots);snapshots.append(image)
            flags,eax,stored=struct.unpack_from('<IIQ',data,512);step['after']=dict(state=lookup[image],eflags=flags,eax=eax,stored=stored)
        cpu={}
        for line in Path('/proc/cpuinfo').read_text().split('\n\n',1)[0].splitlines():
            if ':'in line:
                k,v=map(str.strip,line.split(':',1))
                if k in('vendor_id','model name','cpu family','model','stepping','microcode','flags'):cpu[k]=v
        record=dict(reference='Standalone static i386 native instruction sequence with ordinary Linux ELF bootstrap. Every requested instruction and all resulting FXSAVE bytes, PUSHFL flags, EAX and binary64 destination bytes are retained. No ASITIC process, instruction, memory, CPU control, allocation, signal or returned result is modified. FLDCW is an explicit earlier instruction request within this independent program. Read-only PTRACE GETREGSET observations at bootstrap, three inner points, and the end of every independent request exactly match all 512 corresponding bytes after supplying the Linux software-owned feature word from the independently executed earlier CPUID/XGETBV profile; every raw hardware and kernel target is retained. The complete native output streams of both executions match. These are independent component targets, not continuing replay inputs or a replacement/filter for any original formatter target.',cases=cases,source=source,source_sha256=hashlib.sha256(source.encode()).hexdigest(),commands=commands,probe_sha256=hashlib.sha256((d/'probe').read_bytes()).hexdigest(),environment=env,cpu=cpu,supported_features=supported,xcr0=xcr0,features=features,kernel_release=os.uname().release,gdb_observer=observer,gdb_stdout=observed.stdout.decode(),gdb_stderr=observed.stderr.decode(),kernel_observations=kernel,states=snapshots,steps=steps)
    with gzip.GzipFile(str(args.output),'wb',mtime=0)as stream:stream.write((json.dumps(record,separators=(',',':'))+'\n').encode())
    print(len(cases),'independent requests,',len(steps)-1,'instructions,',len(snapshots),'distinct FXSAVE targets,',len(kernel),'exact Linux XSAVE observations')


if __name__=='__main__':main()

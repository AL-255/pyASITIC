"""Python execution of the pinned decimal formatter's fixed source flow.

The adjacent program is generated offline from original glibc instructions,
LGPL-2.1-or-later, Copyright Free Software Foundation, Inc. See the bundled
license. It contains algorithm instructions, never expected output or state.
Guest data still comes exclusively from earlier owned memory. Unsupported
instructions/callees fail explicitly; no native code is executed at runtime.
"""
from functools import lru_cache
import json,re,struct,weakref
from pathlib import Path

MASK=0xffffffff
NAMES={0x5a990:'fp-l-buffer',0x58920:'fp-buffer',0x58750:'write',0x58390:'pad',0x58440:'putc',0x584b0:'puts',0x58230:'flush',0xbbae0:'memcpy',0xbc470:'strlen-ia32',0xbb390:'strnlen-ia32',0x585a0:'flush-to-file',0x58570:'switch'}
REGS={name:(name,0,32)for name in('eax','ebx','ecx','edx','esi','edi','ebp','esp')}
for full,short,low,high in(('eax','ax','al','ah'),('ebx','bx','bl','bh'),('ecx','cx','cl','ch'),('edx','dx','dl','dh')):
    REGS[short]=(full,0,16);REGS[low]=(full,0,8);REGS[high]=(full,8,8)
for full,short in(('esi','si'),('edi','di'),('ebp','bp'),('esp','sp')):REGS[short]=(full,0,16)


def signed(value,bits):return value-(1<<bits)if value&(1<<(bits-1))else value
def result_flags(value,bits,flags):
    value&=(1<<bits)-1
    return(flags&~0x8d5)|(0x40 if not value else 0)|(0x80 if value>>(bits-1)else 0)|(4 if not(value&255).bit_count()&1 else 0)
def arithmetic(a,b,carry,bits,flags,subtract=False):
    mask=(1<<bits)-1;a&=mask;b&=mask;wide=a-b-carry if subtract else a+b+carry;value=wide&mask
    flags=result_flags(value,bits,flags)|(16 if(a^b^value)&16 else 0)
    flags|=int(wide<0 if subtract else wide>mask)
    overflow=((a^b)&(a^value))if subtract else(~(a^b)&(a^value))
    return value,flags|(0x800 if overflow&(1<<(bits-1))else 0)


def operand(text,branch=False):
    text=text.strip()
    if text in REGS:return('r',*REGS[text])
    if text in('st','st(0)'):return('f',0)
    if re.fullmatch(r'st\([0-7]\)',text):return('f',int(text[3]))
    width=32
    for prefix,bits in(('BYTE PTR ',8),('WORD PTR ',16),('DWORD PTR ',32),('QWORD PTR ',64),('TBYTE PTR ',80)):
        if text.startswith(prefix):width=bits;text=text[len(prefix):];break
    segment=0
    for prefix in('gs:','ds:','es:','cs:'):
        if text.startswith(prefix):segment=int(prefix=='gs:');text=text[len(prefix):];break
    if text.startswith('[')and text.endswith(']')or segment:
        expression=text[1:-1]if text.startswith('[')else text;terms=[];constant=0
        for token in re.findall(r'[+-]?[^+-]+',expression):
            sign=-1 if token.startswith('-')else 1;token=token.lstrip('+-')
            if token.startswith('0x')or token.isdigit():constant+=sign*int(token,0)
            else:
                values=token.split('*');register=values[0];scale=int(values[1],0)if len(values)>1 else 1
                if register!='eiz':
                    if register not in REGS:raise ValueError('Unknown source address register '+register)
                    terms.append((register,scale*sign))
        return('m',width,segment,constant,tuple(terms))
    return('i',int(text,16 if branch else 0))


@lru_cache(maxsize=1)
def program():
    source=json.loads(Path(__file__).with_name('printf_fp_program.json').read_text());code={}
    for address,length,op,args,_raw in source['instructions']:
        if op=='notrack':op,args=args.split(None,1)
        if op=='rep':op='rep_'+args.split(None,1)[0];args=args.split(None,1)[1]
        branch=op=='call'or op.startswith('j')
        operands=tuple(operand(x,branch)for x in args.split(','))if args else()
        code[address]=(length,op,operands)
    return code


class PrintfFPFlow:
    def __init__(self,formatter,fp):self.f=weakref.proxy(formatter);self.m=formatter.m;self.libc=formatter.libc;self.tls=formatter.tls;self.fp=fp;self.code=program();self.instructions=0

    def address(self,o,r):return(o[3]+sum(r[k]*scale for k,scale in o[4])+(self.tls if o[2]else 0))&MASK
    def read(self,o,r):
        if o[0]=='i':return o[1]
        if o[0]=='r':return(r[o[1]]>>o[2])&((1<<o[3])-1)
        if o[0]=='m':return int.from_bytes(self.m.read(self.address(o,r),o[1]//8),'little')
        raise NotImplementedError('Unsupported source operand read '+str(o))
    def width(self,o):return o[3]if o[0]=='r'else o[1]if o[0]=='m'else 32
    def write(self,o,value,r):
        bits=self.width(o);value&=(1<<bits)-1
        if o[0]=='r':mask=((1<<bits)-1)<<o[2];r[o[1]]=(r[o[1]]&~mask)|(value<<o[2])
        elif o[0]=='m':self.m.write(self.address(o,r),value.to_bytes(bits//8,'little'))
        else:raise ValueError('Non-writable source operand')
    def condition(self,name,flags):
        cf=bool(flags&1);pf=bool(flags&4);zf=bool(flags&64);sf=bool(flags&128);of=bool(flags&2048)
        return{'e':zf,'z':zf,'ne':not zf,'nz':not zf,'b':cf,'c':cf,'ae':not cf,'nb':not cf,'be':cf or zf,'a':not(cf or zf),'s':sf,'ns':not sf,'p':pf,'np':not pf,'l':sf!=of,'le':zf or sf!=of,'g':not zf and sf==of,'ge':sf==of,'o':of,'no':not of}[name]
    def push(self,value,r):r['esp']=(r['esp']-4)&MASK;self.m.put_u32(r['esp'],value)
    def pop(self,r):value=self.m.u32(r['esp']);r['esp']=(r['esp']+4)&MASK;return value

    def execute(self,registers,*,stop=None):
        r=dict(registers);offset=r['eip']-self.libc
        if stop is None and offset in NAMES:return self.f.file._child(NAMES[offset],r,self._body)
        return self._body(r,stop=stop)

    def _body(self,registers,*,stop=None):
        r=dict(registers);m=self.m;fp=self.fp
        hooks={0x58750:self.f._write,0x58390:self.f.padding.pad,0xbbae0:self.f.writer.bytes.memcpy,0xbc470:self.f.lengths.length,0xbb390:self.f.lengths.bounded,0x585a0:self.f.file.flush_to_file,0x58570:self.f.file.switch}
        if r['eip']-self.libc in hooks:return hooks[r['eip']-self.libc](r)
        while stop is None or r['eip']!=self.libc+stop:
            pc=r['eip']-self.libc
            if pc not in self.code:raise NotImplementedError(f'Original decimal source callee/instruction {pc:#x} is not implemented')
            length,op,args=self.code[pc];nextpc=r['eip']+length;self.instructions+=1
            try:
                if op in('endbr32','nop'):pass
                elif op=='mov':self.write(args[0],self.read(args[1],r),r)
                elif op in('movzx','movsx'):
                    v=self.read(args[1],r);self.write(args[0],signed(v,self.width(args[1]))if op=='movsx'else v,r)
                elif op=='lea':self.write(args[0],self.address(args[1],r),r)
                elif op=='push':self.push(self.read(args[0],r),r)
                elif op=='pop':v=self.pop(r);self.write(args[0],v,r)
                elif op=='xchg':a,b=(self.read(o,r)for o in args);self.write(args[0],b,r);self.write(args[1],a,r)
                elif op in('add','sub','cmp','adc','sbb','inc','dec','neg'):
                    bits=self.width(args[0]);a=self.read(args[0],r);b=self.read(args[1],r)if len(args)>1 else 1;old=r['eflags'];carry=old&1 if op in('adc','sbb')else 0
                    if op=='neg':a,b=0,a
                    value,flags=arithmetic(a,b,carry,bits,old,op in('sub','cmp','sbb','dec','neg'))
                    if op in('inc','dec'):flags=(flags&~1)|(old&1)
                    r['eflags']=flags
                    if op!='cmp':self.write(args[0],value,r)
                elif op in('xor','and','or','test'):
                    a,b=(self.read(o,r)for o in args);value=a^b if op=='xor'else a|b if op=='or'else a&b;r['eflags']=result_flags(value,self.width(args[0]),r['eflags'])
                    if op!='test':self.write(args[0],value,r)
                elif op in('shl','shr','sar','shld','shrd'):
                    a=self.read(args[0],r);bits=self.width(args[0]);count=self.read(args[-1],r)&31
                    if count:
                        mask=(1<<bits)-1;other=self.read(args[1],r)if len(args)==3 else 0
                        if op in('shl','shld'):value=((a<<count)|(other>>(bits-count)if op=='shld'else 0))&mask;carry=(a>>(bits-count))&1;overflow=((value>>(bits-1))^carry)&1
                        elif op in('shr','shrd'):value=(a>>count)|((other<<(bits-count))&mask if op=='shrd'else 0);carry=(a>>(count-1))&1;overflow=((a^value)>>(bits-1))&1
                        else:value=signed(a,bits)>>count;carry=(a>>(count-1))&1;overflow=0
                        old=r['eflags'];af=old&16 if self.f.writer.bytes.shr1_af=='preserve'else self.f.writer.bytes.shr1_af
                        if op in('shr','shrd'):overflow=((value>>(bits-1))^(value>>(bits-2)))&1
                        r['eflags']=result_flags(value,bits,old)|carry|(overflow<<11)|af;self.write(args[0],value,r)
                elif op in('mul','imul'):
                    bits=self.width(args[0])
                    if op=='mul':wide=r['eax']*self.read(args[0],r);r['eax']=wide&MASK;r['edx']=(wide>>32)&MASK;overflow=bool(r['edx']);value=r['eax']
                    else:
                        a,b=(self.read(o,r)for o in(args[1:]if len(args)==3 else args));wide=signed(a,bits)*signed(b,bits);value=wide&((1<<bits)-1);self.write(args[0],value,r);overflow=wide!=signed(value,bits)
                    # Independently measured AMD reference behavior: MUL's
                    # undefined arithmetic flags retain their earlier bits.
                    r['eflags']=(r['eflags']&~0x801)|(0x801 if overflow else 0)
                elif op in('div','idiv'):
                    denominator=self.read(args[0],r);numerator=(r['edx']<<32)|r['eax']
                    if not denominator:raise NotImplementedError('Integer divide fault requires its original delivery source')
                    if op=='idiv':denominator=signed(denominator,32);numerator=signed(numerator,64);q=abs(numerator)//abs(denominator);q=-q if(numerator<0)!=(denominator<0)else q;rem=numerator-q*denominator
                    else:q,rem=divmod(numerator,denominator)
                    if not(-(1<<31)<=q<1<<31 if op=='idiv'else 0<=q<1<<32):raise NotImplementedError('Integer divide overflow requires its original delivery source')
                    r['eax']=q&MASK;r['edx']=rem&MASK
                    r['eflags']=(r['eflags']&~0xd4)|16
                elif op=='cdq':r['edx']=MASK if r['eax']&0x80000000 else 0
                elif op in('bsr','tzcnt'):
                    value=self.read(args[1],r);bits=self.width(args[1])
                    if op=='bsr':
                        if value:self.write(args[0],value.bit_length()-1,r)
                        r['eflags']=(result_flags(value.bit_length()-1 if value else 0,bits,r['eflags'])&~64)|(0 if value else 64)
                    else:
                        result=(value&-value).bit_length()-1 if value else bits;self.write(args[0],result,r);r['eflags']=(r['eflags']&~0xd5)|int(not value)|(64 if not result else 0)
                elif op.startswith('set'):self.write(args[0],int(self.condition(op[3:],r['eflags'])),r)
                elif op.startswith('cmov'):
                    value=self.read(args[1],r)
                    if self.condition(op[4:],r['eflags']):self.write(args[0],value,r)
                elif op=='call':
                    destination=self.read(args[0],r)+(self.libc if args[0][0]=='i'else 0);self.push(nextpc,r);r['eip']=destination;r=self.execute(r);nextpc=r['eip']
                elif op.startswith('j'):
                    take=op=='jmp'or(not r['ecx']if op=='jecxz'else self.condition(op[1:],r['eflags']))
                    if take:
                        nextpc=self.read(args[0],r)+(self.libc if args[0][0]=='i'else 0)
                        if nextpc-self.libc in NAMES:return self.execute(dict(r,eip=nextpc))
                elif op=='ret':r['eip']=self.pop(r);return r
                elif op=='cld':r['eflags']&=~0x400
                elif op in('stos','rep_stos'):
                    count=r['ecx']if op=='rep_stos'else 1;size=self.width(args[0])//8;delta=-size if r['eflags']&0x400 else size
                    for _ in range(count):self.write(args[0],self.read(args[1],r),r);r['edi']=(r['edi']+delta)&MASK
                    if op=='rep_stos':r['ecx']=0
                elif op=='fld':
                    if args[0][0]=='f':fp.fld_st(args[0][1])
                    elif self.width(args[0])==64:fp.fld64(self.read(args[0],r))
                    else:raise NotImplementedError('Extended x87 load requires its source state')
                elif op in('fst','fstp'):
                    if args[0][0]=='f'and args[0][1]==0 and op=='fstp':fp.fstp_st0()
                    elif self.width(args[0])==64:self.write(args[0],fp.fst64(pop=op=='fstp'),r)
                    else:raise NotImplementedError('Extended x87 store requires its source state')
                elif op in('fabs','fxam'):getattr(fp,op)()
                elif op=='fxch':fp.fxch(args[0][1])
                elif op in('fucomi','fucomip'):r['eflags']=fp.fucomi(args[-1][1],r['eflags'],pop=op=='fucomip')
                elif op=='fnstsw':r['eax']=fp.fnstsw_ax(r['eax'])
                elif op=='fnstcw':self.write(args[0],fp.control,r)
                else:raise NotImplementedError('Original source opcode '+op+' is not implemented')
            except (ValueError,NotImplementedError)as error:
                if type(error)in(ValueError,NotImplementedError):raise type(error)(f'{pc:#x} {op}: {error}')from error
                error.add_note(f'Original decimal instruction {pc:#x} {op}');raise
            r['eip']=nextpc
        return r

"""Original dispatch/history/normalization/quit caller stores in guest Memory.

Follows command_session.cpp/command_runtime.cpp and their pinned i386 ABI.
The legacy readline shim's add_history is a RET; no host history is changed.
All PLT destinations come from the earlier ELF relocation and GOT state.
"""
from .command_storage import string
from .command_catalog import CATALOG
from .signal_install_storage import add_flags,subtract_flags


def logical_flags(value,flags):
    value&=0xffffffff
    return(flags&~0x8d5)|(int(not value)<<6)|((value>>31)<<7)|(int((value&255).bit_count()%2==0)<<2)


class NormalizeFrame:
    """Only source stores; padding and unread locals retain earlier bytes."""
    def __init__(self,memory,registers,flags):
        if flags!=0x8e:raise NotImplementedError('Additional normalizer return-register paths are not bound')
        self.m=memory;self.registers=dict(registers);s=registers['esp'];self.frame=s-4;f=self.frame
        memory.put_u32(f,registers['ebp'])
        for offset,key in ((52,'edi'),(56,'esi'),(60,'ebx')):memory.put_u32(f-offset,registers[key])
        memory.write(f-5,b'\0')
        for offset,value in ((12,flags&2),(16,flags&1),(20,0 if flags&1 else(flags>>3)&1),(24,flags&16),(28,flags&32),(32,flags&64),(36,flags&128),(40,0),(44,0)):
            memory.put_u32(f-offset,value)
    def source(self,pointer):
        self.m.put_u32(self.frame-4,pointer);self.registers['ecx']=self.registers['ecx']&~255
    def character(self,value):self.m.put_u32(self.frame-48,value)
    def content(self):self.m.put_u32(self.frame-40,1)
    def begin_quote(self,value):
        self.content();self.m.put_u32(self.frame-44,1);self.m.write(self.frame-5,bytes([value]))
    def end_quote(self):self.m.put_u32(self.frame-44,0)
    def trim(self,byte,index,classification):
        self.registers['ecx']=(self.registers['ecx']&~255)|byte;self.registers['edx']=index&0xffffffff
        self.registers['eflags']=logical_flags((classification>>8)&32,self.registers['eflags'])


class DispatchStorage:
    def __init__(self,memory,characters,loader,context):self.m,self.characters,self.loader,self.context=memory,characters,loader,context
    def _bind(self,registers,name):
        ctx=self.context;map_=ctx['main_map'];plt=next(x['plt']for x in ctx['maps']if x['address']==map_)
        return self.loader.bind_import(registers,map_,name,plt)
    def history(self,registers):
        """Dispatch entry through history binding/RET and caller argument pop."""
        m=self.m;s=registers['esp'];f=s-4;records=f-4160;line=m.u32(s+4);n=len(string(m,line))
        m.put_u32(f,registers['ebp']);m.put_u32(records-4,registers['edi']);m.put_u32(records-8,registers['ebx'])
        result=dict(registers);result.update(eax=0,ecx=(0xffffffff-n-1)&0xffffffff,ebx=line,edi=line+n+1,ebp=f,esp=records-8)
        result['eflags']=subtract_flags(result['ecx'],0xfffffffe,registers['eflags']&~0x400)
        if n:
            m.put_u32(records-12,line);m.put_u32(records-16,0x804c5bd);result['esp']=records-16
            binding=self._bind(result,b'add_history');result=binding['registers']
            stub=next((x for x in self.context['maps']if x['name'].endswith('/libreadline.so.3')),None)
            if stub is None or stub['plt']['elf_sha256']!='91bfdf1bce9990520d44fc1d66d7a0dbb0a14c5a096acaab1cfae93ec333d90f' or binding['target']!=m.u32(stub['address'])+0x14b0:
                raise NotImplementedError('History implementation is not the pinned RET shim')
            # The linked shim is exactly RET, then the original ADD ESP,4.
            result.update(esp=records-8,eflags=add_flags(records-12,4,result['eflags']))
        result['eip']=0x804c5c0
        return result
    def before_parser(self,registers):
        m=self.m;f=registers['ebp'];records=f-4160;line=registers['ebx'];s=records-20
        m.put_u32(records-12,0x8e);m.put_u32(records-16,line);m.put_u32(s,0x804c5cb)
        incoming=dict(registers);incoming['esp']=s;abi=NormalizeFrame(m,incoming,0x8e)
        self.characters.normalize(m,line,0x8e,abi=abi)
        m.put_u32(records-20,records);m.put_u32(records-24,line);m.put_u32(records-28,0x804c5d8)
        result=abi.registers;result.update(eax=line,edi=records,esp=records-28,eip=0x8086fc0)
        return result
    def quit_binding(self,registers):
        """Parser return through caller CMP and lazy kill target entry."""
        m=self.m;result=dict(registers);f=registers['ebp'];records=f-4160;identity=registers['eax']
        if identity!=0xffffffff:raise NotImplementedError('Non-quit dispatch needs the outer command executor')
        result.update(edx=identity,esp=records-20,eflags=subtract_flags(identity,0xffffffff,registers['eflags']))
        m.put_u32(records-12,3);m.put_u32(records-16,0);m.put_u32(records-20,0x804c5eb)
        return self._bind(result,b'kill')['registers']
    def parser_return(self,registers,identity,line):
        """Catalog addressing retained by the native no-argument parser path."""
        if identity!=-1:raise NotImplementedError('Additional parser return ABI paths are not bound')
        name=string(self.m,line).decode('ascii');index=next((i for i,row in enumerate(CATALOG)if name in row[1]),None)
        if index is None:raise ValueError('Parsed command absent from its catalog')
        result=dict(registers);result.update(eax=identity&0xffffffff,ecx=index*92,esp=registers['ebp']-4160-24,eip=0x804c5d8)
        return result


def enter_dispatch(memory,workspace,main_frame,line,*,ebx,edi,flags,inherited=None):
    """main's retained acquisition arguments and subsequent dispatch call."""
    text=string(memory,line)+b'\0';remaining=5
    for a,b in zip(text,b'QUIT\0'):
        remaining-=1
        if a!=b:break
    else:
        if not remaining:raise NotImplementedError('Acquisition QUIT cancellation needs its exception path')
    top=workspace+4472
    memory.put_u16(top-4,1);memory.put_u32(top-8,line);memory.put_u32(top-12,0x80b4821)
    memory.put_u32(top-16,line);memory.put_u32(top-20,0x804b078)
    # The controlled direct-script startup has no delay-setting command.
    # The acquisition caller loads its initialized zero delay into EDX.
    return dict(inherited or {},eax=0,ebx=ebx,ecx=remaining,edx=0,esi=line,edi=edi,ebp=main_frame,esp=top-20,eip=0x804c598,eflags=logical_flags(0,flags&~0x400))

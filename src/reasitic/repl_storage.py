"""Original main/acquisition/stdio caller stores around source stream IO.

Only caller frames and the proven successful single-threaded fflush return
ABI are implemented here. printf/libio child frames, kernel polling and
stdin read internals remain separate work; their missing bytes are still
checked by the complete continuing comparison.

The fflush/sync and orientation stores follow glibc 2.39 iofflush.c,
fileops.c and genops.c, Copyright (C) 1993-2024 Free Software Foundation,
Inc., LGPL-2.1-or-later. See web/GLIBC-LGPL-2.1.txt.
"""
from .dispatch_storage import NormalizeFrame,logical_flags
from .signal_install_storage import add_flags


class ReplStorage:
    def __init__(self,memory,context,*,libc_base,tls_base):
        self.m,self.context,self.libc_base,self.tls_base=memory,context,libc_base,tls_base

    def _flush_return(self,registers):
        """Known caller/prologue stores and successful unlocked return ABI.

        The source ConsoleStorage/stream operation supplies successful IO.
        No later native call state supplies a register or pointer here.
        Internal sync/printf frames are deliberately not synthesized.
        """
        m=self.m;s=registers['esp'];stream=m.u32(s+4);lock=m.u32(stream+72)
        if m.u32(stream)&0x8000 or m.u32(self.tls_base+12) or any(m.u32(lock+i)for i in (0,4,8)):
            raise NotImplementedError('fflush return ABI needs an unlocked single-threaded stream')
        if m.u32(stream+4)!=m.u32(stream+8):raise NotImplementedError('fflush unread input needs its seek path')
        f=s-4;m.put_u32(f,registers['ebp'])
        for offset,key in ((4,'edi'),(8,'esi'),(12,'ebx')):m.put_u32(f-offset,registers[key])
        # The successful sync return is followed by the lock-depth TEST and
        # owner/lock release. Its final fields equal their earlier zeros.
        # Successful _IO_file_sync invalidates its cached off64_t position.
        m.write(stream+76,b'\xff'*8)
        m.put_u32(lock+8,0);m.put_u32(lock,0)
        result=dict(registers);result.update(eax=0,ecx=m.u32(self.tls_base+12),edx=lock,
            esp=s+4,eip=m.u32(s),eflags=logical_flags(m.u32(lock+4),registers['eflags']))
        return result

    def before_poll(self,parent,line):
        m=self.m;top=parent['esp'];main=parent['ebp'];prompt=0x80b4821
        if not self.context['stdin_regular'] or self.context['stdin_position']!=0:
            raise NotImplementedError('REPL caller needs earlier regular-file stdin at its beginning')
        if m.u32(0x80d8644)!=0x804b4fc or m.read(0x80cbab0,1)!=b'\0' or m.read(0x80cbab8,1)!=b'\0':
            raise NotImplementedError('REPL caller needs direct stdio with recording disabled')
        m.put_u16(top-4,1);m.put_u32(top-8,line);m.put_u32(top-12,prompt);m.put_u32(top-16,0x804b072)
        acquisition=top-20;m.put_u32(acquisition,main)
        for offset,value in ((4,parent['edi']),(8,line),(12,parent['ebx'])):m.put_u32(acquisition-offset,value)
        m.put_u16(acquisition-16,(parent['eax']&0xff00)|1)
        m.put_u32(acquisition-20,line);m.put_u32(acquisition-24,prompt);m.put_u32(acquisition-28,0x804b0f4)
        f=acquisition-32;self.frame=f;m.put_u32(f,acquisition)
        for offset,value in ((1028,parent['edi']),(1032,line),(1036,parent['ebx'])):m.put_u32(f-offset,value)
        m.put_u16(f-1040,0);m.put_u32(f-1044,prompt);m.put_u32(f-1048,0x804b5d1)
        message=f-1052;m.put_u32(message,f);m.put_u32(message-4,line);m.put_u32(message-8,parent['ebx'])
        m.put_u32(message-12,prompt);m.put_u32(message-16,0x80b4891);m.put_u32(message-20,0x804c012)
        m.put_u32(message-20,m.u32(0x80d7d68));m.put_u32(message-24,0x804c01d)
        registers=dict(parent,eax=0,ebx=parent['ebx']&~255,esi=prompt,ebp=message,esp=message-24)
        result=self._flush_return(registers)
        # Message's disabled log/record branches restore the stdio caller;
        # its ADD ESP,8 supplies the flags at the subsequent poll call.
        m.put_u32(f-1040,0x804b5e0)
        result.update(ebx=parent['ebx'],esi=line,edi=parent['edi'],ebp=f,esp=f-1040,eip=0x804bdc4,
            eflags=add_flags(f-1044,8,result['eflags']))
        self.poll_registers=result
        return dict(result)

    def before_input(self):
        """The regular-file stdin path's flush and fgets caller arguments."""
        m=self.m;f=self.frame;registers=self.poll_registers
        m.put_u32(f-1040,m.u32(0x80d7ddc));m.put_u32(f-1044,0x804b5f8)
        self._flush_return(dict(registers,esp=f-1044))
        for offset,value in ((1044,m.u32(0x80d7ddc)),(1048,1024),(1052,registers['esi']),(1056,0x804b609)):
            m.put_u32(f-offset,value)
        stream=m.u32(0x80d7ddc);mode=m.u32(stream+104)
        if mode not in (0,0xffffffff):raise NotImplementedError('Wide-oriented stdin needs its separate read path')
        # The first narrow __underflow sets orientation through _IO_fwide.
        if not mode:m.put_u32(stream+104,0xffffffff)

    def finish_line(self,characters,input_log,output_log):
        """Append/log caller frames and the real normalization local stores."""
        m=self.m;f=self.frame;parent=self.poll_registers;line=parent['esi'];prompt=0x80b4821
        for offset,value in ((1040,0x80b4895),(1044,line),(1048,0x804b617),
                             (1048,prompt),(1052,line),(1056,0x804b621)):
            m.put_u32(f-offset,value)
        log=f-1060;m.put_u32(log,f);m.put_u32(log-4,line);m.put_u32(log-8,parent['ebx'])
        for offset,value in ((12,line),(16,0x80b4b01),(20,input_log),(24,0x804be86),
                             (24,input_log),(28,0x804be91)):
            m.put_u32(log-offset,value)
        registers=dict(parent,ebx=line,esi=prompt,ebp=log,esp=log-28)
        self._flush_return(registers)
        for offset,value in ((28,line),(32,prompt),(36,0x80b4c16),(40,output_log),(44,0x804bea3),
                             (12,output_log),(16,0x804beb1)):
            m.put_u32(log-offset,value)
        result=self._flush_return(dict(registers,esp=log-16))
        m.put_u32(f-1056,0x8e);m.put_u32(f-1060,line);m.put_u32(f-1064,0x804b62c)
        incoming=dict(result,ebx=parent['ebx'],esi=line,ebp=f,esp=f-1064)
        abi=NormalizeFrame(m,incoming,0x8e);characters.normalize(m,line,0x8e,abi=abi)

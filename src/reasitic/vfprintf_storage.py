"""Pinned i386 vfprintf caller with its real formatter on shared guest memory.

Follows glibc 2.39 stdio-common/vfprintf-internal.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Whole calls require earlier CPU/FP inputs;
no formatted text or child return snapshot supplies execution.
"""
from .signal_install_storage import add_flags,subtract_flags

MASK=0xffffffff


class VfprintfStorage:
    def __init__(self,file_storage,*,shr1_af=None,xstate=None):
        self.file=file_storage;self.m=file_storage.m;self.libc=file_storage.libc;self.got=file_storage.got;self.tls=file_storage.tls
        self.heap=file_storage.heap;self.children=file_storage.children
        self.shr1_af=shr1_af;self.xstate=None if xstate is None else bytes(xstate);self.observer=None
        self.formatter_children_start=None;self.formatter_children_end=None

    def before_formatter(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-220
        if r['eip']!=self.libc+0x62110:raise NotImplementedError('Alternate vfprintf needs its source ABI')
        self.file._save4(r);m.put_u32(s-20,self.libc+0x6211d)
        file=m.u32(s+4);fmt=m.u32(s+8);arguments=m.u32(s+12);flags=m.u32(file)
        m.put_u32(local+8,arguments);m.put_u32(local+188,m.u32(self.tls+20))
        r.update(eax=0,ebx=self.got,edi=file,esi=fmt)
        offset=m.read(file+70,1)[0]
        if not offset:
            r['edx']=m.u32(self.got+0x11c)
            if not r['edx']:raise NotImplementedError('Vfprintf incompatible-stream orientation needs its helper source')
            mode=m.u32(file+104);r['eax']=mode
            if not mode:m.put_u32(file+104,MASK)
            elif mode!=MASK:raise NotImplementedError('Vfprintf wide orientation needs its rejection ABI')
        r['eax']=flags
        if flags&8 or not fmt:raise NotImplementedError('Vfprintf invalid output/format needs its error ABI')
        if not offset:
            r['eax']=m.u32(self.got+0x11c)
            if not r['eax']:raise NotImplementedError('Vfprintf incompatible-stream orientation needs its helper source')
            r['eax']=m.u32(file+104)
            if r['eax']!=MASK:raise NotImplementedError('Vfprintf orientation is not narrow')
        if m.read(file+60,1)[0]&128:raise NotImplementedError('Vfprintf locked/cancellation path needs its source ABI')
        buffer=local+32;m.put_u32(local-12,file);m.put_u32(local-16,buffer);m.put_u32(local-20,self.libc+0x62333)
        r.update(ebp=buffer,esp=local-20,eip=self.libc+0x586c0,eflags=subtract_flags(local,8,r['eflags']))
        r=self.file._child('init',r,self.file.init)
        for offset,value in ((20,m.u32(s+16)),(24,m.u32(local+8)),(28,fmt),(32,buffer),(36,self.libc+0x62345)):m.put_u32(local-offset,value)
        return dict(r,esp=local-36,eip=self.libc+0x60530)

    def after_formatter(self,registers):
        m=self.m;r=dict(registers);local=r['esp']+32;s=local+220;buffer=r['ebp']
        if r['eip']!=self.libc+0x62345:raise NotImplementedError('Alternate formatter return needs its parent source ABI')
        if buffer!=local+32:raise ValueError('Formatter did not preserve the vfprintf buffer register')
        m.put_u32(local-16,buffer);m.put_u32(local-20,self.libc+0x6234e)
        r.update(esp=local-20,eip=self.libc+0x58710,eflags=add_flags(local-32,20,r['eflags']))
        r=self.file._child('done',r,self.file.done);count=r['eax']
        if m.u32(local+188)!=m.u32(self.tls+20):raise ValueError('Vfprintf stack canary mismatch')
        return self.file._return4(dict(r,eax=count,eflags=add_flags(local,204,r['eflags'])),s)

    def call(self,registers,formatter=None):
        if formatter is None and(self.shr1_af is None or self.xstate is None):raise NotImplementedError('Vfprintf parser and numeric formatter requires actual earlier CPU/FP inputs')
        incoming=self.before_formatter(registers)
        self.formatter_children_start=len(self.children)
        if self.observer:self.observer('formatter-before',dict(incoming),self.xstate)
        if formatter is None:
            from .printf_format import PrintfFormat
            child=PrintfFormat(self.file,shr1_af=self.shr1_af,xstate=self.xstate);result=child.format(incoming);self.xstate=child.xstate
        else:result=formatter(incoming)
        self.formatter_children_end=len(self.children)
        if self.observer:self.observer('formatter-after',dict(result),self.xstate)
        return self.after_formatter(result)

    def vfprintf(self,registers):return self.call(registers)

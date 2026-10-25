"""Pinned i386 printf buffer write and its actual scalar memcpy child.

Follows glibc 2.39 stdio-common/printf_buffer_write.c and i386 memcpy.S,
Copyright (C) 2022-2024 Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Buffer exhaustion needs its flush-mode source.
"""
from .getline_bytes import GetlineBytes
from .signal_install_storage import add_flags,subtract_flags


class PrintfBuffer:
    def __init__(self,memory,*,libc_base,shr1_af):
        self.m=memory;self.libc=libc_base;self.bytes=GetlineBytes(memory,libc_base=libc_base,shr1_af=shr1_af);self.children=[]

    def write(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-28
        if r['eip']!=self.libc+0x58750:raise NotImplementedError('Alternate printf buffer writer needs its source ABI')
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(s-20,self.libc+0x5875d)
        buffer=m.u32(s+4);source=m.u32(s+8);remaining=m.u32(s+12);mode=m.u32(buffer+20)
        r.update(ebp=buffer,ebx=self.libc+0x22fe34,edx=source,edi=remaining,eax=mode)
        if mode and remaining:
            pointer=m.u32(buffer+4)
            while remaining:
                end=m.u32(buffer+8)
                if pointer==end:raise NotImplementedError('Exhausted printf buffer needs its flush-mode source')
                if pointer>end:raise ValueError('Printf buffer pointer exceeds its end')
                count=min(end-pointer,remaining)
                for offset,value in ((8,count),(12,source),(16,pointer),(20,self.libc+0x587a6)):m.put_u32(local-offset,value)
                m.put_u32(s+8,source)
                incoming=dict(r,eax=pointer,edx=source,esi=count,edi=remaining,esp=local-20,eip=self.libc+0xbbae0,eflags=subtract_flags(local,4,r['eflags']))
                r=self.bytes.memcpy(incoming);self.children.append(dict(kind='memcpy',before=incoming,after=dict(r)))
                pointer=(m.u32(buffer+4)+count)&0xffffffff;source=(m.u32(s+8)+count)&0xffffffff;remaining-=count
                m.put_u32(buffer+4,pointer)
                r.update(eax=pointer,edx=source,edi=remaining)
        r.update(ebp=m.u32(s-4),edi=m.u32(s-8),esi=m.u32(s-12),ebx=m.u32(s-16),esp=s+4,eip=m.u32(s),eflags=add_flags(local,12,r['eflags']))
        return r

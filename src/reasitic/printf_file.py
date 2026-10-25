"""Pinned i386 printf FILE-buffer setup and completion source.

Follows glibc 2.39 printf_buffer_to_file.c and printf_buffer_done.c,
Copyright (C) 2022-2024 Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt.
"""
from .signal_install_storage import add_flags,subtract_flags

MASK=0xffffffff


class PrintfFile:
    def __init__(self,memory,*,libc_base,tls_base,heap=None,io=None):
        self.m=memory;self.libc=libc_base;self.got=libc_base+0x22fe34;self.tls=tls_base;self.children=[];self.heap=heap;self.io=io

    def _child(self,kind,registers,function):
        item=dict(kind=kind,before=dict(registers));self.children.append(item);result=function(registers);item['after']=dict(result);return result

    def _save4(self,r):
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):self.m.put_u32(r['esp']-offset,r[key])

    def _return4(self,r,s):
        m=self.m
        return dict(r,ebp=m.u32(s-4),edi=m.u32(s-8),esi=m.u32(s-12),ebx=m.u32(s-16),esp=s+4,eip=m.u32(s))

    def switch(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];buf=m.u32(s+4);file=m.u32(buf+24);pointer=m.u32(file+20);end=m.u32(file+24)
        if r['eip']!=self.libc+0x58570:raise NotImplementedError('Alternate printf FILE switch needs its source ABI')
        flags=subtract_flags(pointer,end,r['eflags'])
        if pointer>=end:pointer=(buf+28)&MASK;end=(buf+156)&MASK
        for offset,value in ((8,end),(4,pointer),(0,pointer)):m.put_u32(buf+offset,value)
        return dict(r,eax=buf,ecx=end,edx=pointer,esp=s+4,eip=m.u32(s),eflags=flags)

    def init(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-24;buf=m.u32(s+4);file=m.u32(s+8)
        if r['eip']!=self.libc+0x586c0:raise NotImplementedError('Alternate printf FILE init needs its source ABI')
        m.put_u32(s-4,r['ebx']);m.put_u32(s-8,self.libc+0x586ca)
        for offset,value in ((12,0),(0,buf+28),(4,buf+28),(8,buf+156),(16,0),(20,4),(24,file)):m.put_u32(buf+offset,value)
        m.put_u32(local-4,buf);m.put_u32(local-8,self.libc+0x5870a)
        incoming=dict(r,eax=buf,edx=file,ebx=self.got,esp=local-8,eip=self.libc+0x58570,eflags=subtract_flags(s-4,20,r['eflags']))
        r=self._child('switch',incoming,self.switch)
        return dict(r,ebx=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(local-4,24,r['eflags']))

    def done(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-12;buf=m.u32(s+4)
        if r['eip']!=self.libc+0x58710:raise NotImplementedError('Alternate printf FILE done needs its source ABI')
        m.put_u32(s-4,r['ebx']);mode=m.u32(buf+20);r.update(ebx=buf,eax=mode)
        if not mode:return dict(r,eax=MASK,ebx=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(local,8,r['eflags']))
        m.put_u32(local-16,buf);m.put_u32(local-20,self.libc+0x5872c)
        incoming=dict(r,esp=local-20,eip=self.libc+0x585a0,eflags=subtract_flags(local,12,r['eflags']))
        r=self._child('flush-to-file',incoming,self.flush_to_file)
        m.put_u32(s+4,buf);r.update(ebx=m.u32(s-4),esp=s,eip=self.libc+0x58190,eflags=add_flags(local-16,24,r['eflags']))
        return self._child('buffer-done',r,self.buffer_done)

    def flush_to_file(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-44;buf=m.u32(s+4)
        if r['eip']!=self.libc+0x585a0:raise NotImplementedError('Alternate printf FILE flush needs its source ABI')
        m.put_u32(s-4,r['ebp']);m.put_u32(s-8,r['edi']);m.put_u32(s-12,self.libc+0x585ab);m.put_u32(s-12,r['esi']);m.put_u32(s-16,r['ebx'])
        pointer=m.u32(buf+4);delta=(pointer-m.u32(buf))&MASK;low=m.u32(buf+12)+delta;high=(m.u32(buf+16)+(MASK if delta&0x80000000 else 0)+(low>>32))&MASK
        m.put_u32(buf+12,low);m.put_u32(buf+16,high);end=m.u32(buf+8);stage_end=(buf+156)&MASK;one_end=(buf+29)&MASK
        r.update(eax=end,edx=stage_end,esi=pointer,ebx=buf,edi=self.got)
        if end==stage_end:
            from .output_file import OutputFile
            file=m.u32(buf+24);source=(buf+28)&MASK;count=(pointer-source)&MASK;vt=self.vtable(file)
            m.put_u32(local+8,count)
            for offset,value in ((8,count),(12,source),(16,file),(20,self.libc+0x58666)):m.put_u32(local-offset,value)
            incoming=dict(r,eax=file,edx=source,ecx=self.got-0x734,esi=count,ebp=vt,esp=local-20,eip=m.u32(vt+28),eflags=subtract_flags(local,4,r['eflags']))
            r=self._child('xsputn',incoming,OutputFile(self).xsputn)
            if r['eax']!=count:
                m.put_u32(buf+20,0)
            else:
                m.put_u32(local-16,buf);m.put_u32(local-20,self.libc+0x58627)
                incoming=dict(r,ebx=self.got,esp=local-20,eip=self.libc+0x58570,eflags=subtract_flags(local,12,r['eflags']))
                r=self._child('switch',incoming,self.switch)
            r['eflags']=add_flags(local,28,r['eflags']);return self._return4(r,s)
        r['edx']=one_end
        if end==one_end:
            if pointer==end:raise NotImplementedError('One-byte printf staging needs its overflow source')
        else:
            file=m.u32(buf+24);r['ecx']=file
            if end!=m.u32(file+24):raise NotImplementedError('Printf FILE end mismatch needs its assertion path')
            m.put_u32(file+20,pointer)
            if pointer==end:
                pointer=(buf+28)&MASK;m.put_u32(buf+8,one_end);m.put_u32(buf+4,pointer)
            m.put_u32(buf,pointer)
        r['eflags']=add_flags(local,28,r['eflags']);return self._return4(r,s)

    def vtable(self,file):
        offset=self.m.read(file+70,1)[0];offset=offset-256 if offset&128 else offset
        table=self.m.u32(file+148+offset)
        if not 0<=(table-(self.got-0x734))&MASK<=0x593:raise NotImplementedError('Output foreign vtable needs its guard source ABI')
        return table

    def buffer_done(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-36;buf=m.u32(s+4)
        if r['eip']!=self.libc+0x58190:raise NotImplementedError('Alternate printf count completion needs its source ABI')
        m.put_u32(s-4,self.libc+0x58199);self._save4(r);m.put_u32(local+12,self.got)
        mode=m.u32(buf+20);r.update(eax=buf,edx=mode)
        if not mode:r['eax']=MASK
        else:
            current=(m.u32(buf+4)-m.u32(buf))&MASK;total=current+m.u32(buf+12);low=total&MASK;high=(m.u32(buf+16)+(total>>32))&MASK
            error=bool(high&0x80000000)or(high==0 and low<current);sign=MASK if low&0x80000000 else 0
            m.put_u32(local,low);m.put_u32(local+4,sign);r.update(eax=low,edx=high,ecx=high^sign)
            if error or r['ecx']:
                thread=m.u32(self.tls);offset=m.u32(self.got+0xa0);m.put_u32((thread+offset)&MASK,75);r.update(eax=MASK,edx=thread)
        r['eflags']=add_flags(local,20,r['eflags']);return self._return4(r,s)

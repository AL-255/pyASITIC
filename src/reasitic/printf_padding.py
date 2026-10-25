"""Pinned i386 printf padding and its scalar memset stores.

Follows glibc 2.39 printf_buffer_pad_1.c and i386 memset.S,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. The memset multiply's
undefined condition flags are dead before the observable padding return.
No result, memory or register target supplies source inputs.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags

MASK=0xffffffff


class PrintfPadding:
    def __init__(self,file_storage):self.file=file_storage;self.m=file_storage.m;self.libc=file_storage.libc;self.got=file_storage.got

    def _memset(self,r):
        m=self.m;s=r['esp'];p=m.u32(s+4);count=m.u32(s+12);byte=m.read(s+8,1)[0];old_edi=r['edi'];m.put_u32(s-4,old_edi);edx=p
        def store(n):
            nonlocal p,count
            m.write(p,bytes([byte])*n);p=(p+n)&MASK;count-=n
        if count:
            edx=p&3
            if edx:
                if edx!=3:
                    store(1)
                    if not count:return dict(r,eax=m.u32(s+4),edx=edx,ecx=0,edi=m.u32(s-4),esp=s+4,eip=m.u32(s))
                store(1)
                if not count:return dict(r,eax=m.u32(s+4),edx=edx,ecx=0,edi=m.u32(s-4),esp=s+4,eip=m.u32(s))
                edx^=1
                if not edx:store(1)
            edx=count&3;store(count)
        return dict(r,eax=m.u32(s+4),edx=edx,ecx=0,edi=m.u32(s-4),esp=s+4,eip=m.u32(s))

    def pad(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-44
        if r['eip']!=self.libc+0x58390:raise NotImplementedError('Alternate printf padding needs its source ABI')
        self.file._save4(r);m.put_u32(s-20,self.libc+0x5839d)
        buf=m.u32(s+4);remaining=m.u32(s+12);byte=m.read(s+8,1)[0];mode=m.u32(buf+20)
        r.update(ebp=buf,edi=remaining,ecx=byte,eax=mode,ebx=self.got)
        if mode:
            signed=byte if byte<128 else byte-256;m.put_u32(local+12,signed);pointer=m.u32(buf+4);r.update(edx=signed&MASK,eax=pointer)
            while True:
                end=m.u32(buf+8);r['esi']=end
                if end==pointer:raise NotImplementedError('Exhausted printf padding needs its flush source')
                count=min((end-pointer)&MASK,remaining);r['esi']=count
                for offset,value in ((8,count),(12,signed),(16,pointer),(20,self.libc+0x583e5)):m.put_u32(local-offset,value)
                r=self._memset(dict(r,esp=local-20,eip=self.libc+0xbbc10))
                pointer=(m.u32(buf+4)+count)&MASK;m.put_u32(buf+4,pointer);remaining=(remaining-count)&MASK;r.update(eax=pointer,edi=remaining)
                if not remaining:break
        r['eflags']=add_flags(local,28,r['eflags']);return self.file._return4(r,s)

"""Pinned i386 scalar strlen, including unaligned and word-at-a-time probes.

Follows glibc 2.39 sysdeps/i386/strlen.S, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Reads only actual owned bytes, including the
aligned word containing the terminator. No padding is invented.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags
from .getline_bytes import GetlineBytes,cmp8,inc,dec

MASK=0xffffffff
MAGIC=0xfefefeff


class StrlenStorage:
    def __init__(self,memory,*,libc_base,shr1_af):
        self.m,self.libc=memory,libc_base;self.bytes=GetlineBytes(memory,libc_base=libc_base,shr1_af=shr1_af)

    def length(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];start=m.u32(s+4);p=start;edx=p&3;ecx=r['ecx'];flags=logical_flags(edx,r['eflags'])
        if r['eip']!=self.libc+0xbc470:raise NotImplementedError('Alternate strlen needs its source ABI')
        def returned():
            return dict(r,eax=(p-start)&MASK,edx=edx,ecx=ecx,esp=s+4,eip=m.u32(s),eflags=subtract_flags(p,start,flags))
        if edx:
            # The parity branch skips the first two byte probes for offset 3.
            if not flags&4:
                for _ in range(2):
                    flags=cmp8(m.read(p,1)[0],edx>>8,flags)
                    if flags&64:return returned()
                    p,flags=inc(p,flags)
                edx^=2;flags=logical_flags(edx,flags)
            if edx:
                flags=cmp8(m.read(p,1)[0],edx>>8,flags)
                if flags&64:return returned()
                p,flags=inc(p,flags);edx=0;flags=logical_flags(0,flags)
        while True:
            # Four identical unrolled word probes in the native source.
            ecx=m.u32(p);p=(p+4)&MASK;edx=(edx-ecx)&MASK
            flags=add_flags(ecx,MAGIC,flags);ecx=(ecx+MAGIC)&MASK;edx,flags=dec(edx,flags)
            if not flags&1:break
            edx=(edx^ecx)&0x01010100;flags=logical_flags(edx,flags)
            if edx:break
        p=(p-4)&MASK;ecx=(ecx-MAGIC)&MASK
        if ecx&255:
            p,flags=inc(p,flags)
            if ecx&0xff00:
                ecx>>=16;p,flags=inc(p,flags)
                if ecx&255:p,flags=inc(p,flags)
        return returned()

    def bounded(self,registers):
        """The scalar strnlen wrapper and its real, bounded memchr child."""
        m=self.m;r=dict(registers);s=r['esp'];local=s-16;source=m.u32(s+4);limit=m.u32(s+8)
        if r['eip']!=self.libc+0xbb390:raise NotImplementedError('Alternate strnlen needs its source ABI')
        m.put_u32(s-4,r['esi']);m.put_u32(s-8,r['ebx'])
        for offset,value in ((4,limit),(8,0),(12,source),(16,self.libc+0xbb3aa)):m.put_u32(local-offset,value)
        incoming=dict(r,esi=source,ebx=limit,esp=local-16,eip=self.libc+0xbb650,eflags=subtract_flags(s-8,8,r['eflags']))
        r=self.bytes.memchr(incoming);delta=(r['eax']-source)&MASK;result=delta if r['eax']else limit
        return dict(r,eax=result,edx=delta,ebx=m.u32(s-8),esi=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(local-12,20,r['eflags']))

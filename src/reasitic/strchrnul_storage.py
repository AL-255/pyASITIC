"""Pinned i386 scalar strchrnul source, including its actual word probes.

Follows glibc 2.39 i386 strchrnul.S, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Unknown padding is never synthesized.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags
from .getline_bytes import cmp8,test8,inc

MASK=0xffffffff
MAGIC=0xfefefeff


class StrchrnulStorage:
    def __init__(self,memory,*,libc_base):self.m,self.libc=memory,libc_base

    def search(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];p=m.u32(s+4);needle=m.u32(s+8);m.put_u32(s-4,r['edi'])
        if r['eip']!=self.libc+0xa3cb0:raise NotImplementedError('Alternate strchrnul needs its source ABI')
        needle=(needle&~0xff00)|((needle&255)<<8);ecx=needle;needle=((needle<<16)&MASK)|(ecx&0xffff);flags=r['eflags']
        def returned():return dict(r,eax=p,ecx=ecx,edx=needle,edi=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=flags)
        flags=test8(p&3,flags)
        while p&3:
            ecx=(ecx&~255)|m.read(p,1)[0];flags=cmp8(needle,ecx,flags)
            if flags&64:return returned()
            flags=test8(ecx,flags)
            if flags&64:return returned()
            p,flags=inc(p,flags);flags=test8(p&3,flags)
        def possible(value):
            nonlocal flags
            flags=add_flags(MAGIC,value,flags);word=(MAGIC+value)&MASK
            if not flags&1:return True
            word^=value;flags=logical_flags(word,flags);word|=MAGIC;flags=logical_flags(word,flags);word,flags=inc(word,flags)
            return bool(word)
        while True:
            hit=False
            for offset in (0,4,8,12):
                ecx=m.u32(p+offset)^needle;flags=logical_flags(ecx,flags)
                hit=possible(ecx)
                if not hit:ecx^=needle;flags=logical_flags(ecx,flags);hit=possible(ecx)
                if hit:
                    for _ in range(offset//4):flags=add_flags(p,4,flags);p=(p+4)&MASK
                    break
            if hit:break
            flags=add_flags(p,16,flags);p=(p+16)&MASK
        flags=test8(ecx,flags)
        if flags&64:return returned()
        flags=cmp8(ecx,needle,flags)
        if flags&64:return returned()
        p,flags=inc(p,flags);flags=test8(ecx>>8,flags)
        if flags&64:return returned()
        flags=cmp8(ecx>>8,needle,flags)
        if flags&64:return returned()
        p,flags=inc(p,flags);ecx>>=16;flags=test8(ecx,flags)
        if flags&64:return returned()
        flags=cmp8(ecx,needle,flags)
        if flags&64:return returned()
        p,flags=inc(p,flags);return returned()

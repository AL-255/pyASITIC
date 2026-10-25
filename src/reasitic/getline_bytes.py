"""Pinned i386 scalar memchr/memcpy used internally by getline.

Follows glibc 2.39 i386 memchr.S/memcpy.S, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. These direct internal calls use no SIMD/FP.
The undefined SHR AF behavior is an independent earlier CPU input.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags

MASK=0xffffffff


def cmp8(left,right,flags):
    left&=255;right&=255;value=(left-right)&255
    bits=int(left<right)|(int(not value)<<6)|(value&128)|(int((value&255).bit_count()%2==0)<<2)
    bits|=int(bool((left^right^value)&16))<<4|int(bool((left^right)&(left^value)&128))<<11
    return(flags&~0x8d5)|bits


def test8(value,flags):
    return(logical_flags(value&255,flags)&~128)|(value&128)


def inc(value,flags):
    return(value+1)&MASK,(add_flags(value,1,flags)&~1)|(flags&1)


def dec(value,flags):
    return(value-1)&MASK,(subtract_flags(value,1,flags)&~1)|(flags&1)


class GetlineBytes:
    def __init__(self,memory,*,libc_base,shr1_af):
        if shr1_af not in (0,16,'preserve'):raise ValueError('SHR AF needs the earlier CPU behavior profile')
        self.m=memory;self.libc=libc_base;self.shr1_af=shr1_af

    def memchr(self,registers):
        m=self.m;r=dict(registers);s=r['esp']
        if r['eip']!=self.libc+0xbb650:raise NotImplementedError('Alternate memchr implementation needs its source ABI')
        m.put_u32(s-4,r['esi']);m.put_u32(s-8,r['edi'])
        pointer=m.u32(s+4);needle=m.u32(s+8);remaining=m.u32(s+12);ecx=r['ecx'];flags=subtract_flags(remaining,4,r['eflags'])
        def returned(value):return dict(r,eax=value,ecx=ecx,edx=needle,esi=m.u32(s-4),edi=m.u32(s-8),esp=s+4,eip=m.u32(s),eflags=flags)
        if remaining>=4:
            needle=(needle&~0xff00)|((needle&255)<<8);ecx=needle;needle=((needle<<16)&MASK)|(ecx&0xffff)
            flags=test8(pointer&3,flags)
            while pointer&3:
                flags=cmp8(m.read(pointer,1)[0],needle,flags)
                if flags&64:return returned(pointer)
                pointer,flags=inc(pointer,flags);remaining,flags=dec(remaining,flags)
                if not remaining:
                    flags=logical_flags(0,flags);return returned(0)
                flags=test8(pointer&3,flags)
            # Original 16-byte batches, then its three bounded word probes.
            while True:
                flags=subtract_flags(remaining,16,flags);remaining=(remaining-16)&MASK
                words=4 if not flags&1 else ((remaining+16)&MASK)//4
                for _ in range(words):
                    ecx=m.u32(pointer)^needle;flags=logical_flags(ecx,flags)
                    magic=0xfefefeff;flags=add_flags(magic,ecx,flags);magic=(magic+ecx)&MASK
                    possible=not(flags&1)
                    if not possible:
                        magic^=ecx;flags=logical_flags(magic,flags);magic|=0xfefefeff;flags=logical_flags(magic,flags);magic,flags=inc(magic,flags);possible=bool(magic)
                    if possible:
                        flags=test8(ecx,flags)
                        if flags&64:return returned(pointer)
                        pointer,flags=inc(pointer,flags);flags=test8(ecx>>8,flags)
                        if flags&64:return returned(pointer)
                        pointer,flags=inc(pointer,flags);flags=logical_flags(ecx&0xff0000,flags)
                        if flags&64:return returned(pointer)
                        pointer,flags=inc(pointer,flags);return returned(pointer)
                    flags=add_flags(pointer,4,flags);pointer=(pointer+4)&MASK
                if words<4:break
                # The unrolled loop adds 16 once, rather than four ADDs.
                # Its next SUB overwrites those flags before any use.
        remaining&=3;flags=logical_flags(remaining,flags)
        while remaining:
            flags=cmp8(m.read(pointer,1)[0],needle,flags)
            if flags&64:return returned(pointer)
            pointer,flags=inc(pointer,flags);remaining,flags=dec(remaining,flags)
        flags=logical_flags(0,flags);return returned(0)

    def _shr1(self,value,flags):
        result=value>>1;af=flags&16 if self.shr1_af=='preserve'else self.shr1_af
        return result,logical_flags(result,flags)|(value&1)|((value>>31)<<11)|af

    def memcpy(self,registers):
        m=self.m;r=dict(registers);s=r['esp']
        if r['eip']!=self.libc+0xbbae0:raise NotImplementedError('Alternate memcpy implementation needs its source ABI')
        destination=m.u32(s+4);source=m.u32(s+8);count=m.u32(s+12);old_edi=r['edi'];old_esi=r['esi']
        mismatch=(destination^source)&3;flags=logical_flags(mismatch,r['eflags'])&~0x400
        def copy(width):
            nonlocal destination,source
            m.write(destination,m.read(source,width));destination=(destination+width)&MASK;source=(source+width)&MASK
        if not mismatch:
            flags=subtract_flags(count,3,flags)
        if mismatch or count<=3:
            count,flags=self._shr1(count,flags)
            if flags&1:copy(1)
            count,flags=self._shr1(count,flags)
            if flags&1:copy(2)
            for _ in range(count):copy(4)
        else:
            flags=logical_flags(source&3,flags)
            while source&3:
                copy(1);count,flags=dec(count,flags)
                if source&3:flags=logical_flags(source&3,flags)
            m.put_u32(s-4,old_edi);tail=count&3;flags=logical_flags(tail,flags)
            for _ in range(count>>2):copy(4)
            for _ in range(tail):copy(1)
            old_edi=m.u32(s-4)
        return dict(r,eax=m.u32(s+4),edx=old_esi,ecx=0,edi=old_edi,esi=old_esi,esp=s+4,eip=m.u32(s),eflags=flags)

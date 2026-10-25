"""Pinned i386 printf integer digit construction and output.

Follows glibc 2.39 stdio-common/_itoa.c and vfprintf-process-arg.c,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. Uses original digit tables
and caller storage. No host formatting or later native state is loaded.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags
from .getline_bytes import cmp8
import weakref

MASK=0xffffffff


def signed(value):return value-0x100000000 if value&0x80000000 else value


class ItoaWord:
    def __init__(self,file_storage):self.file=file_storage;self.m=file_storage.m;self.libc=file_storage.libc;self.got=file_storage.got

    def word(self,registers):
        m=self.m;r=dict(registers);s=r['esp']
        if r['eip']!=self.libc+0x56dd0:raise NotImplementedError('Alternate integer digit builder needs its source ABI')
        self.file._save4(r);value=m.u32(s+4);end=m.u32(s+8);radix=m.u32(s+12);upper=m.u32(s+16)
        if not 2<=radix<=36:raise NotImplementedError('Invalid integer digit radix needs its native error path')
        high_table=self.got-0x68414;table=high_table if upper else self.got-0x68454
        while True:
            previous=value;value,remainder=divmod(value,radix);end=(end-1)&MASK;m.write(end,m.read(table+remainder,1))
            if previous<radix:break
        edx=0 if radix==10 else high_table if radix in(8,16)else previous
        flags=subtract_flags(previous,radix-1 if radix in(8,16,10)else radix,r['eflags'])
        return self.file._return4(dict(r,eax=end,ecx=value,edx=edx,eflags=flags),s)


class PrintfInteger:
    def __init__(self,formatter):
        self.f=weakref.proxy(formatter);self.file=formatter.file;self.m=formatter.m;self.libc=formatter.libc;self.got=formatter.got;self.digits=ItoaWord(self.file)

    def _pad(self,r,base,byte,count,ret):
        r=self.f._call(r,base,'pad',0x58390,ret,[r['edi'],byte,count],reserve=4)
        return dict(r,esp=base,eflags=add_flags(base-16,16,r['eflags']))

    def _put(self,r,byte):
        m=self.m;buf=r['edi'];p=m.u32(buf+4);end=m.u32(buf+8);r['eax']=p;r['eflags']=subtract_flags(p,end,r['eflags'])
        if p==end:raise NotImplementedError('Integer sign/prefix output needs its buffer flush source')
        r['ecx']=(p+1)&MASK;m.put_u32(buf+4,r['ecx']);m.write(p,bytes([byte]));return r

    def convert(self,registers,base):
        m=self.m;r=dict(registers);handler=r['ecx']-self.libc;arg=m.u32(base+0x10)
        if m.u32(base):raise NotImplementedError('Long-long integer conversion needs its native two-word path')
        if handler==0x612c8:
            r.update(esi=arg,ebp=m.u32(base+0x50),ecx=m.u32(arg),eax=(arg+4)&MASK)
            if r['ebp']:
                r['ecx']&=255
                if r['ecx']&128:r['ecx']|=0xffffff00
            else:
                short=m.u32(base+0x44);r['esi']=short;r['ebx']=r['ecx']&0xffff
                if r['ebx']&0x8000:r['ebx']|=0xffff0000
                if short:r['ecx']=r['ebx']
            m.put_u32(base+0x10,r['eax']);value=r['ecx'];r['esi']=(-value)&MASK
            if r['esi']&0x80000000:r['esi']=value
            m.put_u32(base,value>>31);radix=10;m.put_u32(base+0x40,radix);r['ecx']=m.read(base+0x3c,1)[0]&1;m.write(base+0x3c,bytes([r['ecx']]))
        else:
            radix={0x612a0:10,0x61240:8,0x61180:16}[handler];m.put_u32(base+0x40,radix)
            m.write(base+0x3c,bytes([m.read(base+0x3c,1)[0]&1])if handler==0x612a0 else b'\0')
            r.update(eax=arg,ecx=m.u32(base),ebp=m.u32(base+0x50));m.put_u32(base+0x10,arg+4)
            if r['ebp']:r['esi']=m.read(arg,1)[0]
            else:r['esi']=m.u16(arg)if m.u32(base+0x44)else m.u32(arg)
            m.put_u32(base+0x24,0);m.put_u32(base+0x2c,0)
        value=r['esi'];precision=m.u32(base+0x14)
        if precision==MASK:precision=1;m.put_u32(base+0x14,1)
        else:m.write(base+0x76,b' ')
        if precision or value:
            # 615e5 ... 61605: native _itoa_word arguments and buffer end.
            code=r['edx'];m.write(base+0x77,bytes([code&255]));r.update(ebp=0,eax=int(code==ord('X')),ebx=base+0x4bc)
            r['eflags']=cmp8(code,ord('X'),r['eflags'])
            r=self.f._call(r,base,'itoa-word',0x56dd0,0x6160a,[value,r['ebx'],radix,r['eax']])
            length=(r['ebx']-r['eax'])&MASK;r['ebx']=length
            # ESP is base-16 until 6161b: these stores address base+50/+44.
            m.put_u32(base+0x50,r['eax']);m.put_u32(base+0x44,length);r['eax']=length;r['ebx']=m.read(base+0x28,1)[0]
            r.update(esp=base,ecx=m.u32(base+0x14),edx=m.read(base+0x77,1)[0]);r['ebx']&=1;m.write(base+0x54,bytes([int(bool(value))]))
            delta=(r['ecx']-length)&MASK;r['ecx']=delta;r['ebp']=max(0,signed(delta));m.put_u32(base+0x5c,delta);m.put_u32(base+0x30,r['ebp'])
        else:
            alternate=m.u32(base+0x28)&1
            # 60e8f/61ccc initialize this byte even when no digits are built.
            m.write(base+0x54,b'\0')
            if radix==8 and alternate:
                r.update(eax=1,ebx=0,ecx=base+0x4bb);m.write(r['ecx'],b'0')
                m.put_u32(base+0x30,0);m.put_u32(base+0x5c,MASK);m.put_u32(base+0x44,1);m.put_u32(base+0x50,r['ecx']);m.write(base+0x76,b' ');m.write(base+0x54,b'\0');m.put_u32(base+0x28,1);m.put_u32(base+0x40,8)
            else:
                r.update(eax=0,ebx=alternate,ecx=base+0x4bc)
                for offset,v in ((0x30,0),(0x5c,0),(0x44,0),(0x50,r['ecx'])):m.put_u32(base+offset,v)
                m.write(base+0x76,b' ')
        if m.u32(base+0x38)or m.read(base+0x3c,1)[0]:raise NotImplementedError('Grouped/localized printf integer needs its native source branch')
        # 61560 ... 60f32, no locale grouping requested.
        m.write(base+0x38,b'\0');r['ebp']=m.u32(base+0x44)
        if m.u32(base+0x18):return self._left(r,base,radix,value)
        if value:
            r['esi']=m.u32(base+0x28);r['eax']=(r['eax']&~255)|int(radix==8);r['esi']&=r['eax'];r['eax']=m.u32(base+0x18)
            r['eax']=(m.u32(base+0x20)-m.u32(base+0x30)-r['ebp'])&MASK
            r['ebx']&=m.read(base+0x54,1)[0]
            if r['ebx']and radix==16:r['eax']=(r['eax']-2)&MASK
            if r['esi']:r['eax']=(r['eax']-1)&MASK
        else:
            r['eax']=m.u32(base+0x18);r['esi']=0
            r.update(eax=(m.u32(base+0x20)-m.u32(base+0x30)-r['ebp'])&MASK,ebx=0)
        r['ecx']=m.u32(base);r['ebp']=m.u32(base+0x2c);r['ecx']|=r['ebp']|m.u32(base+0x24)
        sign=bool(r['ecx'])
        negative=bool(m.u32(base))
        if sign:r['eax']=(r['eax']-1)&MASK
        pad=m.read(base+0x76,1)[0]
        if pad==32:
            if signed(r['eax'])>0:
                if sign:m.write(base+0x14,bytes([r['edx']&255]));r=self._pad(r,base,32,r['eax'],0x619e0);r['edx']=m.read(base+0x14,1)[0]
                else:
                    m.write(base,bytes([r['edx']&255]));r=self._pad(r,base,32,r['eax'],0x61997);r['edx']=m.read(base,1)[0]
            if negative:r=self._put(r,45)
            elif m.u32(base+0x24):r=self._put(r,43)
            elif m.u32(base+0x2c):r=self._put(r,32)
        else:
            m.put_u32(base+0x30,m.u32(base+0x30)+r['eax'])
            if sign:
                if m.u32(base):r=self._put(r,45)
                elif m.u32(base+0x24):r=self._put(r,43)
                elif m.u32(base+0x2c):r=self._put(r,32)
        if r['ebx']:
            r['ebx']=radix;r['eax']=0x10004
            if radix==16:
                r=self._put(r,48);r=self._put(r,r['edx']&255)
        r['eax']=m.u32(base+0x30);r['eflags']=logical_flags(r['eax'],r['eflags'])
        if signed(r['eax'])>0:r=self._pad(r,base,48,r['eax'],0x60fb8)
        if r['esi']:
            r=self._put(r,48);r['edx']=r['ecx']
        r['eflags']=cmp8(m.read(base+0x38,1)[0],0,logical_flags(r['esi'],r['eflags']))
        r=self.f._call(r,base,'write',0x58750,0x61659,[r['edi'],m.u32(base+0x50),m.u32(base+0x44)],reserve=4)
        return dict(r,esp=base,eflags=add_flags(base-16,16,r['eflags']))

    def _left(self,r,base,radix,value):
        m=self.m;r['esi']=int(bool(m.u32(base+0x28))and radix==8 and bool(value))
        r['eax']=m.u32(base)
        sign=45 if r['eax']else 43 if m.u32(base+0x24)else 32 if m.u32(base+0x2c)else None
        if sign is not None:r=self._put(r,sign);m.put_u32(base+0x20,m.u32(base+0x20)-1)
        if r['ebx']and m.read(base+0x54,1)[0]and radix==16:
            r['ebx']=radix;r['eax']=0x10004;r=self._put(r,48);r=self._put(r,r['edx']&255);m.put_u32(base+0x20,m.u32(base+0x20)-2)
        r['eax']=m.u32(base+0x30);r['ebp']=(r['ebp']+r['eax'])&MASK
        if r['esi']:
            r['esi']=m.u32(base+0x5c)
            if signed(r['esi'])>0:r=self._pad(r,base,48,m.u32(base+0x30),0x614ed)
            r=self._put(r,48);r['edx']=r['ecx'];r['ebx']=(m.u32(base+0x20)-1-r['ebp'])&MASK
        else:
            r['ebx']=m.u32(base+0x5c)
            if signed(r['ebx'])>0:r=self._pad(r,base,48,m.u32(base+0x30),0x6167f)
            r['ebx']=(m.u32(base+0x20)-r['ebp'])&MASK
        r=self.f._call(r,base,'write',0x58750,0x616a4,[r['edi'],m.u32(base+0x50),m.u32(base+0x44)],reserve=4)
        r.update(esp=base,eflags=logical_flags(r['ebx'],add_flags(base-16,16,r['eflags'])))
        if signed(r['ebx'])>0:r=self._pad(r,base,32,r['ebx'],0x61557)
        return r

"""Pinned i386 printf formatter entry, literal and narrow-string output.

Follows glibc 2.39 stdio-common/vfprintf-internal.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Numeric formatting and remaining conversion
branches stay explicit unfinished source work. No host formatting,
expected text or later state is loaded.
"""
from .signal_install_storage import add_flags,subtract_flags
from .strchrnul_storage import StrchrnulStorage
from .strlen_storage import StrlenStorage
from .printf_buffer import PrintfBuffer
from .printf_padding import PrintfPadding
from .printf_integer import PrintfInteger
from .dispatch_storage import logical_flags
from .getline_bytes import cmp8

MASK=0xffffffff


class PrintfFormat:
    def __init__(self,file_storage,*,shr1_af):
        self.file=file_storage;self.m=file_storage.m;self.libc=file_storage.libc;self.got=file_storage.got;self.tls=file_storage.tls
        self.heap=file_storage.heap;self.children=file_storage.children
        self.strings=StrchrnulStorage(self.m,libc_base=self.libc);self.writer=PrintfBuffer(self.m,libc_base=self.libc,shr1_af=shr1_af)
        self.lengths=StrlenStorage(self.m,libc_base=self.libc,shr1_af=shr1_af);self.padding=PrintfPadding(file_storage)
        self.integers=PrintfInteger(self)

    def before_initial_write(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-1252
        if r['eip']!=self.libc+0x60530:raise NotImplementedError('Alternate printf formatter needs its source ABI')
        self.file._save4(r);buffer=m.u32(s+4);fmt=m.u32(s+8);args=m.u32(s+12);thread=m.u32(self.tls);errno_offset=m.u32(self.got+0xa0)
        errno=m.u32((thread+errno_offset)&0xffffffff)
        for offset,value in ((36,self.got),(24,args),(108,fmt),(1220,m.u32(self.tls+20)),(144,args),(116,errno_offset),(104,errno)):m.put_u32(local+offset,value)
        m.put_u32(local-4,37);m.put_u32(local-8,fmt);m.put_u32(local-12,self.libc+0x6059e)
        incoming=dict(r,eax=errno,ebp=self.got,esi=fmt,edi=buffer,ecx=thread,edx=args,esp=local-12,eip=self.libc+0xa3cb0,eflags=subtract_flags(s-16,1236,r['eflags']))
        r=self.file._child('strchrnul',incoming,self.strings.search);end=r['eax']
        m.put_u32(local+112,end);m.put_u32(local+140,end)
        for offset,value in ((0,end-fmt),(-4,fmt),(-8,buffer)):m.put_u32(local+offset,value)
        return dict(r,eax=(end-fmt)&0xffffffff,ebx=end,esp=local-8,eip=self.libc+0x605b3,eflags=subtract_flags(end,fmt,r['eflags']))

    def _write(self,registers):
        start=len(self.writer.children);result=self.writer.write(registers);self.children.extend(self.writer.children[start:]);return result

    def _call(self,r,base,kind,offset,return_offset,args,*,reserve=0):
        """Perform the actual caller stack reservation, PUSHes and CALL."""
        m=self.m;p=base-reserve
        if reserve:r=dict(r,eflags=subtract_flags(base,reserve,r['eflags']))
        for value in reversed(args):p-=4;m.put_u32(p,value)
        p-=4;m.put_u32(p,self.libc+return_offset)
        functions={'write':self._write,'strchrnul':self.strings.search,'strlen-ia32':self.lengths.length,'strnlen-ia32':self.lengths.bounded,'pad':self.padding.pad,'itoa-word':self.integers.digits.word}
        return self.file._child(kind,dict(r,esp=p,eip=self.libc+offset),functions[kind])

    def _read_int(self,r,base,slot,return_offset):
        """Native read_int uses EAX for its pointer-to-format argument."""
        m=self.m;s=base-4;m.put_u32(s,self.libc+return_offset);incoming=dict(r,eax=slot,esp=s);self.file._save4(incoming)
        p=m.u32(slot);number=m.read(p,1)[0]-48;p+=1;m.put_u32(slot,p);digit=(m.read(p,1)[0]-48)&MASK
        while digit<=9:
            if not number&0x80000000:
                if number>0x0ccccccc:number=MASK
                else:number=number*10+digit;number=number if number<=0x7fffffff else MASK
            p+=1;m.put_u32(slot,p);digit=(m.read(p,1)[0]-48)&MASK
        return self.file._return4(dict(incoming,eax=number,edx=number,ecx=p,eflags=subtract_flags(digit,9,r['eflags'])),s)

    def _dispatch(self,r,base,table_offset,*,first=False):
        m=self.m;code=r['edx']
        if not 32<=code<=122:raise NotImplementedError('Invalid printf conversion needs its source branch')
        r['eax']=m.read(code+r['ebp']-32,1)[0];got=m.u32(base+0x1c);r['esi']=m.u32(base+0x40)if first else got
        jump=m.u32(got+table_offset+4*r['eax']);r['ecx']=(jump+r['ebx'])&MASK;r['eflags']=add_flags(jump,r['ebx'],r['eflags'])
        return r

    def _parse(self,r,base):
        m=self.m
        while r['ecx']not in(self.libc+0x60ce0,self.libc+0x612c8,self.libc+0x612a0,self.libc+0x61240,self.libc+0x61180):
            handler=r['ecx']-self.libc
            if handler==0x60c00: # '-' flag, through the original first-step table.
                p=m.u32(base+0x84)+1;m.put_u32(base+0x84,p);r['edx']=m.read(p,1)[0];m.write(base+0x76,b' ');m.put_u32(base+0x18,1)
                r=self._dispatch(r,base,-0x72e34,first=True)
            elif handler in(0x60c98,0x60a90,0x60b30,0x60b80):
                if handler==0x60b30:
                    if not m.u32(base+0x18):m.write(base+0x76,b'0')
                else:m.put_u32(base+{0x60c98:0x24,0x60a90:0x2c,0x60b80:0x28}[handler],1)
                p=m.u32(base+0x84)+1;m.put_u32(base+0x84,p);r['edx']=m.read(p,1)[0]
                r=self._dispatch(r,base,-0x72e34,first=True)
            elif handler in(0x61328,0x61390,0x61438,0x60940,0x60944):
                p=m.u32(base+0x84)+1;m.put_u32(base+0x84,p);r['edx']=m.read(p,1)[0]
                if handler==0x61328:m.put_u32(base+0x30,1);table=-0x730b4
                elif handler==0x61390:m.put_u32(base+0x44,1);table=-0x72fb4
                else:
                    if handler==0x61438:m.put_u32(base+0x50,1);m.put_u32(base+0x44,0)
                    else:m.put_u32(base+0x30,0);m.put_u32(base,0)
                    table=-0x73034
                r=self._dispatch(r,base,table)
            elif handler==0x61000: # Literal decimal width.
                r=self._read_int(r,base,base+0x84,0x61010);m.put_u32(base+0x20,r['eax'])
                if r['eax']==MASK:raise NotImplementedError('Overflowing printf width needs its error source')
                r['edx']=m.read(m.u32(base+0x84),1)[0]
                if r['edx']==ord('$'):raise NotImplementedError('Positional printf arguments need their source branch')
                r=self._dispatch(r,base,-0x72eb4)
            elif handler==0x613d8: # Precision, with optional decimal digits.
                p=m.u32(base+0x84)+1;m.put_u32(base+0x84,p);r['edx']=m.read(p,1)[0];m.put_u32(base+0x14,0)
                if r['edx']==ord('*'):raise NotImplementedError('Variadic printf precision needs its source branch')
                if 48<=r['edx']<=57:
                    r=self._read_int(r,base,base+0x84,0x61f1f);m.put_u32(base+0x14,r['eax'])
                    if r['eax']==MASK:raise NotImplementedError('Overflowing printf precision needs its error source')
                    r['edx']=m.read(m.u32(base+0x84),1)[0]
                r=self._dispatch(r,base,-0x72f34)
            elif handler in(0x60788,0x6078c):raise NotImplementedError('Floating-point printf needs its original formatter source and produced FP state')
            else:raise NotImplementedError('Printf conversion parser and numeric formatter need their source implementation')
        return r

    def _string(self,r,base):
        m=self.m;args=m.u32(base+0x10);source=m.u32(args);r.update(esi=args,ebx=source,eax=(args+4)&MASK)
        if not source:raise NotImplementedError('Null printf string needs its source branch')
        r['ecx']=m.read(base+0x30,1)[0]^1;m.put_u32(base+0x10,r['eax'])
        if r['edx']==ord('S')or not r['ecx']:raise NotImplementedError('Wide printf string needs its source branch')
        precision=m.u32(base+0x14)
        if precision==MASK:r=self._call(r,base,'strlen-ia32',0xbc470,0x61d00,[source],reserve=12)
        else:r=self._call(r,base,'strnlen-ia32',0xbb390,0x6116f,[source,precision],reserve=8)
        r.update(esi=r['eax'],esp=base,eflags=add_flags(base-16,16,r['eflags']))
        length=r['esi'];width=m.u32(base+0x20);remaining=(width-length)&MASK;r['ebp']=remaining;r['eflags']=subtract_flags(width,length,r['eflags'])
        left=False;write_base=base;reserve=4
        if not remaining&0x80000000:
            r['eax']=m.u32(base+0x18);r['eflags']=logical_flags(r['eax'],r['eflags'])
            left=bool(r['eax'])
            if not left and remaining:
                r=self._call(r,base,'pad',0x58390,0x61ec6,[r['edi'],32,remaining],reserve=4)
                r['eflags']=add_flags(base-16,12,r['eflags']);write_base=base-4;reserve=0
        # 60d3c writes the actual argument bytes; no host string formatting.
        r=self._call(r,write_base,'write',0x58750,0x6195b if left else 0x60d47,[r['edi'],source,length],reserve=reserve)
        r.update(esp=base,eflags=add_flags(base-16,16,r['eflags']))
        if left:
            r['eflags']=logical_flags(r['ebp'],r['eflags'])
            if r['ebp']:
                r=self._call(r,base,'pad',0x58390,0x61972,[r['edi'],32,r['ebp']],reserve=4)
                r.update(esp=base,eflags=add_flags(base-16,16,r['eflags']))
        return r

    def _conversions(self,r,base):
        m=self.m;got=self.got;table=m.u32(got+0x19f8);m.put_u32(base+0x58,table)
        if table or m.u32(got+0x19ec)or m.u32(got+0x1a04):raise NotImplementedError('Registered printf handlers need their source branch')
        for offset,value in ((0x78,0),(0x34,0),(0x7c,MASK),(0x70,m.u32(got+0x16c))):m.put_u32(base+offset,value)
        while True:
            code=m.read(r['ebx']+1,1)[0];r.update(edx=code,eax=(r['ebx']+1)&MASK);m.put_u32(base+0x84,r['eax'])
            if not 32<=code<=122:raise NotImplementedError('Invalid printf conversion needs its source branch')
            r.update(ecx=m.u32(base+0x1c),ebp=got-0x72db4,esi=got-0x72e34)
            m.write(base+0x76,b' ');m.put_u32(base+0x3c,0);m.put_u32(base+0x14,MASK)
            r['eax']=m.read(code+r['ebp']-32,1)[0];r['ebx']=got-0x1cf7fb
            m.put_u32(base+0x40,r['esi']);m.put_u32(base+0x20,0)
            jump=m.u32(r['esi']+4*r['eax']);r['ecx']=(jump+r['ebx'])&MASK;r['eflags']=add_flags(jump,r['ebx'],r['eflags'])
            for offset in (0x50,0x30,0x44,0,0x38,0x24,0x18,0x2c,0x28):m.put_u32(base+offset,0)
            r=self._parse(r,base)
            r=self._string(r,base)if r['ecx']==self.libc+0x60ce0 else self.integers.convert(r,base)
            # 608a0: search and write the next literal span after conversion.
            r['eax']=m.u32(base+0x84);n=m.u32(base+0x34);m.put_u32(base+0x34,n+1)
            r['esi']=(r['eax']+1)&MASK
            r=self._call(r,base,'strchrnul',0xa3cb0,0x608ba,[r['esi'],37],reserve=8)
            # At 608bd ESP is still base-4: [esp+0x88] is base+0x84.
            end=r['eax'];m.put_u32(base+0x84,end);r['ebx']=end
            r['eax']=(end-r['esi'])&MASK;r['eflags']=subtract_flags(end,r['esi'],r['eflags'])
            # ADD esp,12 left one word of reservation before three PUSHes.
            r=self._call(r,base-4,'write',0x58750,0x608d0,[r['edi'],r['esi'],r['eax']])
            r.update(esp=base,eflags=cmp8(m.read(end,1)[0],0,add_flags(base-16,16,r['eflags'])))
            if not m.read(end,1)[0]:return r
            r['edx']=m.u32(r['edi']+20);r['eflags']=logical_flags(r['edx'],r['eflags'])
            if not r['edx']:return r

    def format(self,registers):
        m=self.m;r=self.before_initial_write(registers);s=registers['esp'];local=s-1252;buffer=r['edi'];end=r['ebx']
        m.put_u32(r['esp']-4,self.libc+0x605b8)
        incoming=dict(r,esp=r['esp']-4,eip=self.libc+0x58750)
        r=self.file._child('write',incoming,self._write)
        mode=m.u32(buffer+20)
        if mode and m.read(end,1)!=b'\0':r=self._conversions(r,local+8)
        if m.u32(local+1220)!=m.u32(self.tls+20):raise ValueError('Printf formatter stack canary mismatch')
        return self.file._return4(dict(r,eax=0,eflags=add_flags(local+8,1228,r['eflags'])),s)

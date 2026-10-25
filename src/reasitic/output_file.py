"""Pinned i386 modern FILE buffered output and allocation source.

Follows glibc 2.39 fileops.c, genops.c, filedoalloc.c and i386 mempcpy.S,
Copyright (C) Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Other output/error branches remain explicit.
"""
from .signal_install_storage import add_flags,subtract_flags
from .file_allocation import FileAllocation
from .malloc_top_storage import MallocTopStorage

MASK=0xffffffff


class OutputFile:
    def __init__(self,parent):
        self.p=parent;self.m=parent.m;self.libc=parent.libc;self.got=parent.got;self.tls=parent.tls

    def xsputn(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-44;file=m.u32(s+4);source=m.u32(s+8);count=m.u32(s+12)
        if r['eip']!=self.libc+0x83fc0:raise NotImplementedError('Alternate xsputn needs its source ABI')
        m.put_u32(s-4,self.libc+0x83fc9);self.p._save4(r)
        if not count:return self.p._return4(dict(r,eax=0,ecx=self.got,eflags=add_flags(local,28,r['eflags'])),s)
        # The first staged write has no available FILE output space. Direct
        # buffered writes use the parent's direct-buffer completion branch.
        if m.u32(file+20)<m.u32(file+24)or not(~m.u32(file)&0xa00):
            raise NotImplementedError('Xsputn existing-space/line-buffer branch needs its source ABI')
        vt=self.p.vtable(file)
        for offset,value in ((12,MASK),(16,file),(20,self.libc+0x840ab)):m.put_u32(local-offset,value)
        incoming=dict(r,eax=(vt-(self.got-0x734))&MASK,ebx=count,ecx=self.got,edx=self.got-0x734,esi=file,edi=count,ebp=vt,esp=local-20,eip=m.u32(vt+12),eflags=subtract_flags(local,8,r['eflags']))
        r=self.p._child('overflow',incoming,self.overflow)
        if r['eax']==MASK:raise NotImplementedError('Xsputn failed overflow needs its return branch')
        capacity=(m.u32(file+32)-m.u32(file+28))&MASK
        if capacity<=127 or count>=capacity:raise NotImplementedError('Xsputn direct stream writes need their source ABI')
        # The remainder uses _IO_default_xsputn (a direct internal call).
        for offset,value in ((8,count),(12,source),(16,file),(20,self.libc+0x840e1)):m.put_u32(local-offset,value)
        r=self.default_xsputn(dict(r,eax=count//capacity,edx=count%capacity,ecx=capacity,ebp=source,esp=local-20,eip=self.libc+0x85570,eflags=add_flags(0,source,subtract_flags(local,4,r['eflags']))))
        r.update(eax=(r['eax']-count+count)&MASK,eflags=add_flags(local,28,r['eflags']))
        return self.p._return4(r,s)

    def default_xsputn(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-44;file=m.u32(s+4);source=m.u32(s+8);count=m.u32(s+12)
        self.p._save4(r);m.put_u32(s-20,self.libc+0x8557f);m.put_u32(local+12,self.got);m.put_u32(local+8,self.got-0x734)
        destination=m.u32(file+20);capacity=(m.u32(file+24)-destination)&MASK
        if destination>=m.u32(file+24)or count>capacity:raise NotImplementedError('Default xsputn needs its overflow loop source')
        if count>20:
            m.put_u32(local+4,count);m.put_u32(local-8,count);m.put_u32(local-12,source);m.put_u32(local-16,destination);m.put_u32(local-20,self.libc+0x85657);m.put_u32(s+8,source)
            # Scalar mempcpy copies 1, 2, then 4-byte units; its final SHR
            # flags are overwritten by the caller's subsequent arithmetic.
            p,q=destination,source
            for width in ([1]if count&1 else[])+([2]if count&2 else[])+[4]*(count>>2):m.write(p,m.read(q,width));p+=width;q+=width
            edx=0;ecx=source+count
        else:
            m.put_u32(s+4,file)
            for index in range(count):m.write(destination+index,m.read(source+index,1))
            edx=0;ecx=source+count
        m.put_u32(file+20,destination+count)
        return self.p._return4(dict(r,eax=count,ecx=ecx,edx=edx,eflags=add_flags(local,28,r['eflags'])),s)

    def overflow(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-28;file=m.u32(s+4);ch=m.u32(s+8);flags=m.u32(file)
        if r['eip']!=self.libc+0x831f0:raise NotImplementedError('Alternate overflow needs its source ABI')
        m.put_u32(s-4,self.libc+0x831f9);self.p._save4(r)
        if flags&8 or ch!=MASK:raise NotImplementedError('Overflow error/character output needs its source ABI')
        if m.u32(file+16):raise NotImplementedError('Overflow existing-buffer transition needs its source ABI')
        m.put_u32(local-16,file);m.put_u32(local-20,self.libc+0x83389)
        r=self.p._child('doallocbuf',dict(r,eax=0,ebx=file,ecx=self.got,edx=flags,esi=ch,esp=local-20,eip=self.libc+0x85440,eflags=subtract_flags(local,12,r['eflags'])),self.doallocbuf)
        pointer=m.u32(file+28);flags=m.u32(file)
        if flags&0x100:raise NotImplementedError('Overflow backup area needs its free source ABI')
        end=m.u32(file+32)
        for offset,value in ((12,pointer),(4,pointer),(8,pointer),(20,pointer),(0,flags|0x800),(16,pointer),(24,end)):m.put_u32(file+offset,value)
        if m.u32(file+104)&0x80000000 and flags&0x202:m.put_u32(file+24,pointer)
        m.put_u32(local-8,0);m.put_u32(local-12,pointer);m.put_u32(local-16,file);m.put_u32(local-20,self.libc+0x832db)
        # _IO_do_write is a tail return of zero when to_do is zero.
        return self.p._return4(dict(r,eax=0,ecx=ch,edx=pointer,eflags=add_flags(local,12,r['eflags'])),s)

    def doallocbuf(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-28;file=m.u32(s+4);self.p._save4(r);m.put_u32(s-20,self.libc+0x8544d)
        if m.u32(file+28)or(m.u32(file)&2 and (m.u32(file+104)==0 or m.u32(file+104)&0x80000000)):
            raise NotImplementedError('Doallocbuf existing/unbuffered path needs its source ABI')
        vt=self.p.vtable(file);m.put_u32(local-16,file);m.put_u32(local-20,self.libc+0x854a0)
        incoming=dict(r,eax=(vt-(self.got-0x734))&MASK,ebx=self.got,ecx=0,edx=self.got-0x734,esi=file,edi=vt,esp=local-20,eip=m.u32(vt+52),eflags=subtract_flags(local,12,r['eflags']))
        r=self.p._child('doallocate',incoming,self.doallocate)
        if r['eax']==MASK:raise NotImplementedError('Doallocbuf fallback allocation needs its source ABI')
        return self.p._return4(dict(r,eflags=add_flags(local,12,r['eflags'])),s)

    def doallocate(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];local=s-140;file=m.u32(s+4)
        if r['eip']!=self.libc+0x75490:raise NotImplementedError('Alternate doallocate needs its source ABI')
        self.p._save4(r);m.put_u32(local+108,m.u32(self.tls+20));vt=self.p.vtable(file)
        if m.u32(file+56)&0x80000000:raise NotImplementedError('Doallocate invalid descriptor needs its source ABI')
        m.put_u32(local-12,local);m.put_u32(local-16,file);m.put_u32(local-20,self.libc+0x754f0)
        incoming=dict(r,eax=local,ebx=vt,ecx=0,edx=self.got-0x734,esi=file,edi=self.got,esp=local-20,eip=m.u32(vt+72),eflags=subtract_flags(local,8,r['eflags']))
        r=self.p._child('file-stat',incoming,self.file_stat)
        mode=m.u32(local+16)&0xf000;block=m.u32(local+48)
        if mode==0x2000:raise NotImplementedError('Doallocate terminal detection needs its source ABI')
        size=block if 1<=block<=8191 else 8192
        m.put_u32(local-16,size);m.put_u32(local-20,self.libc+0x75523)
        incoming=dict(r,eax=(block-1)&MASK,ebx=self.got,ebp=size,esp=local-20,eflags=subtract_flags(local,12,r['eflags']))
        if self.p.io is None or self.p.heap is None:raise ValueError('Staged allocation needs the earlier loader and continuing heap')
        target=m.u32(self.got+0x1c4)
        if target!=self.libc+0x9ea00:
            io=self.p.io;main=io.context['main_map'];plt=next(x['plt']for x in io.context['maps']if x['address']==main)
            rel=io.loader._dynamic(main,23);sym=io.loader._dynamic(main,6);strings=io.loader._dynamic(main,5)
            info=m.u32(main+40);rel_size=m.u32(info+4)
            for offset in range(0,rel_size,8):
                symbol=sym+16*(m.u32(rel+offset+4)>>8)
                if io.loader._string(strings+m.u32(symbol))==b'malloc':
                    if target!=plt['address']+16*(offset//8+1):raise NotImplementedError('Interposed malloc needs its source ABI')
                    incoming=io._bind(incoming,b'malloc');break
            else:raise ValueError('Canonical malloc import was not found')
        else:incoming['eip']=target
        r=self.p._child('malloc',incoming,MallocTopStorage(self.p.heap,m,libc_base=self.libc,tls_base=self.tls).malloc)
        pointer=r['eax'];end=(pointer+size)&MASK
        if not pointer:raise NotImplementedError('Doallocate malloc failure needs its source ABI')
        for offset,value in ((4,1),(8,end),(12,pointer),(16,file),(20,self.libc+0x7553a)):m.put_u32(local-offset,value)
        incoming=dict(r,ebp=end,esp=local-20,eip=self.libc+0x853e0,eflags=add_flags(size,pointer,r['eflags']))
        r=self.p._child('setb',incoming,self.setb)
        if m.u32(local+108)!=m.u32(self.tls+20):raise ValueError('Doallocate stack canary mismatch')
        return self.p._return4(dict(r,eax=1,edx=0,eflags=add_flags(local,124,r['eflags'])),s)

    def file_stat(self,registers):
        if registers['eip']!=self.libc+0x83eb0:raise NotImplementedError('Alternate file stat needs its source ABI')
        m=self.m;s=registers['esp']
        if self.p.io is None:raise ValueError('File stat needs earlier external descriptor facts')
        FileAllocation(self.p.io)._stat(registers,m.u32(s+8))
        return dict(registers,eax=0,ecx=0,edx=0,esp=s+4,eip=m.u32(s),eflags=add_flags(s-12,12,registers['eflags']))

    def setb(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];file=m.u32(s+4);flags=m.u32(file);old=m.u32(file+28)
        if old and not flags&1:raise NotImplementedError('Setb replacing an owned buffer needs free source ABI')
        m.put_u32(s-4,r['esi']);m.put_u32(s-8,r['ebx']);m.put_u32(s-12,self.libc+0x853eb)
        m.put_u32(file+28,m.u32(s+8));m.put_u32(file+32,m.u32(s+12));allocate=m.u32(s+16);new=(flags&~1)if allocate else(flags|1);m.put_u32(file,new)
        return dict(r,eax=new,edx=flags&~1,ecx=allocate,ebx=m.u32(s-8),esi=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(s-12,4,r['eflags']))

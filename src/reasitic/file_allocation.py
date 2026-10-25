"""Source i386 stdio stat/allocation callers, without host syscalls.

Follows glibc 2.39 filedoalloc.c, genops.c and Linux fstat/fstatat wrappers,
Copyright (C) 1993-2024 Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Linux statx encodings use named earlier file facts.
The malloc implementation's own register/stack ABI remains separate work.
"""
import struct
from .signal_install_storage import add_flags,subtract_flags


def statx_image(profile):
    """Linux's 256-byte statx record, including its defined zero padding."""
    if profile['query_mask']!=0x7ff:raise NotImplementedError('Additional statx request masks need their metadata')
    fields=profile['fields'];out=bytearray(256)
    for name,offset,fmt in (('mask',0,'I'),('blksize',4,'I'),('attributes',8,'Q'),('nlink',16,'I'),('uid',20,'I'),('gid',24,'I'),('mode',28,'H'),('ino',32,'Q'),('size',40,'Q'),('blocks',48,'Q'),('attributes_mask',56,'Q'),('rdev_major',128,'I'),('rdev_minor',132,'I'),('dev_major',136,'I'),('dev_minor',140,'I'),('mnt_id',144,'Q'),('dio_mem_align',152,'I'),('dio_offset_align',156,'I')):
        struct.pack_into('<'+fmt,out,offset,fields[name])
    for name,offset in (('atime',64),('btime',80),('ctime',96),('mtime',112)):
        sec,nsec=fields[name]['sec'],fields[name]['nsec']
        if not 0<=nsec<10**9:raise ValueError('Invalid statx nanoseconds')
        struct.pack_into('<qI',out,offset,sec,nsec)
    return bytes(out)


def device(major,minor):
    return(minor&255)|((major&4095)<<8)|((minor&~255)<<12)|((major&~4095)<<32)


def stat64_image(profile):
    """The libc converter's zeroed 108-byte __stat64_t64 result."""
    x=profile['fields'];out=bytearray(108)
    for offset,fmt,value in ((0,'Q',device(x['dev_major'],x['dev_minor'])),(8,'Q',x['ino']),(16,'I',x['mode']),
        (20,'I',x['nlink']),(24,'I',x['uid']),(28,'I',x['gid']),(32,'Q',device(x['rdev_major'],x['rdev_minor'])),
        (40,'Q',x['size']),(48,'I',x['blksize']),(52,'Q',x['blocks'])):struct.pack_into('<'+fmt,out,offset,value)
    for name,offset in (('atime',60),('mtime',76),('ctime',92)):
        struct.pack_into('<qI',out,offset,x[name]['sec'],x[name]['nsec'])
    return bytes(out)


class FileAllocation:
    def __init__(self,io):self.io=io;self.m=io.m;self.libc=io.libc;self.got=io.got;self.tls=io.tls

    def before_malloc(self,registers):
        m=self.m;io=self.io;r=dict(registers);s=r['esp'];a=m.u32(s+4);vt=m.u32(a+148)
        if r['eflags']&0x400 or m.u32(a+28)or m.u32(a+56)!=0:raise NotImplementedError('File allocation needs empty-buffer stdin and forward copies')
        # _IO_doallocbuf and its accepted foreign-vtable callback.
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(s-20,self.libc+0x8544d);local=s-28
        r.update(ebx=self.got,esi=a,edi=vt,ecx=0,esp=local)
        r=io._guard(r,self.libc+0x854f5)
        if m.u32(vt+52)!=io.legacy_base+0x220b4:raise NotImplementedError('File doallocate vtable branch is not bound')
        m.put_u32(local-16,a);m.put_u32(local-20,self.libc+0x854a0);r['esp']=local-20
        r=io._wrapper(r,0x220b4,0x1cafb,b'_IO_file_doallocate',[a])
        if r['eip']!=self.libc+0x75490:raise NotImplementedError('File doallocate interposition is not bound')
        entry=r['esp'];alloc=entry-140;self.entry=dict(registers);self.alloc_local=alloc
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(entry-offset,r[key])
        m.put_u32(alloc+108,m.u32(self.tls+20))
        r.update(edi=self.got,esi=a,ebx=vt,esp=alloc)
        r=io._guard(r,self.libc+0x75605)
        m.put_u32(alloc-12,alloc);m.put_u32(alloc-16,a);m.put_u32(alloc-20,self.libc+0x754f0);r.update(eax=alloc,esp=alloc-20)
        if m.u32(vt+72)!=io.legacy_base+0x22208:raise NotImplementedError('File stat vtable branch is not bound')
        r=io._wrapper(r,0x22208,0x1c9a7,b'_IO_file_stat',[a,alloc])
        if r['eip']!=self.libc+0x83eb0:raise NotImplementedError('File stat interposition is not bound')
        self._stat(r,alloc)
        block=m.u32(alloc+48);size=block;mode=m.u32(alloc+16)
        if mode&0xf000!=0x8000:raise NotImplementedError('TTY/nonregular allocation needs its separate branch')
        if not 1<=size<=8191:size=8192
        if size!=io.buffer_size:raise ValueError('Conflicting earlier file block sizes')
        m.put_u32(alloc-16,size);m.put_u32(alloc-20,self.libc+0x75523)
        r.update(eax=(block-1)&0xffffffff,ebx=self.got,ecx=0,edx=0,esi=a,edi=self.got,ebp=size,esp=alloc-20,
            eflags=subtract_flags(alloc,12,r['eflags']))
        # This libc call uses .plt.got's bound GLOB_DAT slot, not JMPREL.
        target=m.u32(self.got+0x1c4)
        if target==self.libc+0x9ea00:return dict(r,eip=target)
        # ELF's canonical function address can be the executable's PLT entry.
        # Follow that real tail jump through its earlier relocation/GOT state.
        main=io.context['main_map'];plt=next(x['plt']for x in io.context['maps']if x['address']==main)
        rel=io.loader._dynamic(main,23);sym=io.loader._dynamic(main,6);strings=io.loader._dynamic(main,5)
        info=m.u32(main+32+8);size=m.u32(info+4)
        for offset in range(0,size,8):
            symbol=sym+16*(m.u32(rel+offset+4)>>8)
            if io.loader._string(strings+m.u32(symbol))==b'malloc':
                if target!=plt['address']+16*(offset//8+1):break
                return io._bind(r,b'malloc')
        raise NotImplementedError('Interposed malloc needs its own caller ABI')

    def _stat(self,registers,destination):
        m=self.m;io=self.io;s=registers['esp'];fd=m.u32(m.u32(s+4)+56)
        if fd!=io.profile.get('fd',0):raise ValueError('Stat descriptor differs from the earlier external file facts')
        # _IO_file_stat tail call, __fstat64_time64 and fstatat's local frame.
        m.put_u32(s+4,fd);m.put_u32(s-4,self.libc+0x10be09);f=s-12
        for offset,value in ((4,0x1000),(8,destination),(12,self.got-0x6c3a6),(16,fd),(20,self.libc+0x10be30)):
            m.put_u32(f-offset,value)
        entry=f-20;local=entry-428
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(entry-offset,registers[key])
        m.put_u32(local+8,self.got);m.put_u32(local+396,m.u32(self.tls+20))
        sysinfo=m.u32(self.tls+16)
        prefixes=('51525589e50f34cd805d5a59c3','0f1f0051525589cd0f05cd805d5a59c3')
        if not any(m.read(sysinfo,len(bytes.fromhex(p)))==bytes.fromhex(p)for p in prefixes):
            raise NotImplementedError('Statx needs a supported i386 VDSO entry ABI')
        # VDSO's call return and three pushes survive its normal return.
        for offset,value in ((4,self.libc+0x10c162),(8,self.got-0x6c3a6),(12,0x1800),(16,destination)):
            m.put_u32(local-offset,value)
        profile=io.profile['statx'];image=statx_image(profile);m.write(local+140,image)
        x=profile['fields']
        for offset,value in ((8,((x['dev_major']<<8)&0xfff00)|(x['dev_minor']&255)),(12,x['dev_major']&0xfffff000),
            (20,x['mode']),(24,((x['rdev_major']<<8)&0xfff00)|(x['rdev_minor']&255)),(28,x['rdev_major']&0xfffff000)):
            m.put_u32(local+offset,value)
        m.write(destination,stat64_image(profile))

    def after_malloc(self,registers):
        """Post-malloc entry through _IO_setb and doallocbuf's caller return."""
        m=self.m;io=self.io;alloc=registers['esp']+16;a=registers['esi'];buffer=registers['eax'];end=buffer+registers['ebp']
        if m.u32(a+28):raise NotImplementedError('Replacing an existing owned buffer needs free ABI stores')
        for offset,value in ((4,1),(8,end),(12,buffer),(16,a),(20,self.libc+0x7553a)):m.put_u32(alloc-offset,value)
        s=alloc-20;m.put_u32(s-4,registers['esi']);m.put_u32(s-8,registers['ebx']);m.put_u32(s-12,self.libc+0x853eb)
        m.put_u32(a+28,buffer);m.put_u32(a+32,end);m.put_u32(a,m.u32(a)&~1)
        # Successful canary comparison, epilogue, legacy wrapper and parent.
        entry=alloc+140;wrapper_frame=m.u32(entry-4);doalloc_entry=wrapper_frame+52
        result=dict(registers,eax=1,ecx=1,edx=0,esp=doalloc_entry+4,eip=m.u32(doalloc_entry),
            ebp=m.u32(doalloc_entry-4),edi=m.u32(doalloc_entry-8),esi=m.u32(doalloc_entry-12),ebx=m.u32(doalloc_entry-16),
            eflags=add_flags(doalloc_entry-28,12,registers['eflags']))
        return result

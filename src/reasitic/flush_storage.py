"""Successful pinned i386 fflush/sync/write source on guest Memory.

Follows glibc 2.39 iofflush.c/fileops.c/write.c and legacy libio wrappers,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. Writes go to a virtual sink,
never a host descriptor. Partial/error writes and read-side seeks remain
separate paths; no observed native return supplies a successful byte count.
"""
from .libio_abi import LibioABI
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags


class FlushStorage(LibioABI):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.writes=[]

    def _save4(self,r):
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):self.m.put_u32(r['esp']-offset,r[key])

    def _return4(self,r,entry):
        m=self.m
        return dict(r,ebp=m.u32(entry-4),edi=m.u32(entry-8),esi=m.u32(entry-12),ebx=m.u32(entry-16),esp=entry+4,eip=m.u32(entry))

    def _legacy_return(self,r):
        m=self.m;f=r['ebp']
        return dict(r,ebx=m.u32(f-4),ebp=m.u32(f),esp=f+8,eip=m.u32(f+4))

    def _vtable(self,r,vt,return_offset):
        difference=(vt-(self.got-0x734))&0xffffffff
        if difference>0x593:r=self._guard(r,self.libc+return_offset)
        return r

    def flush(self,registers):
        m=self.m;r=dict(registers);s=r['esp'];a=m.u32(s+4)
        if r['eip']!=self.libc+0x75b80:raise NotImplementedError('Alternate fflush needs its source ABI')
        if not a:raise NotImplementedError('Flush-all needs the complete stream-list traversal')
        if m.u32(self.tls+12):raise NotImplementedError('Multithread fflush needs its lock ABI')
        self._save4(r);f=s-4;local=f-24;lock=m.u32(a+72);user_locked=bool(m.u32(a)&0x8000)
        r.update(ebp=f,edi=self.got,esi=a)
        if not user_locked:
            owner=m.u32(lock+8);thread=m.u32(self.tls+8)
            if not owner:m.put_u32(lock,1);m.put_u32(lock+8,thread)
            elif owner==thread:m.put_u32(lock+4,m.u32(lock+4)+1)
            else:raise NotImplementedError('Contended fflush needs its lock wait')
            r.update(ebx=thread,ecx=0,edx=lock)
        offset=int.from_bytes(m.read(a+70,1),'little',signed=True);vt=m.u32(a+148+offset)
        r.update(eax=(vt-(self.got-0x734))&0xffffffff,ebx=vt,edx=self.got-0x734,esp=local)
        r=self._vtable(r,vt,0x75cc5)
        m.put_u32(local-16,a);m.put_u32(local-20,self.libc+0x75bd2)
        r.update(esp=local-20,eflags=subtract_flags(local,12,r['eflags']))
        target=m.u32(vt+48)
        if self.legacy_base is not None and target==self.legacy_base+0x22114:
            r=self._wrapper(r,0x22114,0x1ca9b,b'_IO_file_sync',[a]);r=self._sync(r);r=self._legacy_return(r)
        elif target==self.libc+0x833f0:r=self._sync(dict(r,eip=target))
        else:raise NotImplementedError('Stream sync callback needs its own source')
        if r['eax']:raise NotImplementedError('fflush error return needs its errno path')
        r.update(eax=0,ebx=0,eflags=logical_flags(m.u32(a)&0x8000,r['eflags']))
        if not user_locked:
            depth=m.u32(lock+4);r.update(ecx=0,edx=lock)
            if depth:m.put_u32(lock+4,depth-1);r['eflags']=subtract_flags(depth,1,r['eflags'])
            else:
                m.put_u32(lock+8,0);m.put_u32(lock,0);r['eflags']=logical_flags(0,r['eflags'])
        return self._return4(r,s)

    def _sync(self,r):
        m=self.m;s=r['esp'];a=m.u32(s+4);local=s-28
        if r['eip']!=self.libc+0x833f0:raise NotImplementedError('Interposed file sync needs its own source')
        for offset,key in ((4,'edi'),(8,'esi'),(12,'ebx')):m.put_u32(s-offset,r[key])
        r=dict(r,esi=self.got,ebx=a,eax=m.u32(a+20),edx=m.u32(a+16))
        if r['eax']>r['edx']:
            mode=m.u32(a+104)
            if mode and mode<0x80000000:raise NotImplementedError('Wide stream sync needs its wide write ABI')
            count=r['eax']-r['edx']
            for offset,value in ((8,count),(12,r['edx']),(16,a),(20,self.libc+0x8349d)):m.put_u32(local-offset,value)
            r.update(ecx=mode,eax=count,esp=local-20,eip=self.libc+0x82da0)
            r=self._do_write(r)
        if m.u32(a+4)!=m.u32(a+8):raise NotImplementedError('Unread input sync needs its seek syscall')
        m.write(a+76,b'\xff'*8)
        return dict(r,eax=0,ebx=m.u32(s-12),esi=m.u32(s-8),edi=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(local,16,r['eflags']))

    def _do_write(self,r):
        m=self.m;s=r['esp'];local=s-12;a=m.u32(s+4);buffer=m.u32(s+8);count=m.u32(s+12)
        m.put_u32(s-4,r['ebx']);r=dict(r,ebx=count,eax=a,edx=buffer,ecx=count)
        if count:
            m.put_u32(local-4,self.libc+0x82dcf);r.update(esp=local-4,eip=self.libc+0x81cd0)
            r=self._write_buffer(r)
            if r['eax']!=count:raise NotImplementedError('Short buffered write needs its retry path')
        return dict(r,eax=0,ebx=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=logical_flags(0,r['eflags']))

    def _write_buffer(self,r):
        m=self.m;s=r['esp'];a=r['eax'];buffer=r['edx'];count=r['ecx'];local=s-44
        self._save4(r);m.put_u32(local+8,count)
        offset=int.from_bytes(m.read(a+70,1),'little',signed=True);vt=m.u32(a+148+offset)
        r=dict(r,ebx=a,esi=vt,edi=buffer,ebp=self.got-0x734,ecx=vt,edx=offset&0xffffffff,esp=local)
        if m.u32(a)&0x1000:m.write(a+76,b'\xff'*8)
        elif m.u32(a+8)!=m.u32(a+16):raise NotImplementedError('Buffered write needs its read/write seek transition')
        r.update(eax=(vt-(self.got-0x734))&0xffffffff);r=self._vtable(r,vt,0x81df5)
        for off,value in ((8,count),(12,buffer),(16,a),(20,self.libc+0x81d33)):m.put_u32(local-off,value)
        r.update(esp=local-20,eflags=subtract_flags(local,4,r['eflags']))
        target=m.u32(vt+60)
        if self.legacy_base is not None and target==self.legacy_base+0x221e4:
            r=self._wrapper(r,0x221e4,0x1c9cb,b'_IO_file_write',[a,buffer,count]);r=self._file_write(r);r=self._legacy_return(r)
        elif target==self.libc+0x83f30:r=self._file_write(dict(r,eip=target))
        else:raise NotImplementedError('File write callback needs its own source')
        if int.from_bytes(m.read(a+68,2),'little'):raise NotImplementedError('Column adjustment needs its child scan ABI')
        bb=m.u32(a+28)
        for off in (4,8,12,16,20):m.put_u32(a+off,bb)
        mode=m.u32(a+104);end=bb if (mode==0 or mode&0x80000000)and m.u32(a)&0x202 else m.u32(a+32);m.put_u32(a+24,end)
        r.update(eax=count,edx=mode,eflags=add_flags(local,28,r['eflags']))
        return self._return4(r,s)

    def _file_write(self,r):
        m=self.m;s=r['esp'];a=m.u32(s+4);buffer=m.u32(s+8);count=m.u32(s+12);local=s-28
        if r['eip']!=self.libc+0x83f30:raise NotImplementedError('Interposed file write needs its own source')
        if not 0<count<=4096:raise NotImplementedError('File write model needs a positive full-write chunk at most PIPE_BUF')
        if m.read(a+60,1)[0]&2:raise NotImplementedError('Noncancellable write needs its separate syscall ABI')
        self._save4(r)
        for off,value in ((8,count),(12,buffer),(16,m.u32(a+56)),(20,self.libc+0x83f5b)):m.put_u32(local-off,value)
        write=dict(r,eax=m.u32(a+56),ebp=a,esi=count,edi=buffer,ebx=count,esp=local-20)
        r=self._write_syscall(write)
        low=m.u32(a+76);high=m.u32(a+80)
        if not high&0x80000000:
            next_offset=(((high<<32)|low)+count)&0xffffffffffffffff;m.write(a+76,next_offset.to_bytes(8,'little'));r['ecx']=next_offset&0xffffffff
        r.update(eax=count,edx=high,eflags=add_flags(local,12,r['eflags']))
        return self._return4(r,s)

    def _write_syscall(self,r):
        m=self.m;s=r['esp'];local=s-28;fd=m.u32(s+4);buffer=m.u32(s+8);count=m.u32(s+12)
        sysinfo=m.u32(self.tls+16);prefixes=('51525589e50f34cd805d5a59c3','0f1f0051525589cd0f05cd805d5a59c3')
        if not any(m.read(sysinfo,len(bytes.fromhex(p)))==bytes.fromhex(p)for p in prefixes):raise NotImplementedError('Write needs its i386 VDSO ABI')
        for off,key in ((4,'edi'),(8,'esi'),(12,'ebx')):m.put_u32(s-off,r[key])
        for off,value in ((4,self.libc+0x117b17),(8,buffer),(12,count),(16,r['ebp'])):m.put_u32(local-off,value)
        self.writes.append(dict(fd=fd,address=buffer,count=count,data=m.read(buffer,count).hex(),returned=count))
        return dict(r,eax=count,ecx=buffer,edx=count,esp=s+4,eip=m.u32(s),eflags=add_flags(local,16,r['eflags']))

"""Pinned i386 buffered-input seek, with virtual regular-file positions.

Follows glibc 2.39 fileops.c/lseek64.c and its i386 VDSO call ABI,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. No host descriptor is sought.
Offsets, FILEs, TLS and current descriptor positions are earlier source state.
"""
from .signal_install_storage import add_flags,subtract_flags


class SeekStorage:
    def __init__(self,memory,*,libc_base,tls_base,positions,observe=None):
        self.m=memory;self.libc=libc_base;self.tls=tls_base;self.got=libc_base+0x22fe34;self.positions=positions
        self.observe=observe

    def point(self,phase,kind,r):
        if self.observe is not None:self.observe(phase,kind,r,self.positions)

    def llseek(self,registers):
        self.point('before','llseek',registers)
        m=self.m;r=dict(registers);s=r['esp'];local=s-44
        if r['eip']!=self.libc+0x115600:raise NotImplementedError('Alternate llseek needs its source ABI')
        fd,low,high,whence=(m.u32(s+i)for i in(4,8,12,16))
        if fd not in self.positions or whence!=1:raise NotImplementedError('Seek needs an earlier regular-file descriptor position and SEEK_CUR')
        offset=low+(high<<32)
        if offset>>63:offset-=1<<64
        target=self.positions[fd]+offset
        if not 0<=target<=0x7fffffffffffffff:raise NotImplementedError('Failed or overflowing seek needs its errno ABI')
        sysinfo=m.u32(self.tls+16)
        prefixes=('51525589e50f34cd805d5a59c3','0f1f0051525589cd0f05cd805d5a59c3')
        if not any(m.read(sysinfo,len(bytes.fromhex(p)))==bytes.fromhex(p)for p in prefixes):raise NotImplementedError('Seek needs the i386 VDSO ABI')
        for offset,key in((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(local+12,m.u32(self.tls+20))
        for offset,value in((4,self.libc+0x115640),(8,high),(12,low),(16,self.got)):m.put_u32(local-offset,value)
        m.write(local,target.to_bytes(8,'little'));self.positions[fd]=target
        result=dict(r,eax=target&0xffffffff,edx=target>>32,ecx=0,esp=s+4,eip=m.u32(s),
                    eflags=add_flags(local,28,subtract_flags(m.u32(local+12),m.u32(self.tls+20),r['eflags'])))
        for offset,key in((16,'ebx'),(12,'esi'),(8,'edi'),(4,'ebp')):result[key]=m.u32(s-offset)
        self.point('after','llseek',result);return result

    def file_seek(self,registers):
        self.point('before','file_seek',registers)
        m=self.m;r=dict(registers);s=r['esp'];file=m.u32(s+4)
        if r['eip']!=self.libc+0x83e80:raise NotImplementedError('Alternate file seek needs its source ABI')
        low,high,whence=(m.u32(s+i)for i in(8,12,16));m.put_u32(s-4,r['ebx']);m.put_u32(s-8,self.libc+0x83e8a)
        for offset,value in((16,whence),(20,high),(24,low),(28,m.u32(file+56)),(32,self.libc+0x83eab)):m.put_u32(s-offset,value)
        r.update(eax=file,ebx=self.got,esp=s-32,eip=self.libc+0x115600,
                 eflags=subtract_flags(s-4,8,add_flags(self.libc+0x83e8a,0x1abfaa,r['eflags'])))
        r=self.llseek(r)
        result=dict(r,ebx=m.u32(s-4),esp=s+4,eip=m.u32(s),eflags=add_flags(s-28,24,r['eflags']))
        self.point('after','file_seek',result);return result

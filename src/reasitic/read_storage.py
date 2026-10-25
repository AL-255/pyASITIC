"""Source i386 regular-file read and libc/VDSO caller stores.

Follows glibc 2.39 fileops.c/read.c and the i386 syscall ABI,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt. External bytes and descriptor
position are earlier inputs. No host file or system call is performed.
"""
from .signal_install_storage import add_flags


class ReadStorage:
    def __init__(self,memory,*,libc_base,tls_base):
        self.m=memory;self.libc=libc_base;self.tls=tls_base;self.got=libc_base+0x22fe34

    def read(self,registers,file_data,position):
        m=self.m;r=dict(registers);s=r['esp'];file=m.u32(s+4);buffer=m.u32(s+8);capacity=m.u32(s+12)
        if r['eip']!=self.libc+0x83e40:raise NotImplementedError('File read interposition needs its source ABI')
        if m.u32(file+56)!=0:raise NotImplementedError('Read input facts describe stdin only')
        if m.read(file+60,1)[0]&2:raise NotImplementedError('Noncancellable file read needs its separate ABI')
        if m.u32(self.tls+12):raise NotImplementedError('Multithread read needs cancellation ABI')
        if isinstance(position,bool)or not isinstance(position,int)or position<0:raise ValueError('Invalid regular-file descriptor position')
        if capacity>0x7ffff000:raise NotImplementedError('Oversized read needs Linux MAX_RW_COUNT handling')
        sysinfo=m.u32(self.tls+16)
        prefixes=('51525589e50f34cd805d5a59c3','0f1f0051525589cd0f05cd805d5a59c3')
        if not any(m.read(sysinfo,len(bytes.fromhex(p)))==bytes.fromhex(p)for p in prefixes):
            raise NotImplementedError('Read needs a supported i386 VDSO entry ABI')
        # _IO_file_read tail-calls __read with the actual descriptor argument.
        m.put_u32(s+4,0)
        for offset,key in ((4,'edi'),(8,'esi'),(12,'ebx')):m.put_u32(s-offset,r[key])
        local=s-28
        for offset,value in ((4,self.libc+0x116937),(8,buffer),(12,capacity),(16,r['ebp'])):
            m.put_u32(local-offset,value)
        # A regular-file read changes only the returned byte range and offset.
        data=bytes(file_data)[position:position+capacity];m.write(buffer,data)
        result=dict(r,eax=len(data),ecx=buffer,edx=capacity,esp=s+4,eip=m.u32(s),
                    eflags=add_flags(local,16,r['eflags']))
        return dict(data=data,position=position+len(data),registers=result)

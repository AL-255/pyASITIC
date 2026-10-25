"""Pinned i386 select64 timeout conversion and syscall dispatch stores.

Follows glibc 2.39 select.c, LGPL-2.1-or-later; see the bundled license.
No kernel call or later timeout/result is performed or supplied here.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags

MASK=0xffffffff


def select64_dispatch(memory,registers,*,libc_base,tls_base):
    """Execute select64 up to its syscall helper, or its EINVAL return.

    Single-threaded execution uses the actual i386 time32/time64 dispatch.
    Cancellation, the kernel result and post-syscall copyback remain separate
    operations. All operands and addresses come from the earlier guest state.
    """
    m=memory;r=dict(registers);s=r['esp'];local=s-124;got=libc_base+0x22fe34
    if r['eip']!=libc_base+0x120f90:raise ValueError('select64 dispatch needs its actual entry PC')
    for offset,key in((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
    m.put_u32(local+28,got)
    nfds,readfds,writefds,exceptfds,timeout=(m.u32(s+i)for i in(4,8,12,16,20))
    m.put_u32(local+8,readfds);m.put_u32(local+12,writefds);m.put_u32(local+24,exceptfds)
    guard=m.u32(tls_base+20);m.put_u32(local+92,guard)
    r.update(eax=0,ebx=timeout)
    wide=False
    if timeout:
        low,high,usec=(m.u32(timeout+i)for i in(0,4,8));r.update(eax=low,edx=high,ecx=usec)
        m.put_u32(local+16,low);m.put_u32(local+20,high)
        if high&0x80000000 or usec&0x80000000:
            # Invalid signed seconds/microseconds return before any syscall.
            offset=m.u32(got+0xa0);r['edx']=m.u32(tls_base)
            m.put_u32((r['edx']+offset)&MASK,22)
            r.update(eax=MASK,esp=s+4,eip=m.u32(s),eflags=add_flags(local,108,r['eflags']))
            for offset,key in((16,'ebx'),(12,'esi'),(8,'edi'),(4,'ebp')):r[key]=m.u32(s-offset)
            return r
        # The signed multiply by 0x431bde83 followed by SAR 18 computes
        # usec / 1000000. Intermediate undefined flags do not survive the
        # later TLS TEST at either syscall path.
        quotient=((usec*0x431bde83)>>32)>>18
        r.update(ebp=quotient,edi=0)
        m.put_u32(local+32,quotient);m.put_u32(local+36,0)
        seconds=low+(high<<32)
        if seconds+quotient>0x7fffffffffffffff:
            # The source saturates the timespec on signed time64 overflow.
            for offset,value in((76,MASK),(80,0x7fffffff),(84,999999999)):m.put_u32(local+offset,value)
            r['esi']=local+76;wide=True
        else:
            total=seconds+quotient;total_low=total&MASK;total_high=total>>32
            sign=MASK if low&0x80000000 else 0;nsec=(usec-quotient*1000000)*1000
            for offset,value in((40,low),(32,total_low),(76,total_low),(36,total_high),(80,total_high),(44,sign),(84,nsec)):m.put_u32(local+offset,value)
            wide=high!=sign
            if wide:r['esi']=local+76
            else:
                r['esi']=local+56;r['ebp']=r['esi']
                m.put_u32(local+60,nsec);m.put_u32(local+56,total_low)
    else:r.update(ebp=0,esi=0)
    multiple=m.u32(tls_base+12)
    if multiple:raise NotImplementedError('Multithread select64 needs its cancellation source')
    r['eax']=multiple;r['eflags']=logical_flags(multiple,r['eflags'])
    r.update(ecx=m.u32(local+8),edx=m.u32(local+12))
    m.put_u32(local+68,r['esi']);r['edi']=local+64
    m.put_u32(local+72,0);m.put_u32(local+64,nfds)
    r['esi']=m.u32(local+24);r['eax']=413 if wide else 308
    return_pc=libc_base+(0x12109e if wide else 0x12113f)
    m.put_u32(local-4,return_pc);r.update(esp=local-4,eip=libc_base+0x117bb0)
    return r


def select_syscall_entry(memory,registers,*,libc_base,tls_base):
    """Execute the i386 helper's saves/arguments through VDSO entry.

    The VDSO and kernel have not executed at this boundary.
    """
    m=memory;r=dict(registers);s=r['esp'];arguments=r['edi']
    if r['eip']!=libc_base+0x117bb0:raise ValueError('Select syscall helper needs its actual entry PC')
    for offset,key in((4,'ebx'),(8,'edi'),(12,'ebp')):m.put_u32(s-offset,r[key])
    r.update(ebx=m.u32(arguments),ebp=m.u32(arguments+8),edi=m.u32(arguments+4))
    m.put_u32(s-16,libc_base+0x117bc2);r.update(esp=s-16,eip=m.u32(tls_base+16))
    return r

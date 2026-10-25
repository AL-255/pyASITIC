"""Native REPL polling caller and libc timeval conversion in guest Memory.

The libc wrapper follows glibc 2.39 select.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Offsets describe the pinned i386 ABI.
These operations end before select64 executes or any kernel call occurs.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import subtract_flags


def poll_select(memory,registers,loader,context):
    """Build fd_set/timeval and bind select from the earlier ELF state."""
    m=memory;s=registers['esp'];f=s-4
    m.put_u32(f,registers['ebp'])
    m.put_u32(f-144,registers['edi']);m.put_u32(f-148,registers['ebx'])
    m.zero(f-128,128);m.put_u32(f-128,1)
    m.put_u32(f-136,0);m.put_u32(f-132,100)
    for offset,value in ((152,f-136),(156,0),(160,0),(164,f-128),(168,1),(172,0x804be06)):
        m.put_u32(f-offset,value)
    # XOR EAX,EAX defines arithmetic flags; CLD and BTS clear DF and CF.
    result=dict(registers);result.update(eax=0,ecx=0,ebx=f-128,edi=f-136,ebp=f,esp=f-172,
        eflags=logical_flags(0,registers['eflags']&~0x400))
    map_=context['main_map'];plt=next(x['plt']for x in context['maps']if x['address']==map_)
    return loader.bind_import(result,map_,b'select',plt)['registers']


def select64_entry(memory,registers,*,libc_base,tls_base,sar31_af):
    """select's 32-bit timeval adapter through the select64 call boundary."""
    if sar31_af not in (0,16):raise ValueError('SAR AF needs the earlier CPU behavior profile')
    m=memory;s=registers['esp'];local=s-76;timeout=m.u32(s+20)
    if not timeout:raise NotImplementedError('Null-timeout select tail call is not bound')
    seconds=m.u32(timeout);microseconds=m.u32(timeout+4)
    for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,registers[key])
    m.put_u32(local+44,m.u32(tls_base+20))
    m.put_u32(local+12,microseconds)
    for offset,value in ((28,seconds),(32,0xffffffff if seconds&0x80000000 else 0),
                         (36,microseconds),(40,0xffffffff if microseconds&0x80000000 else 0)):
        m.put_u32(local+offset,value)
    wide=local+28
    for offset,value in ((16,wide),(20,m.u32(s+16)),(24,m.u32(s+12)),(28,m.u32(s+8)),(32,m.u32(s+4)),(36,libc_base+0x1213f4)):
        m.put_u32(local-offset,value)
    # The final SAR EBP,31 defines CF/PF/ZF/SF; its OF is cleared.
    high=0xffffffff if microseconds&0x80000000 else 0
    flags=logical_flags(high,subtract_flags(local,12,registers['eflags']))
    flags|=((microseconds>>30)&1)|sar31_af
    # SAR leaves AF undefined on the architecture. Its value comes from an
    # independent earlier CPU instruction probe, never a later select result.
    result=dict(registers);result.update(eax=m.u32(s+4),ebx=timeout,ecx=m.u32(s+12),edx=m.u32(s+8),
        esi=m.u32(s+16),edi=wide,ebp=high,esp=local-36,eip=libc_base+0x120f90,eflags=flags)
    return result

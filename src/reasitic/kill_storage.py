"""Pinned i386 kill wrapper and VDSO saves before kernel execution.

Follows glibc's i386 syscall ABI, LGPL-2.1-or-later; see the bundled license.
These functions only write guest Memory. No signal or syscall is executed.
"""


def kill_vdso_entry(memory,registers,*,libc_base,tls_base):
    """Load kill's real arguments and CALL the earlier TLS sysinfo pointer."""
    m=memory;r=dict(registers);s=r['esp']
    if r['eip']!=libc_base+0x3c390:raise ValueError('kill wrapper needs its actual entry PC')
    r.update(edx=r['ebx'],ecx=m.u32(s+8),ebx=m.u32(s+4),eax=37)
    m.put_u32(s-4,libc_base+0x3c3a6);r.update(esp=s-4,eip=m.u32(tls_base+16))
    return r


def vdso_kernel_entry(memory,registers):
    """Execute recognized i386 VDSO prefixes, stopping before the syscall."""
    m=memory;r=dict(registers);s=r['esp'];pc=r['eip']
    # Both profiles are earlier code bytes, also required by ReadStorage.
    prefix=m.read(pc,12)
    if prefix.startswith(bytes.fromhex('0f1f0051525589cd0f05cd80')):offset=8;frame=r['ecx']
    elif prefix.startswith(bytes.fromhex('51525589e50f34cd805d5a59')):offset=5;frame=s-12
    else:raise NotImplementedError('VDSO syscall prefix requires its earlier instruction ABI')
    for offset_,key in((4,'ecx'),(8,'edx'),(12,'ebp')):m.put_u32(s-offset_,r[key])
    r.update(ebp=frame,esp=s-12,eip=pc+offset)
    return r

"""Native signal-wrapper stores on the continuing i386 stack.

Follows glibc 2.39 signal.c/libc_sigaction.c, Copyright (C) 1991-2024
Free Software Foundation, Inc., LGPL-2.1-or-later. See web/GLIBC-LGPL-2.1.txt.
Python translation Copyright (C) 2026 pyASITIC authors. The instruction
layout is pinned to the captured Ubuntu i386 libc; addresses are code/ABI
offsets, never observed numerical or stack-output tables.
"""
import struct


def startup(memory,main_frame):
    """Read the earlier argc/argv/auxv and derive glibc's i386 guard."""
    argc=memory.u32(main_frame+8);argv=memory.u32(main_frame+12)
    if argc>4096:raise ValueError('Invalid earlier argc')
    pointer=argv+4*(argc+1)
    for _ in range(16384):
        if not memory.u32(pointer):break
        pointer+=4
    else:raise ValueError('Unterminated earlier environment vector')
    pointer+=4;aux={}
    for _ in range(128):
        kind,value=memory.u32(pointer),memory.u32(pointer+4);pointer+=8
        if not kind:break
        aux[kind]=value
    else:raise ValueError('Unterminated earlier auxiliary vector')
    if not aux.get(25):raise NotImplementedError('Startup without AT_RANDOM is not implemented')
    return dict(argc=argc,argv=argv,auxv=aux,guard=memory.u32(aux[25])&~255)


def add_flags(left,right,flags):
    total=left+right;value=total&0xffffffff
    bits=(int(total>0xffffffff)|int(not value)<<6|((value>>31)&1)<<7|
          int((value&255).bit_count()%2==0)<<2|int(bool((left^right^value)&16))<<4|
          int(bool((~(left^right)&(left^value))&0x80000000))<<11)
    return (flags&~0x8d5)|bits


def subtract_flags(left,right,flags):
    left&=0xffffffff;right&=0xffffffff;value=(left-right)&0xffffffff
    bits=(int(left<right)|int(not value)<<6|((value>>31)&1)<<7|
          int((value&255).bit_count()%2==0)<<2|int(bool((left^right^value)&16))<<4|
          int(bool(((left^right)&(left^value))&0x80000000))<<11)
    return (flags&~0x8d5)|bits


def bsd_signal(memory,registers,*,libc_base,guard,intr_mask,old_action,has_vdso):
    """Execute one successful BSD signal wrapper with explicit kernel state."""
    m=memory;s=registers['esp'];sig=m.u32(s+4);handler=m.u32(s+8)
    if not 1<=sig<=64 or sig in (9,19,32,33)or handler==0xffffffff:
        raise NotImplementedError('Native signal error/errno path is not implemented')
    if not has_vdso:raise NotImplementedError('Signal restorer fallback needs its loader state')
    if registers['eflags']&0x400:raise NotImplementedError('Backward signal mask copy is not implemented')
    got=libc_base+0x22fe34;local=s-300;act=local+4;old=local+144;k=local-352
    # Saved registers, PC thunks and the BSD wrapper's partially initialized
    # public sigaction. Only the kernel-sized eight-byte mask is cleared.
    for address,value in ((s-4,registers['esi']),(s-8,registers['ebx']),(s-12,libc_base+0x3bfab)):
        m.put_u32(address,value)
    m.put_u32(local+284,guard);m.put_u32(act,handler)
    mask=1<<(sig-1);m.write(act+4,struct.pack('<Q',mask))
    flags=0 if intr_mask&mask else 0x10000000;m.put_u32(act+132,flags)
    for address,value in ((local-8,old),(local-12,act),(local-16,sig),(local-20,libc_base+0x3c041),
                          (local-24,(sig-32)&0xffffffff),(local-28,libc_base+0x3c13a),(local-28,got)):
        m.put_u32(address,value)
    # __sigaction tail-calls __libc_sigaction after restoring saved registers.
    for address,value in ((local-24,registers['ebp']),(local-28,registers['edi']),
                          (local-32,(sig-32)&0xffffffff),(local-36,got),(local-40,libc_base+0x3c1af),
                          (k+12,got),(k+300,guard),(k+20,handler),(k+24,flags)):
        m.put_u32(address,value)
    m.write(k+32,m.read(act+4,128));m.put_u32(k+28,0)
    # CALL through GS:0x10 and the VDSO's three register pushes. The kernel
    # writes just its 20-byte old action, leaving the rest of koact untouched.
    for address,value in ((k-4,libc_base+0x3c245),(k-8,k+20),(k-12,k+160),(k-16,old)):
        m.put_u32(address,value)
    m.write(k+160,struct.pack('<IIIQ',old_action['handler'],old_action['flags'],old_action['restorer'],old_action['mask']))
    m.put_u32(old,m.u32(k+160));m.write(old+4,m.read(k+172,128))
    m.put_u32(old+132,m.u32(k+164));m.put_u32(old+136,m.u32(k+168))
    result=dict(registers);result.update(eax=old_action['handler'],ecx=0,edx=0,esp=s+4,eip=m.u32(s),eflags=add_flags(local,292,registers['eflags']))
    return dict(registers=result,action=dict(handler=handler,flags=flags,restorer=0,mask=mask),number=sig)


def install_console_signals(memory,workspace,libc_base,*,loader=None,loader_context=None,incoming=None):
    """Original console install sequence after the direct script returns.

    This startup path has not enabled readline or called siginterrupt. Its
    three inherited signal actions are the controlled launcher's defaults.
    """
    m=memory;script_frame=workspace+4460;main=m.u32(script_frame);inputs=startup(m,main)
    registers=dict(eax=0,ebx=m.u32(workspace-12),esi=m.u32(workspace-8),edi=m.u32(workspace-4),ebp=main,esp=script_frame+8,eflags=0x202)
    if incoming:registers.update(incoming)
    if loader is not None:registers['eflags']=add_flags(script_frame+8,4,registers['eflags'])
    m.put_u32(script_frame+8,0x804b057);m.put_u32(script_frame+4,main)
    registers['ebp']=script_frame+4;registers['esp']=script_frame+4;actions={}
    for number,handler,pc in ((2,0x804c2c4,0x804c23b),(6,0x804c2c4,0x804c26c),(3,0x804c33c,0x804c29c)):
        for address,value in ((script_frame,handler),(script_frame-4,number),(script_frame-8,pc)):m.put_u32(address,value)
        registers['esp']=script_frame-8
        if loader is not None:
            context=loader_context;map_=context['main_map'];plt=next(item['plt']for item in context['maps']if item['address']==map_)
            binding=loader.bind_import(registers,map_,b'signal',plt);registers=binding['registers']
            if binding['target']!=libc_base+0x3bfa0:raise NotImplementedError('Interposed signal implementation is not bound')
        call=bsd_signal(m,registers,libc_base=libc_base,guard=inputs['guard'],intr_mask=0,
                        old_action=dict(handler=0,flags=0,restorer=0,mask=0),has_vdso=bool(inputs['auxv'].get(32)))
        registers=call['registers'];actions[number]=call['action']
        if loader is not None:registers['eflags']=subtract_flags(registers['eax'],0xffffffff,registers['eflags'])
    return dict(main_frame=main,line=main-1024,actions=actions,main_registers=dict(registers,ebp=main,esp=script_frame+12,eip=0x804b057))

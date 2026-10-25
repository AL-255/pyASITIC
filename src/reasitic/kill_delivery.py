"""Linux i386 self-group kill through legacy signal-handler entry.

This models the compatibility syscall ABI and composes the original glibc/
VDSO prefixes with the signal-frame serializer. It executes no host syscall.
The actual earlier XSAVE state is required; later interrupted/handler states
are never execution inputs.
"""
from .kill_storage import kill_vdso_entry,vdso_kernel_entry
from .signal_frame import deliver


def interrupted_kill(memory,registers,*,number,mask,process):
    """Successful self-group kill, before the pending signal is delivered.

    Linux entry_SYSCALL_compat/do_fast_syscall_32 restore the saved EBP,
    retain syscall arguments in pt_regs, and select the VDSO int80 landing
    pad. Other process targets and deferred/default signals need their own
    kernel operations.
    """
    m=memory;r=dict(registers);pc=r['eip'];instruction=m.read(pc,4)
    if r['eax']!=37:raise ValueError('Interrupted kill requires syscall 37')
    if r['ebx']!=0 or process['pid']<=0 or process['pgrp']<=0:raise NotImplementedError('Other kill targets need their earlier process-group state')
    if not 1<=number<=64 or number in(9,19):raise NotImplementedError('Default or invalid kill signal needs its own kernel operation')
    if not 0<=mask<1<<64:raise ValueError('Invalid earlier signal mask')
    if mask&(1<<(number-1)):raise NotImplementedError('Blocked kill signal needs pending-signal continuation')
    if instruction==bytes.fromhex('0f05cd80'):
        signal=r['ebp'];flags=r['eflags']&~0x10000
    elif instruction==bytes.fromhex('0f34cd80'):
        if r['ebp']!=r['esp']:raise ValueError('SYSENTER needs its actual saved-stack ABI')
        signal=r['ecx'];flags=r['eflags']|0x200
    else:raise NotImplementedError('Kill needs a recognized earlier compatibility syscall instruction')
    if signal!=number:raise ValueError('Earlier kill argument differs from the requested signal')
    if flags&(0x100|0x20000):raise NotImplementedError('Traced or virtual-mode kill needs its compatibility entry path')
    if(r['cs'],r['ss'])!=(0x23,0x2b):raise NotImplementedError('Other kill segment modes need their compatibility entry path')
    r.update(eax=0,orig_eax=37,ecx=signal,ebp=m.u32(r['esp']),eip=pc+4,eflags=flags)
    return r


def deliver_from_kill(memory,registers,xstate,*,libc_base,tls_base,number,mask,action,process,thread,cpu,vdso,observer=None):
    """Execute once from actual earlier kill state through handler entry.

    An observer can assert each produced inner boundary. Its return value
    never changes execution, and no inner captured state resets Memory/FP.
    """
    if xstate is None:raise ValueError('Kill delivery needs the actual earlier XSAVE state')
    if action['handler']in(0,1):raise NotImplementedError('Default or ignored kill needs its own kernel operation')
    state=bytes(xstate)
    if len(state)!=cpu['size']:raise ValueError('Kill delivery needs the complete earlier standard XSAVE state')
    def observe(phase,r,fp,blocked):
        if observer is not None:observer(phase,dict(r),bytes(fp),blocked)
    r=kill_vdso_entry(memory,registers,libc_base=libc_base,tls_base=tls_base)
    observe('vdso',r,state,mask)
    r=vdso_kernel_entry(memory,r);observe('kernel',r,state,mask)
    r=interrupted_kill(memory,r,number=number,mask=mask,process=process);observe('interrupted',r,state,mask)
    image=dict(address=vdso['address'],data=memory.read(vdso['address'],vdso['size']).hex())
    result=deliver(memory,r,state,number=number,action=action,mask=mask,thread=thread,cpu=cpu,vdso=image)
    observe('handler',result['registers'],result['xstate'],result['mask'])
    return result

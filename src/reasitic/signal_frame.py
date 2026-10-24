"""Serialize the Linux i386 legacy signal ABI in guest memory.

Inputs are the interrupted CPU state, existing stack, signal action/mask,
CPU XSAVE layout and loader VDSO image. No native post-delivery bytes are
inputs. Layouts follow the Linux UAPI sigcontext and sigframe interfaces;
unsupported alternate-stack/RT/dynamic-XSAVE paths are explicit boundaries.
"""
import struct


def elf32_symbols(data,base):
    if data[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('Expected a little-endian ELF32 image')
    offset=struct.unpack_from('<I',data,32)[0];size,count=struct.unpack_from('<HH',data,46)
    if size!=40:raise ValueError('Unsupported ELF32 section size')
    sections=[struct.unpack_from('<10I',data,offset+size*i)for i in range(count)];symbols={}
    for section in sections:
        if section[1]!=11:continue
        if section[9]!=16:raise ValueError('Unsupported ELF32 symbol size')
        strings=sections[section[6]];names=data[strings[4]:strings[4]+strings[5]]
        for position in range(section[4],section[4]+section[5],16):
            name,value,_length,_info,_other,index=struct.unpack_from('<IIIBBH',data,position)
            if index:symbols[names[name:].split(b'\0',1)[0].decode()]=(base+value)&0xffffffff
    return symbols


def legacy_x87(xstate,registers):
    """FXSAVE's abridged tags and 16-byte slots -> i387's full tags/slots."""
    control,status=struct.unpack_from('<HH',xstate);top=(status>>11)&7;tags=0xffff0000
    for index in range(8):
        tag=3
        if xstate[4]&(1<<index):
            offset=32+16*((index-top)&7)
            mantissa,exponent=struct.unpack_from('<QH',xstate,offset);exponent&=0x7fff
            tag=2 if exponent==0x7fff else (1 if not mantissa else 2)if not exponent else(0 if mantissa>>63 else 2)
        tags|=tag<<(2*index)
    ip,dp=struct.unpack_from('<I',xstate,8)[0],struct.unpack_from('<I',xstate,16)[0]
    result=struct.pack('<7I',control|0xffff0000,status|0xffff0000,tags,ip,registers['cs'],dp,registers['ds']|0xffff0000)
    return result+b''.join(xstate[32+16*i:42+16*i]for i in range(8))


def handler_xstate(xstate,cpu):
    """The handler starts with initialized user FP/SIMD state and kernel PKRU."""
    data=bytearray(len(xstate));struct.pack_into('<H',data,0,0x37f)
    struct.pack_into('<I',data,24,0x1f80);data[28:32]=xstate[28:32]
    struct.pack_into('<Q',data,464,cpu['features'])
    if cpu['features']&(1<<9):
        component=next(c for c in cpu['components']if c['bit']==9)
        struct.pack_into('<I',data,component['offset'],cpu['initial_pkru'])
        if cpu['initial_pkru']:struct.pack_into('<Q',data,512,1<<9)
    return bytes(data)


def deliver(memory,registers,xstate,*,number,action,mask,thread,cpu,vdso):
    """Write one legacy frame; return the handler's CPU state and signal mask."""
    if len(xstate)<576:raise ValueError('Truncated standard XSAVE state')
    flags=action['flags'];features=struct.unpack_from('<Q',xstate,464)[0]
    if flags&(4|0x08000000):raise NotImplementedError('RT or alternate-stack signal delivery is not implemented')
    if flags&~0x14000000:raise NotImplementedError('Additional signal-action flags are not implemented')
    if features!=cpu['features']or len(xstate)!=cpu['size']:raise NotImplementedError('Dynamic or restricted XSAVE layout is not implemented')
    if features&~0x2e7:raise NotImplementedError('Additional XSAVE components are not implemented')
    if struct.unpack_from('<Q',xstate,520)[0]:raise NotImplementedError('Compacted XSAVE state is not implemented')
    if struct.unpack_from('<Q',xstate,512)[0]&~features:raise ValueError('Active XSAVE bits exceed enabled features')
    for component in cpu['components']:
        if component['offset']<576 or component['size']<1 or component['offset']+component['size']>len(xstate):raise ValueError('XSAVE component is outside its declared layout')
    if registers['ss']!=0x2b:raise NotImplementedError('Legacy signal stack switching is not implemented')
    if not 1<=number<=64:raise ValueError('Invalid signal number')
    if not 0<=mask<1<<64 or not 0<=action['mask']<1<<64:raise ValueError('Invalid signal mask')
    # The i386 FSAVE prefix precedes a 64-byte aligned XSAVE area. The
    # legacy signal record reserves its historical unused 624-byte FP field.
    extended=len(xstate)+4;fx=(registers['esp']-extended)&~63;fp=fx-112
    frame=((fp-732+4)&~15)-4
    if flags&0x04000000:restorer=action['restorer']
    else:restorer=elf32_symbols(bytes.fromhex(vdso['data']),vdso['address']).get('__kernel_sigreturn',frame+724)
    context=[registers[k]for k in ('gs','fs','es','ds','edi','esi','ebp','esp','ebx','edx','ecx','eax')]
    context+=[thread['trapno'],thread['error_code'],registers['eip'],registers['cs'],registers['eflags'],registers['esp'],registers['ss'],fp,mask&0xffffffff,thread['cr2']]
    memory.write(frame,struct.pack('<24I',restorer,number,*context))
    memory.put_u32(frame+720,mask>>32)
    memory.write(frame+724,b'\x58\xb8\x77\0\0\0\xcd\x80')
    memory.write(fp,legacy_x87(xstate,registers)+struct.pack('<HH',struct.unpack_from('<H',xstate,2)[0],0))
    # The 64-bit kernel saves all legacy register slots, including high XMM
    # slots and zero register padding. Reserved gaps in the full XSAVE
    # layout and the unused historical frame remain the earlier stack bytes.
    memory.write(fx,xstate[:416])
    memory.write(fx+464,struct.pack('<IIQI7I',0x46505853,extended+112,features,len(xstate),*([0]*7)))
    memory.zero(fx+512,64);memory.write(fx+512,struct.pack('<Q',struct.unpack_from('<Q',xstate,512)[0]|3))
    for component in cpu['components']:
        if features&(1<<component['bit']):
            offset,size=component['offset'],component['size']
            # PKRU's architectural component reserves eight bytes but its
            # register/store occupies only the low four bytes.
            if component['bit']==9:size=4
            memory.write(fx+offset,xstate[offset:offset+size])
    memory.put_u32(fx+len(xstate),0x46505845)
    result=dict(registers);result.update(esp=frame,eip=action['handler'],eax=number,ecx=0,edx=0,cs=0x23,ss=0x2b,ds=0x2b,es=0x2b,orig_eax=0xffffffff,eflags=registers['eflags']&~(0x400|0x10000|0x100))
    blocked=mask|action['mask']|(1<<(number-1));blocked&=~((1<<8)|(1<<18))
    return dict(registers=result,mask=blocked,xstate=handler_xstate(xstate,cpu),frame=frame,fpstate=fp,fxstate=fx)

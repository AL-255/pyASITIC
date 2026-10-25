"""Native i386 PLT trampoline and lazy fixup in earlier guest memory.

Follows glibc 2.39 elf/dl-runtime.c and sysdeps/i386/dl-trampoline.S,
Copyright (C) 1995-2024 Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Python translation (C) 2026 pyASITIC authors.
ABI stores are pinned to the documented Ubuntu i386 loader/libc builds.
"""
from .loader_lookup_storage import LoaderLookup
from .signal_install_storage import add_flags


class PltFixup(LoaderLookup):
    def __init__(self,memory,base,*,tls_base):
        super().__init__(memory,base);self.tls_base=tls_base
    def bind_import(self,registers,map_,name,plt):
        """Call a named import using ELF relocation/GOT state and PLT layout.

        Registers/stack describe the target entry with its caller's return
        word already pushed. A previously bound import bypasses the resolver.
        Only ELF section addresses/sizes are needed; no PLT code is read.
        """
        m=self.m;info=m.u32(map_+32+8)
        if not info or not plt:raise NotImplementedError('Import has no ordinary i386 PLT metadata')
        size=m.u32(info+4)
        if size%8 or plt['size']!=16*(size//8+1):raise NotImplementedError('Alternate i386 PLT layout is not implemented')
        rels=self._dynamic(map_,23);symtab=self._dynamic(map_,6);strings=self._dynamic(map_,5)
        for offset in range(0,size,8):
            reloc=rels+offset;symbol=symtab+16*(m.u32(reloc+4)>>8)
            if self._string(strings+m.u32(symbol))!=name:continue
            slot=m.u32(map_)+m.u32(reloc);target=m.u32(slot);unresolved=plt['address']+16*(offset//8+1)+6
            if target!=unresolved:
                after=dict(registers);after['eip']=target;return dict(registers=after,target=target,relocation_address=slot,lazy=False)
            s=registers['esp'];self._put(s-4,offset);self._put(s-8,map_)
            entry=dict(registers);entry.update(esp=s-8,eip=self.base+0x11ba0)
            result=self.resolve(entry);result['lazy']=True;return result
        raise ValueError('Named import absent from the ELF PLT relocations')
    def _ifunc(self,provider,symbol,stack):
        m=self.m;offset=m.u32(symbol+4);base=m.u32(provider)
        if offset not in(0xa3c30,0xa3e10):raise NotImplementedError('This IFUNC resolver source path is not implemented')
        # i386 IFUNC selectors follow CPU usable/preference bits.
        # Its PC thunk writes a return word but has no frame or FP effects.
        got=base+0x22fe34;self._put(stack-4,base+offset+9);cpu=m.u32(got+0x10c)
        if offset==0xa3e10:
            # strcmp.c: SSE4.2, then SSSE3, then the ia32 implementation.
            features=m.u32(cpu+0x74)
            if features&0x100000:return got-0x96b34
            return got-0x9ea24 if features&0x200 else got-0x173c14
        if self._byte(cpu+0x7b)&4 and self._byte(cpu+0x19c)&1:return got-0x1796a4
        return got-0x17b114 if self._byte(cpu+0x75)&2 else got-0x1741d4
    def resolve(self,registers):
        """_dl_runtime_resolve entry -> resolved target entry, before execution."""
        m=self.m;t=registers['esp'];map_=m.u32(t);reloc_arg=m.u32(t+4)
        if m.u32(self.tls_base+12):raise NotImplementedError('Multithreaded PLT scope locking is not implemented')
        if m.u32(map_+448):raise NotImplementedError('Audited PLT binding is not implemented')
        s=t-16;local=s-76
        # Trampoline saves volatile registers; CALL enters regparm _dl_fixup.
        for offset,key in ((4,'eax'),(8,'ecx'),(12,'edx')):self._put(t-offset,registers[key])
        self._put(s,self.base+0x11bb0)
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):self._put(s-offset,registers[key])
        self._put(local+12,self.got);self._put(local+8,reloc_arg)
        symtab=self._dynamic(map_,6);strtab=self._dynamic(map_,5);reloc=self._dynamic(map_,23)+reloc_arg
        info=m.u32(reloc+4);symbol=symtab+16*(info>>8);target=m.u32(map_)+m.u32(reloc)
        for offset,value in ((20,strtab),(28,reloc),(16,info),(24,target),(40,symbol)):self._put(local+offset,value)
        if info&255!=7:raise ValueError('PLT relocation is not R_386_JMP_SLOT')
        provider=map_
        if self._byte(symbol+13)&3==0:
            version=0;verinfo=m.u32(map_+244)
            if verinfo:
                # DT_VERSYM's cached l_info slot, like other D_PTR operands,
                # is relative only when the dynamic section is read-only.
                versions=m.u32(verinfo+4)+(m.u32(map_)if self._byte(map_+422)&32 else 0)
                version=m.u32(map_+384)+16*(m.u16(versions+2*(info>>8))&0x7fff)
                if not m.u32(version+4):version=0
            name=strtab+m.u32(symbol);scope=m.u32(map_+488)
            self._words(local-32,(name,map_,local+40,scope,version,1,1,0));self._put(local-36,self.base+0xfac6)
            args=dict(registers);args.update(eax=symbol,ebx=0,ecx=1,edx=local+40,esi=name,edi=map_,ebp=info>>8,esp=local-36,eip=self.base+0xa6b0,eflags=add_flags(strtab,m.u32(symbol),registers['eflags']))
            found=self.lookup(args);provider=found['provider'];symbol=m.u32(local+40)
        value=m.u32(symbol+4)+(0 if m.u16(symbol+14)==0xfff1 else m.u32(provider))
        self._put(local+44,value)
        if self._byte(symbol+12)&15==10:
            self._put(local-4,self.base+0xfc22);value=self._ifunc(provider,symbol,local-4);self._put(local+44,value)
        if not m.u32(self.got-0x458):self._put(target,value)
        # POP EDX, load ECX, overwrite its stack save with the target, then
        # restore EAX and RET $12. The map/relocation words remain below ESP.
        self._put(t-8,value)
        after=dict(registers);after.update(esp=t+8,eip=value,eflags=add_flags(local,60,registers['eflags']))
        return dict(registers=after,provider=provider,symbol=symbol,target=value,relocation_address=target)

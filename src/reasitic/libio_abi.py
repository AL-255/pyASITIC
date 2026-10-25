"""Shared pinned legacy i386 libio callbacks, guards and PIC wrappers.

Follows glibc 2.39 libio/vtables.c and the legacy C++ ABI,
LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt.
"""
from .signal_install_storage import add_flags


class LibioABI:
    def __init__(self,memory,loader,context,*,libc_base,tls_base):
        self.m,self.loader,self.context=memory,loader,context
        self.libc,self.tls,self.got=libc_base,tls_base,libc_base+0x22fe34
        self.legacy=next(x for x in context['maps']if x['name'].endswith('/libstdc++-libc6.1-1.so.2'))
        if self.legacy['plt']['elf_sha256']!='bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34':
            raise NotImplementedError('Legacy IO needs the pinned streambuf ABI')
        self.legacy_base=memory.u32(self.legacy['address']);self.legacy_got=loader._dynamic(self.legacy['address'],3)

    def _bind(self,registers,name,provider=None):
        provider=provider or next(x for x in self.context['maps']if x['address']==self.context['main_map'])
        return self.loader.bind_import(registers,provider['address'],name,provider['plt'])['registers']

    def _guard(self,registers,return_pc):
        m=self.m;entry=registers['esp']-4;local=entry-44;target=self.libc+0x81640
        encoded=m.u32(self.got+0x1a30);decoded=((encoded>>9)|(encoded<<23))&0xffffffff
        if decoded^m.u32(self.tls+24)!=target:raise NotImplementedError('Foreign-vtable validation needs its loader-namespace branch')
        m.put_u32(entry,return_pc);m.put_u32(entry-4,registers['ebx']);m.put_u32(entry-8,self.libc+0x8164a)
        m.put_u32(local+28,m.u32(self.tls+20))
        return dict(registers,eax=0,edx=target,eip=return_pc,eflags=add_flags(local,40,registers['eflags']))

    def _wrapper(self,registers,offset,addend,name,arguments):
        m=self.m;entry=registers['esp'];f=entry-4;pc=self.legacy_base+offset
        m.put_u32(f,registers['ebp']);m.put_u32(f-4,registers['ebx']);m.put_u32(f-8,pc+9)
        for i,value in enumerate(reversed(arguments)):m.put_u32(f-8-4*i,value)
        s=f-8-4*len(arguments);m.put_u32(s,pc+21+3*len(arguments))
        r=dict(registers,ebp=f,ebx=self.legacy_got,esp=s,eflags=add_flags(pc+9,addend,registers['eflags']))
        return self._bind(r,name,self.legacy)

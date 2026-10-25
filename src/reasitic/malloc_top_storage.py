"""Pinned i386 single-thread malloc ABI for a top split with empty free bins.

Follows glibc 2.39 malloc/malloc.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Heap.malloc makes the allocation decision.
No native return value or later allocation state supplies a runtime input.
"""
from .heap import request_size,bin_index
from .signal_install_storage import add_flags


class MallocTopStorage:
    def __init__(self,heap,memory,*,libc_base,tls_base):
        self.heap,self.m,self.libc,self.tls=heap,memory,libc_base,tls_base
        self.got=libc_base+0x22fe34

    def malloc(self,registers):
        m,h=self.m,self.heap;r=dict(registers);s=r['esp'];request=m.u32(s+4);size=request_size(request);index=h._cache_index(size)
        if r['eip']!=self.libc+0x9ea00:raise NotImplementedError('Alternate malloc needs its source ABI')
        if not m.read(self.got+0x3c04,1)[0]or m.u32(self.tls+12):raise NotImplementedError('Top malloc needs initialized single-thread state')
        thread=m.u32(self.tls);cache_offset=m.u32(self.got+0x78);cache=m.u32((thread+cache_offset)&0xffffffff)
        if cache!=h.cache_address or m.u32(self.got+0x368)!=h.parameters['tcache_bins']:raise ValueError('Malloc TLS/control state differs from the continuing heap')
        h.require_cache_memory(m,m.u32(self.got+0x3bfc))
        if h.arena_address!=self.got+0x92c:raise NotImplementedError('Alternate malloc arenas need their source ABI')
        if not cache or index<h.parameters['tcache_bins']or size<1008 or h.have_fastchunks:
            raise NotImplementedError('Top malloc tcache/small/consolidation branches need their source ABI')
        if m.read(self.got+0x3c18,1)[0]!=h.max_fast or size<=h.max_fast:raise ValueError('Malloc fastbin controls differ from the continuing heap')
        if any(h.bins[1:])or any(h.binmap):raise NotImplementedError('Top malloc bin-search stores need their source ABI')
        if m.u32(self.got+0x3c14):raise NotImplementedError('Malloc perturbation needs its child copy ABI')
        top=h.top;chunk=h.chunks[top]
        if m.u32(h.arena_address+56)!=top or m.u32(top+4)&~7!=chunk.size:raise ValueError('Malloc physical top differs from the continuing heap')
        if chunk.size>h.system_mem or chunk.size<size+16:raise NotImplementedError('Top malloc needs a valid sufficiently large existing top')
        local=s-44;entry=local-4;inner=entry-92
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(entry,self.libc+0x9eb7f)
        for offset,value in ((4,thread),(8,self.got),(12,request),(16,h.arena_address)):m.put_u32(entry-offset,value)
        for offset,value in ((12,self.got),(28,request),(56,bin_index(size)),(44,0),(20,thread),(52,index),(24,cache_offset),(36,0),(16,h._bin_head(1))):m.put_u32(inner+offset,value)
        pointer=h.malloc(request)
        if pointer!=top+8:raise ValueError('Malloc source decision did not split the top')
        m.put_u32(h.arena_address+56,h.top)
        # alloc_perturb still executes its frame and PIC thunk when disabled.
        m.put_u32(inner-4,self.libc+0x9e16c);m.put_u32(inner-8,size|1);m.put_u32(inner-12,self.libc+0x9a986)
        return dict(r,eax=pointer,ecx=0,edx=0,esp=s+4,eip=m.u32(s),eflags=add_flags(local,28,r['eflags']))

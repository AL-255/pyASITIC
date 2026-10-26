"""Pinned i386 large malloc ABI, sharing bin/top/consolidation execution.

Follows glibc 2.39 malloc/malloc.c, LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. Heap.malloc remains the allocation algorithm.
Small/tcache allocator paths require their own source ABI before connection.
"""
from .heap import request_size,bin_index
from .signal_install_storage import add_flags


class MallocStorage:
    def __init__(self,heap,memory,*,libc_base,tls_base):
        self.heap=heap;self.m=memory;self.libc=libc_base;self.got=libc_base+0x22fe34;self.tls=tls_base

    def enter(self,registers):
        self.large=None
        m=self.m;h=self.heap;r=dict(registers);s=r['esp'];request=m.u32(s+4);size=request_size(request);index=h._cache_index(size)
        if r['eip']!=self.libc+0x9ea00:raise NotImplementedError('Malloc interposition needs its own ABI')
        if not m.read(self.got+0x3c04,1)[0]or m.u32(self.tls+12):raise NotImplementedError('Malloc ABI needs initialized single-thread state')
        cache_offset=m.u32(self.got+0x78);cache=m.u32((self.tls+cache_offset)&0xffffffff)
        if cache!=h.cache_address or m.u32(self.got+0x368)!=h.parameters['tcache_bins']:
            raise ValueError('Malloc TLS/control state differs from the continuing heap')
        h.require_cache_memory(m,m.u32(self.got+0x3bfc))
        if h.arena_address!=self.got+0x92c:raise NotImplementedError('Malloc alternate arenas need their source ABI')
        if not cache or index<h.parameters['tcache_bins']:
            raise NotImplementedError('Malloc tcache paths need their source ABI')
        if size<1008:raise NotImplementedError('Malloc small branches need their source ABI')
        if h.have_fastchunks or not h.bins[1]or h.chunks[h.bins[1][-1]].size!=size:
            from .malloc_top_storage import MallocTopStorage
            self.large=MallocTopStorage(h,m,libc_base=self.libc,tls_base=self.tls)
            self.large.enter(r);return
        if m.read(self.got+0x3c18,1)[0]!=h.max_fast:raise ValueError('Malloc fastbin controls differ from the continuing heap')
        if m.u32(self.got+0x3c14):raise NotImplementedError('Malloc perturbation needs its child copy ABI')
        candidate=h.bins[1][-1];head=h._bin_head(1);following=candidate+size
        next_word=m.u32(following+4)
        if m.u32(candidate+4)&~7!=size or m.u32(candidate+8)!=head or m.u32(m.u32(candidate+12)+8)!=candidate or m.u32(following)&~7!=size or next_word&1 or not 7<next_word<=h.system_mem:
            raise ValueError('Malloc unsorted physical links/foot differ from source metadata')
        self.registers=r;self.local=s-44;self.inner=self.local-4-92;self.candidate=candidate
        self.following_word=m.u32(following+4)|1
        # __libc_malloc saves four registers and invokes _int_malloc
        # through the ordinary single-thread CALL/RET branch.
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(self.local-4,self.libc+0x9eb7f)
        inner_entry=self.local-4
        for offset,value in ((4,self.tls),(8,self.got),(12,request),(16,h.arena_address)):
            m.put_u32(inner_entry-offset,value)
        # _int_malloc's local slots, only where the actual branch stores.
        for offset,value in ((12,self.got),(28,request),(56,bin_index(size)),(44,0),
            (20,self.tls),(52,index),(24,cache_offset),(36,0),(16,head),(40,0),(48,0),(32,size)):
            m.put_u32(self.inner+offset,value)

    def returned(self,pointer):
        if self.large is not None:return self.large.returned(pointer)
        if pointer!=self.candidate+8:raise ValueError('Malloc returned a different source candidate')
        r=self.registers;s=r['esp']
        return dict(r,eax=pointer,ecx=self.following_word,edx=0,esp=s+4,eip=self.m.u32(s),
                    eflags=add_flags(self.local,28,r['eflags']))

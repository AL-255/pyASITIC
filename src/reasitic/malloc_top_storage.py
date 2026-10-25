"""Pinned i386 single-thread large malloc ABI, including bin and top splits.

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
        if not cache or index<h.parameters['tcache_bins']or size<1008:
            raise NotImplementedError('Top malloc tcache/small branches need their source ABI')
        if m.read(self.got+0x3c18,1)[0]!=h.max_fast or size<=h.max_fast:raise ValueError('Malloc fastbin controls differ from the continuing heap')
        if m.u32(self.got+0x3c14):raise NotImplementedError('Malloc perturbation needs its child copy ABI')
        local=s-44;entry=local-4;inner=entry-92
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):m.put_u32(s-offset,r[key])
        m.put_u32(entry,self.libc+0x9eb7f)
        for offset,value in ((4,thread),(8,self.got),(12,request),(16,h.arena_address)):m.put_u32(entry-offset,value)
        for offset,value in ((12,self.got),(28,request),(56,bin_index(size))):m.put_u32(inner+offset,value)
        if h.have_fastchunks:self._consolidate(inner,size,request)
        top=h.top;chunk=h.chunks[top]
        if m.u32(h.arena_address+56)!=top or m.u32(top+4)&~7!=chunk.size:raise ValueError('Malloc physical top differs from the continuing heap')
        if chunk.size>h.system_mem:raise ValueError('Malloc top exceeds arena system memory')
        for offset,value in ((44,0),(20,thread),(52,index),(24,cache_offset),(36,0),(16,h._bin_head(1))):m.put_u32(inner+offset,value)
        unsorted=list(reversed(h.bins[1]))
        exact=next((p for p in unsorted if h.chunks[p].size==size),None)
        processed=unsorted[:unsorted.index(exact)]if exact is not None else unsorted
        if unsorted:
            # The unsorted loop stores these locals only after observing a
            # nonempty list. Requests larger than every candidate retag the
            # candidates and then reach the unchanged top-split branch.
            for offset,value in ((40,len(processed)),(48,0),(32,size),(36,len(processed))):m.put_u32(inner+offset,value)
            if processed:m.put_u32(inner+60,bin_index(h.chunks[processed[-1]].size))
            for candidate in processed+([exact]if exact is not None else[]):
                c=h.chunks[candidate];following=candidate+c.size;word=m.u32(following+4)
                if m.u32(candidate+4)&~7!=c.size or not 7<word<=h.system_mem or m.u32(following)&~7!=c.size or word&1:
                    raise ValueError('Malloc unsorted physical size/footer differs from the continuing heap')
        for chain in h.bins[1:]:
            for candidate in chain:
                if m.u32(m.u32(candidate+8)+12)!=candidate or m.u32(m.u32(candidate+12)+8)!=candidate:raise ValueError('Malloc free-bin physical links differ from the continuing heap')
        sizes={p:c.size for p,c in h.chunks.items()}
        exact_word=m.u32(exact+size+4)|1 if exact is not None else None
        pointer=h.malloc(request)
        candidate=pointer-8;ecx=0
        if exact is not None:
            if candidate!=exact:raise ValueError('Malloc source decision differs from its unsorted exact fit')
            ecx=exact_word
        elif candidate==top:
            m.put_u32(h.arena_address+56,h.top)
            # alloc_perturb still executes its frame and PIC thunk when disabled.
            m.put_u32(inner-4,self.libc+0x9e16c);m.put_u32(inner-8,size|1);m.put_u32(inner-12,self.libc+0x9a986)
        else:
            original_size=sizes[candidate];remaining=original_size-size;selected=bin_index(original_size)
            m.put_u32(inner+20,original_size)
            if selected==bin_index(size):
                m.put_u32(inner+24,remaining);m.put_u32(inner-4,self.libc+0x9e0a5);m.put_u32(inner-8,original_size);m.put_u32(inner-12,candidate)
                if remaining<16:raise NotImplementedError('Same-bin malloc without splitting needs its source ABI')
                m.put_u32(inner-4,self.libc+0x9e11f);m.put_u32(inner-8,candidate);m.put_u32(inner-12,self.libc+0x9a986)
            elif selected>bin_index(size):
                m.put_u32(inner+24,candidate);m.put_u32(inner-4,self.libc+0x9df0b);m.put_u32(inner-8,original_size);m.put_u32(inner-12,original_size);ecx=candidate
            else:raise ValueError('Malloc source selected an unexpected size class')
        return dict(r,eax=pointer,ecx=ecx,edx=0,esp=s+4,eip=m.u32(s),eflags=add_flags(local,28,r['eflags']))

    def _consolidate(self,inner,size,request):
        """malloc_consolidate's saves, loop locals and actual heap merges."""
        m,h=self.m,self.heap;entry=inner-4;local=entry-76;arena=h.arena_address
        m.put_u32(entry,self.libc+0x9d8ff)
        for offset,value in ((4,size),(8,arena),(12,request),(16,arena)):m.put_u32(entry-offset,value)
        m.put_u32(local+44,self.got);m.put_u32(local+32,arena+56)
        h.have_fastchunks=False;m.put_u32(arena+8,0)
        for index,chain in enumerate(h.fastbins):
            slot=arena+12+4*index;m.put_u32(local+12,slot)
            expected=chain[0]if chain else 0
            if m.u32(slot)!=expected:raise ValueError('Malloc fastbin head differs from the continuing heap')
            m.put_u32(slot,0)
            if chain:m.put_u32(local+16,arena)
            while chain:
                p=chain[0];word=m.u32(p+4);chunk=h.chunks[p];length=word&~7;key=(p+8)>>12;encoded=m.u32(p+8);following=encoded^key
                if p%16!=8 or length!=chunk.size or(length>>3)-2!=index or following!=(chain[1]if len(chain)>1 else 0):raise ValueError('Malloc fastbin physical header/link differs from the continuing heap')
                next_address=p+length;next_word=m.u32(next_address+4);next_size=next_word&~7
                m.put_u32(local+24,key);m.put_u32(local+28,following);m.put_u32(local+20,next_size)
                merged=p;total=length
                if not word&1:
                    previous=m.u32(p);merged=p-previous
                    if chunk.previous!=previous or h.chunks[merged].size!=previous:raise ValueError('Malloc backward consolidation footer differs')
                    total+=previous;m.put_u32(local+40,next_word);m.put_u32(local+36,encoded)
                    m.put_u32(local-4,self.libc+0x9b3a6);m.put_u32(local-8,total);m.put_u32(local-12,merged)
                if next_address!=h.top and not m.u32(next_address+next_size+4)&1:
                    total+=next_size;m.put_u32(local+36,encoded)
                    m.put_u32(local-4,self.libc+0x9b3f5);m.put_u32(local-8,total);m.put_u32(local-12,merged)
                chain.pop(0);old_top=h.top;h._merge(p)
                if old_top!=h.top:m.put_u32(arena+56,h.top)
        m.put_u32(local+12,arena+56)

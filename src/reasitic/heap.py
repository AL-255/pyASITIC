"""Single-threaded i386 glibc 2.39 arena placement, under development.

This module is not connected to electrical solves. Snapshot initialization is
for independent native comparisons; production must derive its own allocation
history. Noncontiguous heap extension and mmap remain explicit boundaries.

The algorithms follow malloc/malloc.c in glibc 2.39, Copyright (C) 1996-2024
Free Software Foundation, Inc. and Copyright The GNU Toolchain Authors,
under LGPL-2.1-or-later. See web/GLIBC-LGPL-2.1.txt. Distributed without
warranty of merchantability or fitness for a particular purpose.
Python translation Copyright (C) 2026 pyASITIC authors.
"""
from dataclasses import dataclass


class SystemAllocationRequired(NotImplementedError):
    """The arena cannot satisfy a request without an OS allocation."""


@dataclass
class Chunk:
    size: int
    previous: int
    previous_in_use: bool


def request_size(size):
    if isinstance(size,bool) or not isinstance(size,int) or not 0<=size<=0x7fffffff:
        raise ValueError('Invalid i386 allocation size')
    return max(16,(size+4+15)&~15)


def bin_index(size):
    if size<1008:return (size>>4)+1
    for shift,limit,offset in ((6,45,49),(9,20,91),(12,10,110),(15,4,119),(18,2,124)):
        if size>>shift<=limit:return offset+(size>>shift)
    return 126


class Heap:
    """Arena metadata and ordered free lists, with no numerical fixture data."""
    def __init__(self,snapshot):
        self.chunks={c['address']:Chunk(c['size_word']&~7,c['prev_size'],bool(c['size_word']&1))for c in snapshot['chunks']}
        self.top=snapshot['top'];self.last_remainder=snapshot['last_remainder']
        self.have_fastchunks=bool(snapshot['have_fastchunks'])
        self.max_fast=snapshot['max_fast'];self.parameters=dict(snapshot['parameters'])
        self.flags=snapshot['flags'];self.system_mem=snapshot['system_mem']
        self.ranges=[(m['start'],m['end'])for m in snapshot['maps']if m['path']!='[heap]']
        self.bins=[[],*(list(b)for b in snapshot['bins'])]
        self.fastbins=[list(b)for b in snapshot['fastbins']]
        # Cached entries contain user addresses; all other lists use headers.
        self.tcache=[[p-8 for p in b]for b in snapshot['tcache']]
        self.tcache_enabled=bool(snapshot['tcache_address'])

    def _cache_index(self,size):return (size-16)//16

    def _cache_has_space(self,size):
        index=self._cache_index(size)
        return self.tcache_enabled and index<self.parameters['tcache_bins'] and len(self.tcache[index])<self.parameters['tcache_count']

    def _unlink(self,p):
        for chain in self.bins[1:]:
            if p in chain:chain.remove(p);return
        raise ValueError('Free chunk is missing from arena bins')

    def _mark_in_use(self,p):
        self.chunks[p+self.chunks[p].size].previous_in_use=True
        return p+8

    def _insert_bin(self,p):
        size=self.chunks[p].size;chain=self.bins[bin_index(size)]
        if size<1008:chain.insert(0,p);return
        index=0
        while index<len(chain)and self.chunks[chain[index]].size>size:index+=1
        if index<len(chain)and self.chunks[chain[index]].size==size:index+=1
        chain.insert(index,p)

    def _split(self,p,size,advertise=False):
        chunk=self.chunks[p];remaining=chunk.size-size
        if remaining<16:return self._mark_in_use(p)
        next_address=p+chunk.size;chunk.size=size;chunk.previous_in_use=True
        remainder=p+size;self.chunks[remainder]=Chunk(remaining,0,True)
        following=self.chunks[next_address];following.previous=remaining;following.previous_in_use=False
        self.bins[1].insert(0,remainder)
        if advertise:self.last_remainder=remainder
        return p+8

    def malloc(self,request):
        size=request_size(request);cache_index=self._cache_index(size)
        cacheable=self.tcache_enabled and cache_index<self.parameters['tcache_bins']
        if cacheable and self.tcache[cache_index]:return self.tcache[cache_index].pop(0)+8
        if size<=self.max_fast:
            chain=self.fastbins[(size>>3)-2]
            if chain:
                p=chain.pop(0)
                while chain and self._cache_has_space(size):self.tcache[cache_index].insert(0,chain.pop(0))
                return p+8
        small=size<1008;index=bin_index(size)
        if small:
            chain=self.bins[index]
            if chain:
                p=chain.pop();self._mark_in_use(p)
                while chain and self._cache_has_space(size):
                    other=chain.pop();self._mark_in_use(other);self.tcache[cache_index].insert(0,other)
                return p+8
        elif self.have_fastchunks:self._consolidate()
        while True:
            return_cached=False;unsorted_count=0;iterations=0
            while self.bins[1]:
                p=self.bins[1][-1];chunk=self.chunks[p]
                if small and len(self.bins[1])==1 and p==self.last_remainder and chunk.size>size+16:
                    self.bins[1].pop();return self._split(p,size,True)
                self.bins[1].pop()
                if chunk.size==size:
                    self._mark_in_use(p)
                    if self._cache_has_space(size):
                        self.tcache[cache_index].insert(0,p);return_cached=True;continue
                    return p+8
                self._insert_bin(p);unsorted_count+=1
                limit=self.parameters['tcache_unsorted_limit']
                if return_cached and limit and unsorted_count>limit:return self.tcache[cache_index].pop(0)+8
                iterations+=1
                if iterations>=10000:break
            if return_cached:return self.tcache[cache_index].pop(0)+8
            if not small:
                chain=self.bins[index]
                suitable=[p for p in chain if self.chunks[p].size>=size]
                if suitable:
                    best=min(self.chunks[p].size for p in suitable)
                    p=next(p for p in suitable if self.chunks[p].size==best)
                    position=chain.index(p)
                    if position+1<len(chain)and self.chunks[chain[position+1]].size==best:p=chain[position+1]
                    chain.remove(p);return self._split(p,size)
            for chain in self.bins[index+1:]:
                if chain:
                    p=chain.pop();return self._split(p,size,small)
            top=self.chunks[self.top]
            if top.size>=size+16:
                p=self.top;remaining=top.size-size;top.size=size;top.previous_in_use=True
                self.top=p+size;self.chunks[self.top]=Chunk(remaining,0,True)
                return p+8
            if self.have_fastchunks:self._consolidate();continue
            if size>=self.parameters['mmap_threshold'] and self.parameters['n_mmaps']<self.parameters['n_mmaps_max']:
                raise SystemAllocationRequired(f'mmap required for {request} bytes (chunk {size})')
            if self.flags&2:raise SystemAllocationRequired('Noncontiguous brk extension required')
            end=self.top+top.size
            extra=(size+self.parameters['top_pad']+16-top.size+4095)&~4095
            if any(start<end+extra and finish>end for start,finish in self.ranges):
                raise SystemAllocationRequired('Contiguous brk extension overlaps a mapping')
            top.size+=extra;self.system_mem+=extra

    def _merge(self,p):
        chunk=self.chunks[p];size=chunk.size;next_address=p+size
        if not chunk.previous_in_use:
            previous=p-chunk.previous;self._unlink(previous)
            size+=self.chunks[previous].size;del self.chunks[p];p=previous
        if next_address==self.top:
            size+=self.chunks[self.top].size;del self.chunks[self.top];self.top=p
        else:
            next_chunk=self.chunks[next_address];after=next_address+next_chunk.size
            if not self.chunks[after].previous_in_use:
                self._unlink(next_address);size+=next_chunk.size;del self.chunks[next_address]
            self.chunks[p+size].previous=size;self.chunks[p+size].previous_in_use=False
            self.bins[1].insert(0,p)
        self.chunks[p].size=size;self.chunks[p].previous_in_use=True
        return size

    def _consolidate(self):
        self.have_fastchunks=False
        for chain in self.fastbins:
            while chain:self._merge(chain.pop(0))

    def free(self,address):
        if not address:return
        p=address-8
        if p not in self.chunks:raise ValueError('Unknown allocation')
        size=self.chunks[p].size
        if self._cache_has_space(size):self.tcache[self._cache_index(size)].insert(0,p);return
        if size<=self.max_fast:
            self.fastbins[(size>>3)-2].insert(0,p);self.have_fastchunks=True;return
        size=self._merge(p)
        if size>=65536:
            if self.have_fastchunks:self._consolidate()
            if self.chunks[self.top].size>=self.parameters['trim_threshold']:
                top=self.chunks[self.top]
                extra=max(0,top.size-16-1-self.parameters['top_pad'])&~4095
                top.size-=extra;self.system_mem-=extra

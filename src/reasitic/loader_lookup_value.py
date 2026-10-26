"""Ordinary ELF lookup values and non-stack stores from live process metadata.

Source algorithm: glibc 2.39 elf/dl-lookup.c, Copyright (C) 1995-2024 Free
Software Foundation, Inc., LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt.
Uses the same ELF readers as the complete i386 ABI implementation. This
semantic entry has no caller CPU/stack/FP implementation; those full targets
remain failing assertions, never copied or excluded from continuing audits.
"""
from .loader_lookup_storage import LoaderLookup,gnu_hash,elf_hash


class LoaderLookupValue(LoaderLookup):
    def value(self,name,undef_map,ref,scopes,version=0,*,type_class=1,flags=1,skip_map=0):
        m=self.m
        if m.u32(self.got-0x488):raise NotImplementedError('Loader debug output is not implemented')
        if version and flags&2:raise ValueError('Versioned lookup cannot request newest unversioned symbol')
        counter=self.got+0x5f4;self._put(counter,m.u32(counter)+1)
        hashed=gnu_hash(self._string(name));old_hash=None;weak=None;seen_scopes=set();first=True
        while m.u32(scopes):
            if scopes in seen_scopes:raise ValueError('Cyclic loader scope vector')
            seen_scopes.add(scopes);scope=m.u32(scopes);lst=m.u32(scope);count=m.u32(scope+4);start=0
            if first and skip_map:
                while start<count and m.u32(lst+4*start)!=skip_map:start+=1
                if start==count:raise ValueError('skip_map absent from first loader scope')
            first=False
            for i in range(start,count):
                map_=m.u32(m.u32(lst+4*i)+20)
                if map_==skip_map or(type_class&2 and not self._byte(map_+420)&3):continue
                if self._byte(map_+422)&4 and(not undef_map or not self._byte(undef_map+422)&4):continue
                buckets=m.u32(map_+392)
                if not buckets:continue
                symtab=self._dynamic(map_,6);strtab=self._dynamic(map_,5);bloom=m.u32(map_+404);gnu=bool(bloom);chain=0
                if gnu:
                    word=m.u32(bloom+4*((hashed>>5)&m.u32(map_+396)));shift=m.u32(map_+400)&31
                    if not(word>>(hashed&31)&word>>((hashed>>shift)&31)&1):continue
                    index=m.u32(m.u32(map_+408)+4*(hashed%buckets))
                    if not index:continue
                    chain=(m.u32(map_+412)+4*index)&0xffffffff
                else:
                    if old_hash is None:old_hash=elf_hash(self._string(name))
                    index=m.u32(m.u32(map_+412)+4*(old_hash%buckets))
                symbol=0;versions=[];seen=set()
                while index:
                    if index in seen:raise ValueError('Cyclic ELF symbol hash chain')
                    seen.add(index);hashword=m.u32(chain)if gnu else 0
                    if not gnu or((hashword^hashed)>>1)==0:
                        candidate=symtab+16*index;kind=self._byte(candidate+12)&15;shndx=m.u16(candidate+14)
                        valid=not((not m.u32(candidate+4)and shndx!=0xfff1 and kind!=6)or(type_class&int(shndx==0))or kind not in(0,1,2,5,6,10))
                        if valid and(candidate==ref or not self._compare_strings(strtab+m.u32(candidate),name)):
                            verstab=m.u32(map_+452)
                            if version:
                                if not verstab:
                                    filename=m.u32(version+12)
                                    if filename:
                                        names=[m.u32(map_+4)];p=m.u32(map_+28);visited=set()
                                        while p:
                                            if p in visited:raise ValueError('Cyclic ELF library name chain')
                                            visited.add(p);names.append(m.u32(p));p=m.u32(p+4)
                                        if any(not self._compare_strings(filename,p)for p in names):raise ValueError('Required ELF version missing from its provider')
                                else:
                                    versym=m.u16(verstab+2*index);v=m.u32(map_+384)+16*(versym&0x7fff);hash_=m.u32(v+4)
                                    different=hash_!=m.u32(version+4)or bool(self._compare_strings(m.u32(v),m.u32(version)))
                                    if different and(m.u32(version+8)or hash_ or versym&0x8000):valid=False
                            elif verstab:
                                versym=m.u16(verstab+2*index)
                                if versym&0x7fff >=(2 if flags&2 else 3):
                                    if not versym&0x8000:versions.append(candidate)
                                    valid=False
                            if valid:symbol=candidate;break
                    if gnu:
                        chain+=4;index+=1
                        if hashword&1:break
                    else:index=m.u32(m.u32(map_+408)+4*index)
                if not symbol and len(versions)==1:symbol=versions[0]
                if not symbol:continue
                visibility=self._byte(symbol+13)&3
                if visibility in(1,2):continue
                if visibility==3 and undef_map:raise NotImplementedError('Protected loader binding needs its diagnostic/copy path')
                binding=self._byte(symbol+12)>>4
                if binding==10:raise NotImplementedError('GNU unique loader table mutation is not implemented')
                if binding==2 and m.u32(self.got-0x454):
                    if weak is None:weak=(map_,symbol)
                    continue
                if binding not in(1,2):continue
                return self._finish_value(map_,symbol,ref)
            scopes+=4
        if weak is not None:return self._finish_value(*weak,ref)
        raise NotImplementedError('Unresolved ELF symbol exception/weak return path is not implemented')

    def _finish_value(self,provider,symbol,ref):
        if ref and self._byte(ref+13)&3==3:raise NotImplementedError('Protected reference lookup is not implemented')
        if self._byte(provider+420)&3==2:raise NotImplementedError('dlopen dependency mutation is not implemented')
        if not self.m.u32(provider+536):self._put(provider+536,1)
        return dict(provider=provider,symbol=symbol)

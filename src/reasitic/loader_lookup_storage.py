"""ELF symbol lookup and pinned i386 loader stack stores.

Follows glibc 2.39 elf/dl-lookup.c, Copyright (C) 1995-2024 Free Software
Foundation, Inc., LGPL-2.1-or-later; see web/GLIBC-LGPL-2.1.txt.
Python translation Copyright (C) 2026 pyASITIC authors. ABI offsets refer to
the documented Ubuntu i386 loader build. Symbol names, hash chains, versions,
scope order and retained bytes are read from earlier guest memory. No native
lookup outputs, machine code or per-symbol answer tables are executed/loaded.
"""
from .signal_install_storage import add_flags


def gnu_hash(name):
    value=5381
    for byte in name:value=(33*value+byte)&0xffffffff
    return value


def elf_hash(name):
    value=0
    for byte in name:
        value=((value<<4)+byte)&0xffffffff;high=value&0xf0000000
        value=(value^(high>>24))&~high
    return value


class LoaderLookup:
    """One process's loader memory; successful ordinary lazy PLT lookups.

    Debug printing, protected/unique binding and dlopen dependency mutation
    require their own source paths. They raise explicitly instead of returning
    an approximate symbol. ELF IFUNC addresses are returned as symbols: the
    later _dl_fixup resolver invocation belongs to a separate call boundary.
    """
    def __init__(self,memory,base):self.m,self.base,self.got=memory,base,base+0x33fe8
    def _put(self,address,value):self.m.put_u32(address,value)
    def _words(self,p,values):
        for i,v in enumerate(values):self._put(p+4*i,v)
    def _byte(self,p):return self.m.read(p,1)[0]
    def _string(self,p):
        value=bytearray()
        for i in range(1048576):
            byte=self._byte(p+i)
            if not byte:return bytes(value)
            value.append(byte)
        raise ValueError('Unterminated ELF string')
    def _strcmp(self,stack,left,right,pc):
        # Loader-local byte strcmp has no frame or stores beyond CALL.
        self._put(stack-12,right);self._put(stack-16,left);self._put(stack-20,self.base+pc)
        return self._compare_strings(left,right)
    def _compare_strings(self,left,right):
        # Stop at the first differing byte, just as the native byte loop does;
        # an unread, unmapped tail must not fault a completed comparison.
        for i in range(1048576):
            a,b=self._byte(left+i),self._byte(right+i)
            if a!=b:return (a>b)-(a<b)
            if not a:return 0
        raise ValueError('Unterminated ELF string comparison')
    def _name_match(self,stack,name,map_,*,esi,ebx):
        m=self.m;s=stack
        self._put(s-4,esi);self._put(s-8,ebx);local=s-20
        def compare(other,pc):
            self._put(local-4,other);self._put(local-8,name);self._put(local-12,self.base+pc)
            return not self._compare_strings(name,other)
        if compare(m.u32(map_+4),0xb77a):return True
        link=m.u32(map_+28);seen=set()
        while link:
            if link in seen:raise ValueError('Cyclic ELF library name chain')
            seen.add(link)
            if compare(m.u32(link),0xb7a2):return True
            link=m.u32(link+4)
        return False
    def _check_match(self,h,*,name,ref,version,flags,type_class,symbol,index,strtab,map_,gnu,chain,new_hash):
        m=self.m;c=h-80;entry=h-36
        # Eight stack arguments follow the three regparm arguments. Caller
        # register allocation differs for GNU and traditional ELF hash walks.
        num,versioned=h+0x58,h+0x5c
        self._words(h-32,(flags,type_class,symbol,index,strtab,map_,versioned,num))
        self._put(entry,self.base+(0xa019 if gnu else 0x9eea))
        saved=(new_hash,chain,symbol-16*index,map_)if gnu else(versioned,index,num,map_)
        for offset,value in zip((4,8,12,16),saved):self._put(entry-offset,value)
        self._put(c+12,self.got)
        info=self._byte(symbol+12);kind=info&15;shndx=m.u16(symbol+14)
        if (not m.u32(symbol+4)and shndx!=0xfff1 and kind!=6)or(type_class&int(shndx==0))or kind not in (0,1,2,5,6,10):return 0
        if symbol!=ref and self._strcmp(c,strtab+m.u32(symbol),name,0x9b88):return 0
        verstab=m.u32(map_+452)
        if version:
            if not verstab:
                filename=m.u32(version+12)
                if filename:
                    self._put(c-12,map_);self._put(c-16,filename);self._put(c-20,self.base+0x9c88)
                    if self._name_match(c-20,filename,map_,esi=version,ebx=symbol):raise ValueError('Required ELF version missing from its provider')
            else:
                versym=m.u16(verstab+2*index);v=m.u32(map_+384)+16*(versym&0x7fff);hash_=m.u32(v+4)
                different=hash_!=m.u32(version+4)
                if not different:different=bool(self._strcmp(c,m.u32(v),m.u32(version),0x9c44))
                if different and(m.u32(version+8)or hash_ or versym&0x8000):return 0
        elif verstab:
            versym=m.u16(verstab+2*index)
            if versym&0x7fff >= (2 if flags&2 else 3):
                if not versym&0x8000:
                    count=m.u32(num);self._put(num,count+1)
                    if not count:self._put(versioned,symbol)
                return 0
        return symbol
    def _dynamic(self,map_,tag):
        p=self.m.u32(map_+32+4*tag)
        if not p:return 0
        return self.m.u32(p+4)+(self.m.u32(map_)if self._byte(map_+422)&32 else 0)
    def _do_lookup(self,local,*,name,new_hash,ref,scope,start,version,type_class,flags,skip_map,undef_map,result,old_hash,scope_pointer):
        m=self.m;entry=local-52;h=entry-124
        self._words(local-48,(ref,result,scope,start,version,flags,skip_map,type_class,undef_map))
        self._put(entry,self.base+0xa7de)
        for offset,value in zip((4,8,12,16),(result,old_hash,scope_pointer,new_hash)):self._put(entry-offset,value)
        count=m.u32(scope+4);lst=m.u32(scope)
        for offset,value in ((0x20,name),(0x18,self.got),(0x28,new_hash),(0x34,old_hash),(0xc,count),(0x30,new_hash&31),(0x2c,new_hash>>5),(0x10,type_class&2)):
            self._put(h+offset,value)
        for i in range(start,count):
            map_=m.u32(m.u32(lst+4*i)+20)
            if map_==skip_map or(type_class&2 and not self._byte(map_+420)&3):continue
            if self._byte(map_+422)&4 and(not undef_map or not self._byte(undef_map+422)&4):continue
            buckets=m.u32(map_+392);self._put(h+0x24,buckets)
            if not buckets:continue
            self._put(h+0x58,0);self._put(h+0x5c,0)
            symtab=self._dynamic(map_,6);strtab=self._dynamic(map_,5)
            self._put(h+0x14,symtab);self._put(h+0x1c,strtab)
            bloom=m.u32(map_+404);gnu=bool(bloom);chain=0
            if gnu:
                word=m.u32(bloom+4*((new_hash>>5)&m.u32(map_+396)));shift=m.u32(map_+400)&31
                if not(word>>(new_hash&31)&word>>((new_hash>>shift)&31)&1):continue
                index=m.u32(m.u32(map_+408)+4*(new_hash%buckets))
                if not index:continue
                self._put(h+0x3c,lst);self._put(h+0x8c,i)
                self._put(h+0x24,h+0x58);self._put(h+0x38,h+0x5c)
                chain=(m.u32(map_+412)+4*index)&0xffffffff
            else:
                hash_=m.u32(old_hash)
                if hash_==0xffffffff:hash_=elf_hash(self._string(name));self._put(old_hash,hash_)
                index=m.u32(m.u32(map_+412)+4*(hash_%buckets))
                if not index:continue
                self._put(h+0x24,lst);self._put(h+0x8c,i)
            symbol=0;seen=set()
            while index:
                if index in seen:raise ValueError('Cyclic ELF symbol hash chain')
                seen.add(index)
                hashword=m.u32(chain)if gnu else 0
                if not gnu or((hashword^new_hash)>>1)==0:
                    symbol=self._check_match(h,name=name,ref=ref,version=version,flags=flags,type_class=type_class,symbol=symtab+16*index,index=index,strtab=strtab,map_=map_,gnu=gnu,chain=chain,new_hash=new_hash)
                    if symbol:break
                if gnu:
                    chain+=4;index+=1
                    if hashword&1:break
                else:index=m.u32(m.u32(map_+408)+4*index)
            if not symbol and m.u32(h+0x58)==1:symbol=m.u32(h+0x5c)
            if not symbol:continue
            visibility=self._byte(symbol+13)&3
            if visibility in (1,2):continue
            if visibility==3 and undef_map:raise NotImplementedError('Protected loader binding needs its diagnostic/copy path')
            binding=self._byte(symbol+12)>>4
            if binding==10:raise NotImplementedError('GNU unique loader table mutation is not implemented')
            if binding==2 and m.u32(self.got-0x454):
                if not m.u32(result):self._words(result,(symbol,map_))
                continue
            if binding not in (1,2):continue
            self._words(result,(symbol,map_));return True
        return False
    def lookup(self,registers):
        """Execute _dl_lookup_symbol_x from its earlier C ABI entry state."""
        m=self.m;s=registers['esp'];name,undef_map,ref,scopes,version,type_class,flags,skip_map=(m.u32(s+4+4*i)for i in range(8))
        if m.u32(self.got-0x488):raise NotImplementedError('Loader debug output is not implemented')
        if version and flags&2:raise ValueError('Versioned lookup cannot request newest unversioned symbol')
        if not m.u32(ref):raise NotImplementedError('Lookup without an earlier PLT reference needs its own return-register path')
        local=s-108;new_hash=gnu_hash(self._string(name));old_hash=local+56;result=local+60
        for offset,key in ((4,'ebp'),(8,'edi'),(12,'esi'),(16,'ebx')):self._put(s-offset,registers[key])
        for offset,value in ((8,self.got),(12,24),(56,0xffffffff),(60,0),(64,0)):
            self._put(local+offset,value)
        counter=self.got+0x5f4;self._put(counter,m.u32(counter)+1)
        first=m.u32(scopes);start=0
        if skip_map:
            lst=m.u32(first);count=m.u32(first+4)
            while start<count and m.u32(lst+4*start)!=skip_map:start+=1
            if start==count:raise ValueError('skip_map absent from first loader scope')
        self._put(local+16,start);pointer=scopes;seen=set()
        while m.u32(pointer):
            if pointer in seen:raise ValueError('Cyclic loader scope vector')
            seen.add(pointer)
            if self._do_lookup(local,name=name,new_hash=new_hash,ref=m.u32(ref),scope=m.u32(pointer),start=start,version=version,type_class=type_class,flags=flags,skip_map=skip_map,undef_map=undef_map,result=result,old_hash=old_hash,scope_pointer=pointer):break
            pointer+=4;start=0
        symbol,provider=m.u32(result),m.u32(result+4)
        if not symbol:raise NotImplementedError('Unresolved ELF symbol exception/weak return path is not implemented')
        original=m.u32(ref)
        if original and self._byte(original+13)&3==3:raise NotImplementedError('Protected reference lookup is not implemented')
        if self._byte(provider+420)&3==2:raise NotImplementedError('dlopen dependency mutation is not implemented')
        if not m.u32(provider+536):self._put(provider+536,1)
        self._put(ref,symbol)
        after=dict(registers);after.update(eax=provider,ecx=m.u32(local+16),edx=(~self._byte(original+13)&3)if original else 0,esp=s+4,eip=m.u32(s),eflags=add_flags(local,92,registers['eflags']))
        return dict(registers=after,symbol=symbol,provider=provider)

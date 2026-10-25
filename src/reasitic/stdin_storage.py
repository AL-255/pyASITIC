"""Native narrow fgets/getline/uflow callers on the continuing guest memory.

Follows glibc 2.39 iofgets.c, iogetline.c, genops.c and fileops.c,
Copyright (C) 1993-2024 Free Software Foundation, Inc., LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt. The legacy streambuf wrappers use their pinned
i386 ABI. Additional stat/allocator/read paths remain unfinished.
"""
from .dispatch_storage import logical_flags
from .signal_install_storage import add_flags,subtract_flags
from .command_storage import string


class StdinStorage:
    def __init__(self,memory,loader,context,profile,*,libc_base,tls_base,heap=None):
        self.m,self.loader,self.context,self.profile=memory,loader,context,profile
        self.heap=heap
        self.libc,self.tls,self.got=libc_base,tls_base,libc_base+0x22fe34
        self.legacy=next(x for x in context['maps']if x['name'].endswith('/libstdc++-libc6.1-1.so.2'))
        if self.legacy['plt']['elf_sha256']!='bca97b602b1eec9f0b591bec0fa4dc5f84f1382636cc8f10094f1da8a3c77d34':
            raise NotImplementedError('Stdin wrappers need the pinned legacy streambuf ABI')
        self.legacy_base=memory.u32(self.legacy['address']);self.legacy_got=loader._dynamic(self.legacy['address'],3)
        stat=profile['statx']['fields']if 'statx'in profile else profile['stdin_stat']
        block=stat['blksize']if 'statx'in profile else stat['st_blksize']
        if(stat['mode']if 'statx'in profile else stat['st_mode'])&0o170000!=0o100000:raise NotImplementedError('Stdin allocation needs regular-file stat metadata')
        self.buffer_size=min(8192,block)if block>0 else 8192

    def _bind(self,registers,name,provider=None):
        provider=provider or next(x for x in self.context['maps']if x['address']==self.context['main_map'])
        return self.loader.bind_import(registers,provider['address'],name,provider['plt'])['registers']

    def _guard(self,registers,return_pc):
        """The accepted-foreign-vtable fast path, derived from earlier TLS/GOT."""
        m=self.m;entry=registers['esp']-4;local=entry-44;target=self.libc+0x81640
        encoded=m.u32(self.got+0x1a30);decoded=((encoded>>9)|(encoded<<23))&0xffffffff
        if decoded^m.u32(self.tls+24)!=target:raise NotImplementedError('Foreign-vtable validation needs its loader-namespace branch')
        m.put_u32(entry,return_pc);m.put_u32(entry-4,registers['ebx']);m.put_u32(entry-8,self.libc+0x8164a)
        m.put_u32(local+28,m.u32(self.tls+20))
        return dict(registers,eax=0,edx=target,eip=return_pc,eflags=add_flags(local,40,registers['eflags']))

    def _wrapper(self,registers,offset,addend,name,arguments):
        """Legacy PIC wrapper, including its actual saved EBX and call args."""
        m=self.m;entry=registers['esp'];f=entry-4;pc=self.legacy_base+offset
        m.put_u32(f,registers['ebp']);m.put_u32(f-4,registers['ebx']);m.put_u32(f-8,pc+9)
        for i,value in enumerate(reversed(arguments)):m.put_u32(f-8-4*i,value)
        s=f-8-4*len(arguments);m.put_u32(s,pc+21+3*len(arguments))
        r=dict(registers,ebp=f,ebx=self.legacy_got,esp=s,eflags=add_flags(pc+9,addend,registers['eflags']))
        return self._bind(r,name,self.legacy)

    def enter(self,registers):
        m=self.m;r=self._bind(registers,b'fgets');s=r['esp'];f=s-4;self.entry=dict(r);self.fgets_frame=f
        if r['eip']!=self.libc+0x75f70:raise NotImplementedError('Stdin fgets implementation differs from the pinned ABI')
        self.line=m.u32(s+4);self.limit=m.u32(s+8)-1;self.stream=m.u32(s+12);a=self.stream;self.flags=m.u32(a)
        if self.limit<=0 or m.u32(a+28)or m.u32(a+4)!=m.u32(a+8)or m.u32(a+36)or m.u32(a+48)or self.flags&0x917:
            raise NotImplementedError('Stdin ABI needs the first buffered narrow read without backup/error state')
        lock=m.u32(a+72)
        if any(m.u32(lock+i)for i in (0,4,8))or m.u32(self.tls+12):raise NotImplementedError('Stdin fgets needs its uncontended single-threaded lock path')
        m.put_u32(f,r['ebp'])
        for offset,key in ((4,'edi'),(8,'esi'),(12,'ebx')):m.put_u32(f-offset,r[key])
        m.put_u32(f-32,self.got);m.put_u32(f-28,self.flags&32)
        m.put_u32(lock,1);m.put_u32(lock+8,m.u32(self.tls+8));m.put_u32(a,self.flags&~32)
        for offset,value in ((56,1),(60,10),(64,self.limit),(68,self.line),(72,a),(76,self.libc+0x7600b)):
            m.put_u32(f-offset,value)
        getline=f-76
        for offset,value in ((24,0),(28,1),(32,10),(36,self.limit),(40,self.line),(44,a),(48,self.libc+0x774c2)):
            m.put_u32(getline-offset,value)
        info=getline-48;local=info-44;self.info_local=local
        for offset,value in ((4,f),(8,self.flags&32),(12,a),(16,self.limit)):m.put_u32(info-offset,value)
        m.put_u32(local+12,self.got);m.put_u32(local+8,self.line)
        mode=m.u32(a+104);used=m.u32(self.got+0x11c)
        if not mode:
            if not used:raise NotImplementedError('Stdin orientation needs the legacy compatibility branch')
            m.put_u32(a+104,0xffffffff)
        elif mode!=0xffffffff:raise NotImplementedError('Stdin is wide-oriented')
        m.put_u32(local-16,a);m.put_u32(local-20,self.libc+0x77381)
        uflow=local-20
        for offset,value in ((4,self.limit),(8,0),(12,0),(16,self.libc+0x85220)):m.put_u32(uflow-offset,value)
        vt=m.u32(a+148);self.vtable=vt
        if m.read(a+70,1)!=b'\0'or m.u32(vt+20)!=self.legacy_base+0x28ba4:raise NotImplementedError('Stdin uflow vtable branch is not bound')
        r=dict(r,eax=vt-(self.got-0x734),ebx=self.got,ecx=used,edx=self.got-0x734,esi=a,edi=vt,ebp=a,esp=uflow-12)
        r=self._guard(r,self.libc+0x853bd)
        r.update(eax=m.u32(vt+20),ebx=0,esi=0,edi=self.limit,esp=uflow)
        r=self._wrapper(r,0x28ba4,0x1600b,b'_IO_default_uflow',[a])
        if r['eip']!=self.libc+0x85510:raise NotImplementedError('Stdin default uflow interposition is not bound')
        sd=r['esp'];m.put_u32(sd-4,r['esi']);m.put_u32(sd-8,r['ebx'])
        r=dict(r,ebx=a,esi=vt,edx=self.got-0x734,esp=sd-12)
        r=self._guard(r,self.libc+0x8556d)
        m.put_u32(sd-28,a);m.put_u32(sd-32,self.libc+0x8554a);r['esp']=sd-32
        if m.u32(vt+16)!=self.legacy_base+0x220f4:raise NotImplementedError('Stdin underflow vtable branch is not bound')
        r=self._wrapper(r,0x220f4,0x1cabb,b'_IO_file_underflow',[a])
        if r['eip']!=self.libc+0x82de0:raise NotImplementedError('Stdin file underflow interposition is not bound')
        self.underflow=dict(r);u=r['esp']-4;self.underflow_frame=u
        m.put_u32(u,r['ebp']);m.put_u32(u-4,r['edi']);m.put_u32(u-8,r['esi']);m.put_u32(u-12,r['ebx'])

    def before_allocate(self):
        m=self.m;u=self.underflow_frame;local=u-40;a=self.stream
        m.put_u32(local-16,a);m.put_u32(local-20,self.libc+0x82fe4)
        if 'statx'in self.profile:
            from .file_allocation import FileAllocation
            self.allocation=FileAllocation(self)
            r=dict(self.underflow,eax=0,edx=0,edi=self.got,esi=a,ebp=u,esp=local-20,eip=self.libc+0x85440,
                eflags=subtract_flags(local,12,self.underflow['eflags']))
            self.malloc_entry=self.allocation.before_malloc(r)
            if self.profile.get('malloc_abi'):
                from .malloc_storage import MallocStorage
                if self.heap is None:raise ValueError('Malloc ABI requires the continuing guest heap')
                self.malloc_storage=MallocStorage(self.heap,m,libc_base=self.libc,tls_base=self.tls)
                self.malloc_storage.enter(self.malloc_entry)

    def after_allocate(self,buffer,capacity):
        if 'statx'in self.profile:
            if self.profile.get('malloc_abi'):r=self.malloc_storage.returned(buffer)
            else:
                # Older inputs lack malloc controls. Its internal ABI remains
                # absent there; _IO_setb overwrites volatile ECX/EDX before use.
                r=dict(self.malloc_entry,eax=buffer,esp=self.malloc_entry['esp']+4,eip=self.libc+0x75523)
            self.allocation.after_malloc(r)

    def before_read(self,buffer,capacity):
        m=self.m;u=self.underflow_frame;local=u-40;a=self.stream;vt=self.vtable
        m.put_u32(local-16,a);m.put_u32(local-20,self.libc+0x82f0f)
        sw=local-20;m.put_u32(sw-4,a);m.put_u32(sw-8,self.got-0x734)
        # Source _IO_switch_to_get_mode, followed by underflow's area reset.
        m.put_u32(a+12,buffer);m.put_u32(a,m.u32(a)&~0x800)
        for offset in (4,8,12,16,20,24):m.put_u32(a+offset,buffer)
        r=dict(self.underflow,ebp=u,esp=local,ebx=self.got-0x734,esi=a,edi=vt,ecx=buffer)
        r=self._guard(r,self.libc+0x830b5);r.update(eax=buffer,edx=capacity,esp=local-20)
        for offset,value in ((8,capacity),(12,buffer),(16,a),(20,self.libc+0x82f50)):m.put_u32(local-offset,value)
        if m.u32(vt+56)!=self.legacy_base+0x22190:raise NotImplementedError('Stdin read vtable branch is not bound')
        r=self._wrapper(r,0x22190,0x1ca1f,b'_IO_file_read',[a,buffer,capacity])
        if r['eip']!=self.libc+0x83e40:raise NotImplementedError('Stdin file read interposition is not bound')
        self.buffer=buffer;self.capacity=capacity;self.read_entry=r

    def read_buffer(self,file_data,position):
        if self.profile.get('read_abi'):
            from .read_storage import ReadStorage
            storage=ReadStorage(self.m,libc_base=self.libc,tls_base=self.tls)
            self.read_result=storage.read(self.read_entry,file_data,position)
            return self.read_result['data'],self.read_result['position']
        data=file_data[position:position+self.capacity];self.m.write(self.buffer,data)
        return data,position+len(data)

    def returned(self,count):
        m=self.m;a=self.stream;local=self.info_local
        text=m.read(self.line,count)
        if not text.endswith(b'\n')or count<2:raise NotImplementedError('Stdin getline EOF/delimiter-first return ABI is not bound')
        # The first char comes from uflow; getline scans/copies the remaining
        # buffered bytes. Child memchr/memcpy ISA state remains separate work.
        for offset,value in ((8,count-1),(12,10),(16,self.buffer+1),(20,self.libc+0x77343)):
            m.put_u32(local-offset,value)
        m.put_u32(local+8,self.buffer+count)
        for offset,value in ((8,count-1),(12,self.buffer+1),(16,self.line+1),(20,self.libc+0x773f6)):
            m.put_u32(local-offset,value)
        m.put_u32(a,m.u32(a)|(self.flags&32));lock=m.u32(a+72);m.put_u32(lock+8,0);m.put_u32(lock,0)
        return dict(self.entry,eax=self.line,ecx=m.u32(self.tls+12),edx=lock,esp=self.entry['esp']+4,
                    eip=m.u32(self.entry['esp']),eflags=logical_flags(m.u32(lock+4),self.entry['eflags']))

    def append_newline(self,registers,frame):
        m=self.m;source=0x80b4895;line=self.line
        if string(m,source)!=b'\n':raise ValueError('Native stdio append literal differs')
        for offset,value in ((1040,source),(1044,line),(1048,0x804b617)):m.put_u32(frame-offset,value)
        r=dict(registers,esp=frame-1048,eflags=add_flags(frame-1052,16,registers['eflags']))
        r=self._bind(r,b'strcat')
        if r['eip']!=self.libc+0xb4d20:raise NotImplementedError('Stdin strcat CPU implementation is not bound')
        text=string(m,line);length=len(text)
        if length>=16:raise NotImplementedError('Stdin strcat vector scan needs its SIMD state')
        m.put_u32(r['esp']-4,r['edi']);m.write(line+length,b'\n\0')
        # The implementation's first-16-byte scalar probe and two-byte copy
        # do not modify any XMM register. The final CMP sees the source NUL.
        return dict(r,eax=line,ecx=source,edx=line+length,esp=r['esp']+4,eip=m.u32(r['esp']),
                    eflags=subtract_flags(0,0,r['eflags']))

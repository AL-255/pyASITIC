"""Successful buffered fgets/fprintf stores on the continuing i386 streams.

Follows glibc 2.39 libio fileops/iofgets/iofclose (LGPL-2.1-or-later;
see web/GLIBC-LGPL-2.1.txt). ABI, external bytes and offsets are inputs.
Error/backup/line-buffer paths require their own implementations.
"""
import struct
from .libio_storage import FileStorage


class InputStream:
    def __init__(self,memory,address,data,position,allocate):
        self.memory=memory;self.address=address;self.data=data;self.position=position;self.allocate=allocate

    def readline(self,destination,size,*,abi=None):
        m=self.memory;a=self.address;count=0
        while count<size-1:
            flags,rp,re,rb,wb,wp,we,bb,be=struct.unpack('<9I',m.read(a,36))
            if rp<re and count and abi and abi.profile.get('getline_bytes_abi'):
                copied=abi.buffered_line(destination+count,size-1-count,count)
                count+=copied;break
            if rp>=re:
                if flags&16:break
                if flags&4:raise ValueError('Source fgets stream has no read access')
                if not bb:
                    if abi:abi.before_allocate()
                    capacity=abi.buffer_size if abi else 4096
                    bb=self.allocate('stdin.buffer',capacity);be=bb+capacity
                    if abi:abi.after_allocate(bb,capacity)
                    m.put_u32(a+28,bb);m.put_u32(a+32,be)
                if abi:abi.before_read(bb,be-bb)
                for offset in (4,8,12,16,20,24):m.put_u32(a+offset,bb)
                if abi:data,self.position=abi.read_buffer(self.data,self.position)
                else:
                    data=self.data[self.position:self.position+be-bb];m.write(bb,data);self.position+=len(data)
                if not data:m.put_u32(a,flags|16);break
                rp=bb;re=bb+len(data);m.put_u32(a+8,re)
            value=m.read(rp,1);m.write(destination+count,value);m.put_u32(a+4,rp+1);count+=1
            if value==b'\n':break
        if not count:return None
        m.write(destination+count,b'\0');return m.read(destination,count)


class OutputStream:
    def __init__(self,memory,address,buffer,capacity,abi,fd):
        self.memory=memory;self.address=address;self.buffer=buffer;self.capacity=capacity;self.data=bytearray();self.pointer=0
        storage=FileStorage(memory,abi)
        storage._put(address,'file','_flags',0xfbad3c84)
        storage._put(address,'file','_fileno',fd);storage._put(address,'file','_mode',-1)
        for offset in (4,8,12,16,20,28):memory.put_u32(address+offset,buffer)
        for offset in (24,32):memory.put_u32(address+offset,buffer+capacity)

    def write(self,data):
        data=bytes(data);self.data.extend(data);offset=0
        while offset<len(data):
            if self.pointer==self.capacity:self.pointer=0
            size=min(self.capacity-self.pointer,len(data)-offset)
            self.memory.write(self.buffer+self.pointer,data[offset:offset+size]);self.pointer+=size;offset+=size
        self.memory.put_u32(self.address+20,self.buffer+self.pointer)

    def flush(self):
        self.pointer=0;self.memory.put_u32(self.address+20,self.buffer)

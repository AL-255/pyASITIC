"""Guest-memory storage used by the original COPY's default names.

The binary's inlined libstdc++ 2.9 string/pool code is the reference: Rep
clone/replace at 0x80b1d10/0x80b1ec0, pool chunk allocation at 0x80b1ba0,
and COPY's string expression at 0x80782de. This is a component of the native
heap reconstruction, not the Python UI's string implementation. Initial pool
globals and bytes are explicit caller state. Allocation failure/recovery and
concurrent pool access are outside this single-threaded successful path.
"""


class LegacyStrings:
    def __init__(self,memory,allocate,release,*,nil_address,pool_address):
        self.memory=memory;self.allocate=allocate;self.release=release
        self.nil=nil_address;self.pool=pool_address

    def _slot(self,size):return self.pool+4*((size+7)//8-1)

    def _chunk(self,size,count):
        m=self.memory;start=m.u32(self.pool+64);end=m.u32(self.pool+68)
        available=(end-start)&0xffffffff;total=size*count
        if available>=total:m.put_u32(self.pool+64,start+total);return start,count
        if available>=size:
            count=available//size;m.put_u32(self.pool+64,start+count*size);return start,count
        amount=2*total+((m.u32(self.pool+72)//16+7)&~7)
        if available:
            slot=self._slot(available);m.put_u32(start,m.u32(slot));m.put_u32(slot,start)
        start=self.allocate(amount,'malloc');m.put_u32(self.pool+64,start)
        m.put_u32(self.pool+72,m.u32(self.pool+72)+amount);m.put_u32(self.pool+68,start+amount)
        return self._chunk(size,count)

    def get(self,size):
        if size>128:return self.allocate(size,'malloc')
        m=self.memory;slot=self._slot(size);address=m.u32(slot)
        if address:m.put_u32(slot,m.u32(address));return address
        size=(size+7)&~7;address,count=self._chunk(size,20)
        if count>1:
            m.put_u32(slot,address+size)
            for i in range(1,count):m.put_u32(address+i*size,address+(i+1)*size if i+1<count else 0)
        return address

    def put(self,address,size):
        if size>128:self.release(address,'malloc');return
        m=self.memory;slot=self._slot(size);m.put_u32(address,m.u32(slot));m.put_u32(slot,address)

    def _new(self,text):
        capacity=16
        while capacity<len(text)+1:capacity*=2
        address=self.get(capacity+16);m=self.memory
        # Rep's spare bytes and text beyond its length are not initialized.
        m.put_u32(address+4,capacity);m.put_u32(address+8,1);m.write(address+12,b'\0')
        m.write(address+16,text);m.put_u32(address,len(text));return address+16

    def copy(self,pointer):
        m=self.memory
        if m.read(pointer-4,1)!=b'\0':return self._new(m.read(pointer,m.u32(pointer-16)))
        m.put_u32(pointer-8,m.u32(pointer-8)+1);return pointer

    def destroy(self,pointer):
        m=self.memory;references=m.u32(pointer-8);m.put_u32(pointer-8,references-1)
        if references==1:self.put(pointer-16,m.u32(pointer-12)+16)

    def replace(self,pointer,position,count,text):
        m=self.memory;length=m.u32(pointer-16)
        if position>length:raise ValueError('Legacy string replace position is out of range')
        count=min(count,length-position);needed=length-count+len(text)+1
        m.write(pointer-4,b'\0');capacity=m.u32(pointer-12)
        resize=m.u32(pointer-8)>1 or needed>capacity or (2*needed<capacity if needed>16 else capacity>32)
        value=m.read(pointer,position)+bytes(text)+m.read(pointer+position+count,length-position-count)
        if resize:
            result=self._new(value);self.destroy(pointer);return result
        m.write(pointer,value);m.put_u32(pointer-16,len(value));return pointer

    def c_string(self,pointer):
        length=self.memory.u32(pointer-16)
        if length:self.memory.write(pointer+length,b'\0')
        return self.memory.read(pointer,length).split(b'\0',1)[0]

    def default_name(self,source,exists,random_byte=None):
        # Native expression: a = source; b = a + "_"; c = b; ~b();
        # then collision appends, strcpy(c.c_str()), ~c(), ~a().
        first=self.copy(self.nil+16)
        first=self.replace(first,0,0xffffffff,source)
        temporary=self.copy(first)
        temporary=self.replace(temporary,self.memory.u32(temporary-16),0,b'_')
        result=self.copy(temporary);self.destroy(temporary)
        while exists(self.c_string(result)):
            length=self.memory.u32(result-16)
            if length>79:break
            if random_byte is None:raise NotImplementedError('COPY name collision requires the caller random-byte stream')
            result=self.replace(result,length,0,bytes([random_byte()&255]))
        name=self.c_string(result);self.destroy(result);self.destroy(first);return name

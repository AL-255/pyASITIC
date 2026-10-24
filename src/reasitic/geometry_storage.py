"""Original clone/COPY/JOIN stores into the process's shared guest memory.

Follows geometry.cpp, composite_geometry.cpp and the PI2/CALCTRANS drivers,
with the original binary's libstdc++ naming storage supplied separately.
Source shape records, process heap and scene head are caller inputs. Nothing
here loads observations or initializes unwritten descriptor bytes to zero.
Secondary segment groups are an explicit boundary of this component.
"""
import struct
from .allocation_plan import StorageEvent
from .retained_scalar import Real as R
from .solver import _subdivision


class GeometryStorage:
    def __init__(self,heap,memory,head,*,strings=None):
        self.heap=heap;self.memory=memory;self.head=head;self.strings=strings
        self.events=[];self.addresses={};self.owners={};self.name_serial=0

    def allocate(self,name,size,allocator='scalar'):
        event=StorageEvent('allocate',name,size,allocator);address=self.heap.malloc(size)
        self.events.append((event,address));self.addresses[name]=address;self.owners[address]=name;return address

    def release(self,address,allocator='scalar'):
        self.events.append((StorageEvent('free',self.owners.pop(address),0,allocator),address));self.heap.free(address)

    def string_allocate(self,size,allocator):
        name=f'names.{self.name_serial}';self.name_serial+=1;return self.allocate(name,size,allocator)

    def text(self,address):
        result=bytearray()
        for offset in range(80):
            value=self.memory.read(address+offset,1)
            if value==b'\0':return bytes(result)
            result.extend(value)
        raise ValueError('Native shape name is not NUL terminated within its field')

    def shapes(self):
        address=self.head;seen=set()
        while address:
            if address in seen:raise ValueError('Geometry descriptor chain has a cycle')
            seen.add(address);yield address;address=self.memory.u32(address+0xb0)

    def segments(self,shape):
        address=self.memory.u32(shape+0xa8);seen=set()
        while address:
            if address in seen:raise ValueError('Geometry segment chain has a cycle')
            if self.memory.u32(address+0xe8):raise NotImplementedError('Geometry storage for secondary segment groups is not implemented')
            seen.add(address);yield address;address=self.memory.u32(address+0xec)

    def _number(self,address):return struct.unpack('<d',self.memory.read(address,8))[0]
    def _store(self,address,value):self.memory.write(address,struct.pack('<d',float(value)))
    def _floating_copy(self,destination,source):self._store(destination,R(self._number(source)))

    def descriptor(self,source,name):
        m=self.memory;address=self.allocate(name+'.descriptor',188)
        m.put_u32(address+0xa8,0);m.put_u32(address+0xb4,0);m.write(address+0xb8,b'\0')
        m.put_u32(address+0xb0,self.head);self.head=address
        m.write(address,self.text(source)+b'\0');m.write(address+0x50,m.read(source+0x50,4))
        for offset in (0x54,0x5c,*range(0x70,0xa1,8)):self._floating_copy(address+offset,source+offset)
        m.write(address+0x64,m.read(source+0x64,12));m.put_u32(address+0xac,m.u32(source+0xac));return address

    def prepend(self,shape,data,name):
        m=self.memory;address=self.allocate(name,240);m.write(address,data)
        m.put_u32(address+0xec,m.u32(shape+0xa8));m.put_u32(shape+0xa8,address);m.put_u32(address+0xe8,0);return address

    def reverse(self,shape):
        previous=0
        for address in list(self.segments(shape)):
            self.memory.put_u32(address+0xec,previous);previous=address
        self.memory.put_u32(shape+0xa8,previous)

    def clone(self,source,name,cap_length,length):
        shape=self.descriptor(source,name);index=0
        for address in self.segments(source):
            data=self.memory.read(address,240)
            coordinates=tuple(v for offset in (0,0x44,0x88)for v in struct.unpack_from('<6d',data,offset))
            rows=_subdivision(struct.pack('<20d',cap_length,length,*coordinates))
            if rows is None:self.prepend(shape,data,f'{name}.segment.{index}');index+=1;continue
            for row in rows:
                # Split uses typed copies, unlike the unsplit raw 240-byte copy.
                part=bytearray(data)
                for base in (0,0x88,0x44):
                    for offset in range(base,base+64,8):struct.pack_into('<d',part,offset,float(R(struct.unpack_from('<d',data,offset)[0])))
                for offset in (0xcc,0xd4):struct.pack_into('<d',part,offset,float(R(struct.unpack_from('<d',data,offset)[0])))
                for i,offset in enumerate((0,0x44,0x88)):struct.pack_into('<6d',part,offset,*row[6*i:6*i+6])
                self.prepend(shape,part,f'{name}.segment.{index}');index+=1
        self.reverse(shape);return shape

    def copy(self,source,name):
        if self.strings is None:raise ValueError('Native default COPY names require the caller legacy string pool')
        shape=self.descriptor(source,name)
        value=self.strings.default_name(self.text(source),lambda text:any(self.text(p)==text for p in self.shapes()))
        self.memory.write(shape,value+b'\0')
        for i,address in enumerate(self.segments(source)):self.prepend(shape,self.memory.read(address,240),f'{name}.segment.{i}')
        self.reverse(shape);return shape

    def remove(self,shape):
        m=self.memory;following=m.u32(shape+0xb0)
        if self.head==shape:self.head=following
        else:
            previous=next(p for p in self.shapes()if m.u32(p+0xb0)==shape);m.put_u32(previous+0xb0,following)
        for address in list(self.segments(shape)):self.release(address)
        self.release(shape)

    def join(self,target,source,name):
        # The caller's layer checks must accept this JOIN. No generator or
        # technology-specific special case is used in the actual stores.
        if self.text(target)==self.text(source):raise ValueError('Cannot join a shape to itself')
        m=self.memory;self.reverse(target);index=len(list(self.segments(target)))
        for address in self.segments(source):
            for offset in (0,8,0x18,0x20,0x88,0x90,0xa0,0xa8,0x44,0x4c,0x5c,0x64):
                axis=0x5c if offset in(8,0x20,0x90,0xa8,0x4c,0x64)else 0x54
                self._store(address+offset,(R(self._number(source+axis))-self._number(target+axis))+self._number(address+offset))
            self.prepend(target,m.read(address,240),f'{name}.segment.{index}');index+=1
        if m.u32(target+0x50)==2 and m.u32(source+0x50)<2:
            for offset in(0x54,0x5c,*range(0x70,0x91,8),0xa0):self._floating_copy(target+offset,source+offset)
            m.write(target+0x64,m.read(source+0x64,12));self._store(target+0x98,R(.25)+self._number(source+0x98));m.put_u32(target+0xac,m.u32(source+0xac))
        m.put_u32(target+0x50,21);self.remove(source);self.reverse(target)

    def setup(self,driver,arguments,*,cap_length,length):
        if driver=='pi2':return self.clone(arguments[0],'geometry',cap_length,length),arguments[1]
        if driver!='calctrans':raise ValueError('Unknown geometry setup driver')
        first=self.clone(arguments[0],'clone.first',cap_length,length)
        second=self.clone(arguments[1],'clone.second',cap_length,length)
        target=self.copy(first,'geometry');other=self.copy(second,'copy.second')
        self.reverse(other);self.join(target,other,'geometry');self.remove(first);self.remove(second)
        reference=target if self.text(arguments[0])==self.text(arguments[2])else arguments[2]
        return target,reference

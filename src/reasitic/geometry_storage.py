"""Original clone/COPY/JOIN stores into the process's shared guest memory.

Follows geometry.cpp, composite_geometry.cpp and the PI2/CALCTRANS drivers,
with the original binary's libstdc++ naming storage supplied separately.
Source shape records, process heap and scene head are caller inputs. Nothing
here loads observations or initializes unwritten descriptor bytes to zero.
Primary and secondary links occupy distinct fields, as in the original.
"""
import math,struct
from .allocation_plan import StorageEvent
from .retained_scalar import Real as R
from .solver import _subdivision


class GeometryStorage:
    def __init__(self,heap,memory,head,*,strings=None,selected=0):
        self.heap=heap;self.memory=memory;self.head=head;self.strings=strings;self.selected=selected
        self.events=[];self.addresses={};self.owners={};self.name_serial=0

    def allocate(self,name,size,allocator='scalar'):
        event=StorageEvent('allocate',name,size,allocator);address=self.heap.malloc(size)
        self.events.append((event,address));self.addresses[name]=address;self.owners[address]=name;return address

    def release(self,address,allocator='scalar'):
        self.events.append((StorageEvent('free',self.owners.pop(address,f'initial.{address:x}'),0,allocator),address));self.heap.free(address)

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
            seen.add(address);yield address;address=self.memory.u32(address+0xec)

    def children(self,parent):
        address=self.memory.u32(parent+0xe8);seen=set()
        while address:
            if address in seen:raise ValueError('Geometry secondary chain has a cycle')
            seen.add(address);yield address;address=self.memory.u32(address+0xe8)

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

    def secondary(self,parent,data,name):
        m=self.memory;address=self.allocate(name,240);m.write(address,data)
        m.put_u32(address+0xec,m.u32(parent+0xec));m.put_u32(address+0xe8,m.u32(parent+0xe8));m.put_u32(parent+0xe8,address);return address

    def prepend(self,shape,data,name):
        m=self.memory;address=self.allocate(name,240);m.write(address,data)
        m.put_u32(address+0xec,m.u32(shape+0xa8));m.put_u32(shape+0xa8,address);m.put_u32(address+0xe8,0)
        child=struct.unpack_from('<I',data,0xe8)[0];index=0
        while child:
            original=m.read(child,240);self.secondary(address,original,f'{name}.secondary.{index}');index+=1;child=struct.unpack_from('<I',original,0xe8)[0]
        return address

    def reverse(self,shape):
        if not self.memory.u32(shape+0xa8):self.memory.u32(0xec) # Native empty-chain dereference.
        previous=0
        for address in list(self.segments(shape)):
            self.memory.put_u32(address+0xec,previous);previous=address
        self.memory.put_u32(shape+0xa8,previous)

    def clone(self,source,name,cap_length,length):
        shape=self.descriptor(source,name);index=0
        for address in self.segments(source):
            data=self.memory.read(address,240);children=[self.memory.read(p,240)for p in self.children(address)]
            def length_of(record):
                first=struct.unpack_from('<3d',record);last=struct.unpack_from('<3d',record,24);x,y,z=(R(b)-a for a,b in zip(first,last));return((x*x+y*y)+z*z).sqrt()
            maximum=float(length_of(data))
            for child in children:
                value=length_of(child)
                if value>R(maximum):maximum=float(value)
            if not min(cap_length,length)<maximum:self.prepend(shape,data,f'{name}.segment.{index}');index+=1;continue
            count=math.ceil((R(maximum)/R(length)).value)
            def subdivided(record):
                coordinates=tuple(v for offset in(0,0x44,0x88)for v in struct.unpack_from('<6d',record,offset))
                rows=_subdivision(struct.pack('<20d',cap_length,length,*coordinates),count)
                parts=[]
                for row in rows:
                    # Typed split copies quiet NaNs and clear both links.
                    part=bytearray(record)
                    for base in(0,0x88,0x44):
                        for offset in range(base,base+64,8):struct.pack_into('<d',part,offset,float(R(struct.unpack_from('<d',record,offset)[0])))
                    for offset in(0xcc,0xd4):struct.pack_into('<d',part,offset,float(R(struct.unpack_from('<d',record,offset)[0])))
                    for i,offset in enumerate((0,0x44,0x88)):struct.pack_into('<6d',part,offset,*row[6*i:6*i+6])
                    struct.pack_into('<II',part,0xe8,0,0);parts.append(part)
                return parts
            rows=subdivided(data);branches=[subdivided(child)for child in children]
            for j,row in enumerate(rows):
                parent=self.prepend(shape,row,f'{name}.segment.{index}')
                for ci,branch in enumerate(branches):self.secondary(parent,branch[j],f'{name}.segment.{index}.secondary.{ci}')
                index+=1
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
        for address in list(self.segments(shape)):
            for child in list(self.children(address)):self.release(child)
            self.release(address)
        self.release(shape)

    def join(self,target,source,name):
        # The caller's layer checks must accept this JOIN. No generator or
        # technology-specific special case is used in the actual stores.
        if self.text(target)==self.text(source):raise ValueError('Cannot join a shape to itself')
        m=self.memory;self.reverse(target);index=len(list(self.segments(target)))
        for address in self.segments(source):
            for record in(address,*self.children(address)):self.translate(record,target,source)
            self.prepend(target,m.read(address,240),f'{name}.segment.{index}');index+=1
        if m.u32(target+0x50)==2 and m.u32(source+0x50)<2:
            for offset in(0x54,0x5c,*range(0x70,0x91,8),0xa0):self._floating_copy(target+offset,source+offset)
            m.write(target+0x64,m.read(source+0x64,12));self._store(target+0x98,R(.25)+self._number(source+0x98));m.put_u32(target+0xac,m.u32(source+0xac))
        m.put_u32(target+0x50,21);self.remove(source);self.reverse(target)

    def translate(self,address,target,source):
        for offset in(0,8,0x18,0x20,0x88,0x90,0xa0,0xa8,0x44,0x4c,0x5c,0x64):
            axis=0x5c if offset in(8,0x20,0x90,0xa8,0x4c,0x64)else 0x54
            self._store(address+offset,(R(self._number(source+axis))-self._number(target+axis))+self._number(address+offset))

    def join_shunt(self,target,source,name):
        m=self.memory;self.reverse(target);self.reverse(source);cursor=m.u32(target+0xa8)
        for i,address in enumerate(self.segments(source)):
            self.translate(address,target,source);self.secondary(cursor,m.read(address,240),f'{name}.secondary.{i}');cursor=m.u32(cursor+0xec)
        self.remove(source);self.reverse(target)

    def dispatch_shunt(self,arguments,name='shunt'):
        target=arguments[0]
        selected=bool(self.selected and(self.text(target)==self.text(self.selected)or self.text(arguments[1])==self.text(self.selected)))
        for i,source in enumerate(arguments[1:]):
            if i and self.selected and self.text(source)==self.text(self.selected):selected=True
            self.join_shunt(target,source,f'{name}.{i}')
        if selected:self.selected=target
        # Native command 421 falls through to PHASE with argument one's raw
        # descriptor pointer, even though the source has just been deleted.
        phase=arguments[1];old=self.memory.u32(target+0xac)
        if (phase<0x80000000 and old>=0x80000000)or(phase>=0x80000000 and 0<old<0x80000000):
            for parent in self.segments(target):
                for address in(parent,*self.children(parent)):
                    for first,last in((0,24),(0x44,0x5c),(0x88,0xa0)):
                        for offset in(0,8,16):
                            saved=self._number(address+first+offset);self._floating_copy(address+first+offset,address+last+offset);self._store(address+last+offset,R(saved))
            self.memory.put_u32(target+0xac,phase)

    def setup(self,driver,arguments,*,cap_length,length):
        if driver=='pi2':return self.clone(arguments[0],'geometry',cap_length,length),arguments[1]
        if driver!='calctrans':raise ValueError('Unknown geometry setup driver')
        first=self.clone(arguments[0],'clone.first',cap_length,length)
        second=self.clone(arguments[1],'clone.second',cap_length,length)
        target=self.copy(first,'geometry');other=self.copy(second,'copy.second')
        self.reverse(other);self.join(target,other,'geometry');self.remove(first);self.remove(second)
        reference=target if self.text(arguments[0])==self.text(arguments[2])else arguments[2]
        return target,reference

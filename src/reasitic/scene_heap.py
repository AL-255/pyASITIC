"""Geometry-only 32-bit arena for native erased descriptor identities.

Layout replay uses the reference glibc 2.39 size/cache/bin rules, without
allocating real native pointers. This is not a general process-heap emulator.
Source: https://github.com/bminor/glibc/blob/glibc-2.39/malloc/malloc.c
The reference i386 ABI aligns malloc records to 16 bytes: 0xbc shape requests
occupy 192 bytes and 0xf0 segment requests occupy 256 bytes.
"""
import struct
from collections import defaultdict,deque

class GeometryArena:
 def __init__(self):
  self.blocks={};self.cache=defaultdict(list);self.unsorted=deque();self.bins=defaultdict(deque);self.last=None;self.top=0;self.memory=bytearray()
 def _remove_free(self,address):
  if address in self.unsorted:self.unsorted.remove(address)
  else:
   size,_=self.blocks[address]
   if address in self.bins[size]:self.bins[size].remove(address)
 def _take(self,address,size):
  available,_=self.blocks[address];self._remove_free(address)
  if available-size>=16:
   remainder=address+size;self.blocks[remainder]=(available-size,'free');self.unsorted.append(remainder);self.last=remainder;available=size
  self.blocks[address]=(available,'live');return address
 def malloc(self,request):
  size=max(16,(request+4+15)//16*16)
  if self.cache[size]:
   address=self.cache[size].pop();self.blocks[address]=(size,'live');return address
  if self.bins[size]:
   address=self.bins[size].popleft();self.blocks[address]=(size,'live')
   while self.bins[size]and len(self.cache[size])<7:
    other=self.bins[size].popleft();self.blocks[other]=(size,'cached');self.cache[size].append(other)
   return address
  collected=False
  while self.unsorted:
   address=self.unsorted[0];available,_=self.blocks[address]
   if len(self.unsorted)==1 and address==self.last and available>size+16:return self._take(address,size)
   self.unsorted.popleft()
   if available==size:
    if len(self.cache[size])<7:self.cache[size].append(address);self.blocks[address]=(size,'cached');collected=True;continue
    self.blocks[address]=(size,'live');return address
   self.bins[available].append(address)
  if collected:
   address=self.cache[size].pop();self.blocks[address]=(size,'live');return address
  candidates=[n for n,values in self.bins.items()if n>=size and values]
  if candidates:return self._take(self.bins[min(candidates)][0],size)
  address=self.top;self.top+=size;self.memory.extend(bytes(size));self.blocks[address]=(size,'live');return address
 def free(self,address):
  size,state=self.blocks[address];assert state=='live'
  if len(self.cache[size])<7:self.cache[size].append(address);self.blocks[address]=(size,'cached');return
  right=address+size
  if right in self.blocks and self.blocks[right][1]=='free':
   self._remove_free(right);size+=self.blocks.pop(right)[0]
  previous=next((a for a,(n,state)in self.blocks.items()if state=='free'and a+n==address),None)
  if previous is not None:
   self._remove_free(previous);size+=self.blocks.pop(previous)[0];self.blocks.pop(address);address=previous
  self.blocks[address]=(size,'free');self.unsorted.append(address)
 def number(self,address):return struct.unpack_from('<d',self.memory,address)[0]
 def store(self,address,value):struct.pack_into('<d',self.memory,address,value)
 def write(self,shape,address,segments):
  self.store(address+0x54,shape.origin[0]);self.store(address+0x5c,shape.origin[1])
  for segment,base in zip(shape.segments,segments):
   self.memory[base:base+0xf0]=bytes(0xf0)
   for point,offset in zip(segment.points,(0,24,0x44,0x5c,0x88,0xa0)):struct.pack_into('<3d',self.memory,base+offset,*point)
   for offset,value in((0x30,segment.primary_width if segment.primary_width is not None else segment.width),(0x38,segment.primary_thickness if segment.primary_thickness is not None else segment.thickness),(0x74,segment.width),(0x7c,segment.thickness),(0xb8,segment.width),(0xc0,segment.thickness),(0xcc,segment.width),(0xd4,segment.thickness)):self.store(base+offset,value)
   for offset,value in((0x40,segment.metal),(0x84,segment.metal),(0xc8,segment.metal),(0xdc,segment.metal),(0xe0,segment.nx),(0xe4,segment.ny)):struct.pack_into('<i',self.memory,base+offset,value)
 def read(self,shape,address,segments):
  shape.origin[:]=[self.number(address+0x54),self.number(address+0x5c)]
  for segment,base in zip(shape.segments,segments):
   for point,offset in zip(segment.points,(0,24,0x44,0x5c,0x88,0xa0)):point[:]=struct.unpack_from('<3d',self.memory,base+offset)
   segment.width=self.number(base+0xcc);segment.thickness=self.number(base+0xd4)
   segment.primary_width=self.number(base+0x30);segment.primary_thickness=self.number(base+0x38)
   segment.metal=struct.unpack_from('<i',self.memory,base+0xdc)[0];segment.nx=struct.unpack_from('<i',self.memory,base+0xe0)[0];segment.ny=struct.unpack_from('<i',self.memory,base+0xe4)[0]
